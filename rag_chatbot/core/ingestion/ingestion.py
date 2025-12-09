import os
import re
import logging
import hashlib
import pickle
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, List, Optional

import pymupdf
from llama_index.core import Document, Settings
from llama_index.core.schema import BaseNode
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv
from tqdm import tqdm

from ...setting import get_settings, RAGSettings

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class DocumentReader:
    """Handles reading various document formats."""

    SUPPORTED_TEXT_FORMATS = ('.pdf', '.epub', '.txt')
    SUPPORTED_MARKDOWN_FORMATS = ('.md', '.markdown')
    SUPPORTED_IMAGE_FORMATS = ('.jpg', '.jpeg', '.tiff', '.png')

    def __init__(self):
        self._textract_available = self._check_textract_available()
        self._docx_available = self._check_docx_available()
        self._pptx_available = self._check_pptx_available()

    def _check_textract_available(self) -> bool:
        """Check if AWS Textract credentials are available."""
        return bool(
            os.getenv("AWS_ACCESS_KEY_ID") and
            os.getenv("AWS_SECRET_ACCESS_KEY")
        )

    def _check_docx_available(self) -> bool:
        """Check if docx support is available."""
        try:
            from langchain_community.document_loaders import Docx2txtLoader
            return True
        except ImportError:
            return False

    def _check_pptx_available(self) -> bool:
        """Check if pptx support is available."""
        try:
            from langchain_community.document_loaders import UnstructuredPowerPointLoader
            return True
        except ImportError:
            return False

    def read(self, file_path: str) -> str:
        """Read document and return extracted text."""
        file_name = Path(file_path).name.lower()

        if file_name.endswith(self.SUPPORTED_TEXT_FORMATS):
            return self._read_pdf_like(file_path)
        elif file_name.endswith(self.SUPPORTED_MARKDOWN_FORMATS):
            return self._read_markdown(file_path)
        elif file_name.endswith(".docx"):
            return self._read_docx(file_path)
        elif file_name.endswith(".pptx"):
            return self._read_pptx(file_path)
        elif file_name.endswith(self.SUPPORTED_IMAGE_FORMATS):
            return self._read_image(file_path)
        else:
            logger.warning(f"Unsupported file format: {file_name}")
            return ""

    def _read_pdf_like(self, file_path: str) -> str:
        """Read PDF, EPUB, or TXT files using pymupdf."""
        try:
            document = pymupdf.open(file_path)
            all_text = []
            for page in document:
                page_text = page.get_text("text")
                all_text.append(page_text)
            document.close()
            return " ".join(all_text)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return ""

    def _read_markdown(self, file_path: str) -> str:
        """Read markdown files as plain text."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading markdown {file_path}: {e}")
                return ""
        except Exception as e:
            logger.error(f"Error reading markdown {file_path}: {e}")
            return ""

    def _read_docx(self, file_path: str) -> str:
        """Read DOCX files."""
        if not self._docx_available:
            logger.warning("DOCX support not available. Install langchain-community.")
            return ""
        try:
            from langchain_community.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(file_path)
            document = loader.load()
            return " ".join([page.page_content for page in document])
        except Exception as e:
            logger.error(f"Error reading DOCX {file_path}: {e}")
            return ""

    def _read_pptx(self, file_path: str) -> str:
        """Read PPTX files."""
        if not self._pptx_available:
            logger.warning("PPTX support not available. Install langchain-community.")
            return ""
        try:
            from langchain_community.document_loaders import UnstructuredPowerPointLoader
            loader = UnstructuredPowerPointLoader(file_path)
            document = loader.load()
            return " ".join([page.page_content for page in document])
        except Exception as e:
            logger.error(f"Error reading PPTX {file_path}: {e}")
            return ""

    def _read_image(self, file_path: str) -> str:
        """Read image files using AWS Textract OCR."""
        if not self._textract_available:
            logger.warning(
                "AWS Textract not configured. Set AWS_ACCESS_KEY_ID and "
                "AWS_SECRET_ACCESS_KEY environment variables for image OCR."
            )
            return ""
        try:
            from langchain_community.document_loaders import AmazonTextractPDFLoader
            loader = AmazonTextractPDFLoader(file_path)
            document = loader.load()
            return " ".join([page.page_content for page in document])
        except Exception as e:
            logger.error(f"Error reading image {file_path} with Textract: {e}")
            return ""


class TextProcessor:
    """Handles text filtering and normalization."""

    # Regex pattern for filtering text
    FILTER_PATTERN = re.compile(r'[a-zA-Z0-9 `~!@#$%^&*()_\-+=\[\]{}|\\;:\'",.<>/?]+')
    WHITESPACE_PATTERN = re.compile(r'\s+')

    @classmethod
    def filter_text(cls, text: str) -> str:
        """Filter and normalize text."""
        if not text:
            return ""
        matches = cls.FILTER_PATTERN.findall(text)
        filtered_text = ' '.join(matches)
        normalized_text = cls.WHITESPACE_PATTERN.sub(' ', filtered_text.strip())
        return normalized_text


class NodeCache:
    """Handles caching of processed nodes to disk."""

    def __init__(self, cache_dir: str = "data/node_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, file_path: str) -> str:
        """Generate cache key based on file path and modification time."""
        file_path = Path(file_path)
        if file_path.exists():
            mtime = file_path.stat().st_mtime
            content = f"{file_path.name}_{mtime}"
        else:
            content = file_path.name
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, file_path: str) -> Optional[List[BaseNode]]:
        """Get cached nodes for a file."""
        cache_key = self._get_cache_key(file_path)
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Error loading cache for {file_path}: {e}")
        return None

    def set(self, file_path: str, nodes: List[BaseNode]) -> None:
        """Cache nodes for a file."""
        cache_key = self._get_cache_key(file_path)
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(nodes, f)
        except Exception as e:
            logger.warning(f"Error caching nodes for {file_path}: {e}")

    def clear(self) -> None:
        """Clear all cached nodes."""
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.warning(f"Error deleting cache file {cache_file}: {e}")


class LocalDataIngestion:
    """Handles document ingestion with parallel processing and caching."""

    def __init__(
        self,
        setting: RAGSettings | None = None,
        max_workers: int = 4,
        use_cache: bool = True
    ) -> None:
        self._setting = setting or get_settings()
        self._node_store: dict[str, List[BaseNode]] = {}
        self._ingested_file: List[str] = []
        self._max_workers = max_workers

        # Initialize components
        self._reader = DocumentReader()
        self._processor = TextProcessor()
        self._cache = NodeCache() if use_cache else None

        # Create splitter once
        self._splitter = SentenceSplitter.from_defaults(
            chunk_size=self._setting.ingestion.chunk_size,
            chunk_overlap=self._setting.ingestion.chunk_overlap,
            paragraph_separator=self._setting.ingestion.paragraph_sep,
            secondary_chunking_regex=self._setting.ingestion.chunking_regex
        )

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file contents for duplicate detection."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.warning(f"Error calculating hash for {file_path}: {e}")
            return ""

    def _process_single_file(
        self,
        input_file: str,
        embed_nodes: bool = True,
        embed_model: Any | None = None,
        it_practice: Optional[str] = None,
        offering_name: Optional[str] = None,
        offering_id: Optional[str] = None
    ) -> tuple[str, List[BaseNode]]:
        """Process a single file and return (filename, nodes).

        Args:
            input_file: Path to the file
            embed_nodes: Whether to embed nodes
            embed_model: Embedding model to use
            it_practice: IT Practice classification
            offering_name: Offering name
            offering_id: Unique offering ID

        Returns:
            Tuple of (filename, nodes)
        """
        file_name = Path(input_file).name
        file_path = Path(input_file)

        # Check memory cache first
        if file_name in self._node_store:
            return file_name, self._node_store[file_name]

        # Check disk cache
        if self._cache:
            cached_nodes = self._cache.get(input_file)
            if cached_nodes:
                logger.debug(f"Using cached nodes for {file_name}")
                return file_name, cached_nodes

        # Read and process document
        raw_text = self._reader.read(input_file)
        if not raw_text:
            logger.warning(f"No text extracted from {file_name}")
            return file_name, []

        filtered_text = self._processor.filter_text(raw_text)

        # Calculate file metadata
        file_hash = self._calculate_file_hash(input_file)
        file_size = file_path.stat().st_size if file_path.exists() else 0
        upload_timestamp = datetime.now().isoformat()

        # Create enhanced metadata
        metadata = {
            "file_name": file_name,
            "file_hash": file_hash,
            "file_size": file_size,
            "upload_timestamp": upload_timestamp,
        }

        # Add Sales Enablement metadata if provided
        if it_practice:
            metadata["it_practice"] = it_practice
        if offering_name:
            metadata["offering_name"] = offering_name
        if offering_id:
            metadata["offering_id"] = offering_id

        # Create document and split into nodes
        document = Document(
            text=filtered_text.strip(),
            metadata=metadata
        )

        nodes = self._splitter([document], show_progress=False)

        # Embed nodes if requested
        if embed_nodes and nodes:
            model = embed_model or Settings.embed_model
            if model:
                try:
                    nodes = model(nodes, show_progress=False)
                except Exception as e:
                    logger.error(f"Error embedding nodes for {file_name}: {e}")

        # Cache to disk
        if self._cache and nodes:
            self._cache.set(input_file, nodes)

        return file_name, nodes

    def store_nodes(
        self,
        input_files: list[str],
        embed_nodes: bool = True,
        embed_model: Any | None = None,
        it_practice: Optional[str] = None,
        offering_name: Optional[str] = None,
        offering_id: Optional[str] = None
    ) -> List[BaseNode]:
        """Process multiple files with parallel execution and enhanced metadata.

        Args:
            input_files: List of file paths to process
            embed_nodes: Whether to embed nodes
            embed_model: Embedding model to use
            it_practice: IT Practice classification for all files
            offering_name: Offering name for all files
            offering_id: Unique offering ID for all files

        Returns:
            List of processed nodes with enhanced metadata
        """
        return_nodes: List[BaseNode] = []
        self._ingested_file = []

        if not input_files:
            return return_nodes

        if embed_nodes:
            Settings.embed_model = embed_model or Settings.embed_model

        # Log metadata info
        if it_practice or offering_name:
            logger.info(
                f"Processing {len(input_files)} files with metadata: "
                f"IT Practice='{it_practice}', Offering='{offering_name}'"
            )

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {
                executor.submit(
                    self._process_single_file,
                    input_file,
                    embed_nodes,
                    embed_model,
                    it_practice,
                    offering_name,
                    offering_id
                ): input_file
                for input_file in input_files
            }

            # Use tqdm for progress tracking
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Ingesting documents"
            ):
                try:
                    file_name, nodes = future.result()
                    if nodes:
                        self._node_store[file_name] = nodes
                        self._ingested_file.append(file_name)
                        return_nodes.extend(nodes)

                        # Log node count with metadata
                        chunk_count = len(nodes)
                        logger.debug(
                            f"Processed {file_name}: {chunk_count} chunks, "
                            f"Practice='{it_practice}', Offering='{offering_name}'"
                        )
                except Exception as e:
                    input_file = futures[future]
                    logger.error(f"Error processing {input_file}: {e}")

        logger.info(f"Total nodes created: {len(return_nodes)}")
        return return_nodes

    def reset(self) -> None:
        """Reset in-memory node store."""
        self._node_store.clear()
        self._ingested_file.clear()

    def clear_cache(self) -> None:
        """Clear both memory and disk cache."""
        self.reset()
        if self._cache:
            self._cache.clear()

    def check_nodes_exist(self) -> bool:
        """Check if any nodes are stored."""
        return len(self._node_store) > 0

    def get_all_nodes(self) -> List[BaseNode]:
        """Get all stored nodes."""
        return_nodes = []
        for nodes in self._node_store.values():
            return_nodes.extend(nodes)
        return return_nodes

    def get_ingested_nodes(self) -> List[BaseNode]:
        """Get nodes from currently ingested files."""
        return_nodes = []
        for file in self._ingested_file:
            if file in self._node_store:
                return_nodes.extend(self._node_store[file])
        return return_nodes
