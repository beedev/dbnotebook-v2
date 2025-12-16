"""Simple Flask-based web interface for RAG Chatbot."""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import Generator

from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_file

from ..pipeline import LocalRAGPipeline
from ..core.image import ImageGenerator
from ..core.metadata import MetadataManager
from ..api.routes.chat import create_chat_routes

logger = logging.getLogger(__name__)


class FlaskChatbotUI:
    """Flask-based UI for the RAG chatbot."""

    def __init__(
        self,
        pipeline: LocalRAGPipeline,
        host: str = "host.docker.internal",
        data_dir: str = "data/data",
        upload_dir: str = "uploads",
        db_manager=None,
        notebook_manager=None
    ):
        self._pipeline = pipeline
        self._host = host
        self._data_dir = Path(data_dir)
        self._upload_dir = Path(upload_dir)
        self._processed_files: list[str] = []  # Track processed files

        # Notebook feature
        self._db_manager = db_manager
        self._notebook_manager = notebook_manager

        # Initialize image generator
        self._image_generator = ImageGenerator(pipeline._settings)

        # Initialize metadata manager
        self._metadata_manager = MetadataManager(config_dir="data/config")

        # Document metadata file
        self._doc_metadata_file = Path("data/config/documents_metadata.json")
        self._doc_metadata_file.parent.mkdir(parents=True, exist_ok=True)

        # Ensure directories exist
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._upload_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Flask app
        template_dir = Path(__file__).parent.parent / "templates"
        self._app = Flask(
            __name__,
            template_folder=str(template_dir)
        )

        self._setup_routes()

        # pgvector Persistence: Load nodes from persistent storage instead of re-ingesting
        # Documents are persisted to pgvector during upload, no need to reload from disk
        # The pipeline will load nodes from pgvector when set_engine() is called
        # self._reload_documents_with_metadata()  # DISABLED - using pgvector persistence

        logger.info("Flask UI initialized (using pgvector persistence)")

    def _reload_documents_with_metadata(self) -> None:
        """Reload all documents from data and uploads directories with metadata from JSON."""
        try:
            # Load document metadata
            doc_metadata = self._load_document_metadata()

            if not doc_metadata:
                logger.info("No document metadata found")
                return

            # Find all documents in data and uploads directories
            doc_files = []
            for directory in [self._data_dir, self._upload_dir]:
                if directory.exists():
                    for file_path in directory.iterdir():
                        if file_path.is_file() and file_path.name in doc_metadata:
                            doc_files.append(str(file_path))

            if not doc_files:
                logger.info("No documents found in data or uploads directories")
                return

            logger.info(f"Reloading {len(doc_files)} documents with metadata")

            # Process each document with its metadata
            for doc_path in doc_files:
                filename = os.path.basename(doc_path)
                metadata = doc_metadata[filename]

                it_practice = metadata.get("it_practice")
                offering_name = metadata.get("offering_name")
                offering_id = metadata.get("offering_id", "")

                # Auto-generate offering_id from offering_name if empty
                if not offering_id and offering_name and offering_name != "N/A":
                    offering_id = offering_name.lower().replace(" ", "-").replace("_", "-")

                # Store nodes with metadata
                self._pipeline.store_nodes(
                    input_files=[doc_path],
                    it_practice=it_practice if it_practice != "N/A" else None,
                    offering_name=offering_name if offering_name != "N/A" else None,
                    offering_id=offering_id if offering_id else None
                )

                # Track processed file
                if filename not in self._processed_files:
                    self._processed_files.append(filename)

                logger.info(f"Reloaded {filename} with Practice='{it_practice}', Offering='{offering_name}'")

            # Set chat mode after loading documents
            self._pipeline.set_chat_mode()
            logger.info(f"Successfully reloaded {len(doc_files)} documents with metadata")

        except Exception as e:
            logger.error(f"Error reloading documents with metadata: {e}")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def _load_document_metadata(self) -> dict:
        """Load document metadata from JSON file."""
        if self._doc_metadata_file.exists():
            try:
                with open(self._doc_metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading document metadata: {e}")
                return {}
        return {}

    def _save_document_metadata(self, metadata: dict) -> None:
        """Save document metadata to JSON file."""
        try:
            with open(self._doc_metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving document metadata: {e}")

    def _add_document_metadata(self, filename: str, it_practice: str, offering_name: str, offering_id: str) -> None:
        """Add metadata for a document."""
        metadata = self._load_document_metadata()
        metadata[filename] = {
            "it_practice": it_practice or "N/A",
            "offering_name": offering_name or "N/A",
            "offering_id": offering_id or ""
        }
        self._save_document_metadata(metadata)

    def _remove_document_metadata(self, filename: str) -> None:
        """Remove metadata for a document."""
        metadata = self._load_document_metadata()
        if filename in metadata:
            del metadata[filename]
            self._save_document_metadata(metadata)

    def _get_document_metadata(self, filename: str) -> dict:
        """Get metadata for a document."""
        metadata = self._load_document_metadata()
        return metadata.get(filename, {
            "it_practice": "N/A",
            "offering_name": "N/A",
            "offering_id": ""
        })

    def _is_image_generation_request(self, message: str) -> bool:
        """Use LLM to intelligently detect if message is requesting image generation."""
        # Quick keyword check first for efficiency
        image_keywords = ["image", "infographic", "diagram", "visual", "picture", "illustration", "graphic", "chart", "visualization"]
        message_lower = message.lower()

        # If no image-related keywords at all, skip LLM check
        if not any(keyword in message_lower for keyword in image_keywords):
            return False

        # Use LLM to understand intent
        intent_prompt = f"""Analyze this user message and determine if they are requesting IMAGE GENERATION (creating a new visual/image/infographic/diagram).

User message: "{message}"

Respond with ONLY "YES" if they want to generate/create a new image, infographic, diagram, or visual.
Respond with ONLY "NO" if they are asking about images, analyzing images, or want text-based information.

Examples:
- "Create an infographic about our products" -> YES
- "Generate a diagram showing the architecture" -> YES
- "What images do we have?" -> NO
- "Explain the diagram in the document" -> NO
- "Tell me about the infographic" -> NO

Response:"""

        try:
            # Use a simple, fast model for intent classification
            from llama_index.llms.openai import OpenAI
            llm = OpenAI(model="gpt-3.5-turbo", temperature=0, timeout=300.0)
            response = llm.complete(intent_prompt)

            # Check if response contains YES
            return "YES" in str(response).upper()
        except Exception as e:
            logger.error(f"Error in intent detection: {e}")
            # Fallback to simple keyword matching
            creation_words = ["generate", "create", "make", "draw", "design", "produce"]
            return any(word in message_lower for word in creation_words)


    def _create_image_prompt_with_context(self, user_message: str, document_content: str) -> str:
        """Create detailed image generation prompt using document content and user request.

        Args:
            user_message: User's original request
            document_content: Retrieved content from RAG documents

        Returns:
            Enhanced prompt optimized for image generation with document context
        """
        try:
            from llama_index.llms.openai import OpenAI

            expansion_prompt = f"""You are an expert at creating detailed image generation prompts for AI image models like Imagen.

CRITICAL: Image generation models struggle with text accuracy. Be EXTREMELY explicit about text spelling.

User's request: "{user_message}"

Document content retrieved from knowledge base:
\"\"\"
{document_content}
\"\"\"

Create a detailed image generation prompt with the following structure:

1. **EXACT TEXT TO INCLUDE** - Spell out each word letter-by-letter:
   - Extract key product names, features, and terms from the documents
   - For each text element, write: "Text reads: [WORD]" and then spell it: "spelled: W-O-R-D"
   - Be extremely explicit: "The word 'FRAMEWORK' must be spelled: F-R-A-M-E-W-O-R-K"
   - List 5-7 key text elements that MUST appear correctly

2. **Visual Design Elements** (NO TEXT):
   - Professional infographic layout with clean sections
   - Business-appropriate color scheme (blues, grays, whites)
   - Icons and graphics representing concepts
   - Clear visual hierarchy with distinct sections
   - Modern, minimal design

3. **Text Placement Instructions**:
   - Specify where each text element should appear
   - "Main heading at top", "Feature bullets in left section", etc.

4. **Style Guidelines**:
   - Professional business presentation style
   - High contrast for readability
   - Balanced composition
   - Clean, modern typography

IMPORTANT CONSTRAINTS:
- NO Lorem Ipsum or placeholder text
- NO gibberish or random characters
- EVERY text element must be spelled out letter-by-letter
- Maximum 50 words total text across entire image
- Prefer simple, short words when possible

Output format:
1. First list: "TEXT ELEMENTS (spelled out): [list each word with spelling]"
2. Then: "VISUAL DESIGN: [describe the visual layout without text]"
3. Then: "COMPLETE PROMPT: [combine everything into final prompt]"

Output ONLY this structured prompt."""

            llm = OpenAI(model="gpt-4-turbo", temperature=0.7, timeout=300.0)
            response = llm.complete(expansion_prompt)
            enhanced_prompt = str(response).strip()

            logger.info(f"Original request: {user_message[:100]}...")
            logger.info(f"Document context length: {len(document_content)} chars")
            logger.info(f"Enhanced prompt: {enhanced_prompt[:200]}...")

            return enhanced_prompt

        except Exception as e:
            logger.error(f"Error creating image prompt with context: {e}")
            logger.info("Falling back to user message")
            return user_message

    def _extract_text_structure(self, user_message: str, document_content: str) -> dict:
        """Extract structured text elements from document content for overlay.

        Args:
            user_message: User's original request
            document_content: Retrieved content from RAG documents

        Returns:
            Dictionary with structured text for overlay
        """
        try:
            from llama_index.llms.openai import OpenAI

            extraction_prompt = f"""Extract key information from the document for creating an infographic.

User wants: "{user_message}"

Document content:
\"\"\"
{document_content}
\"\"\"

Extract and structure the information as follows:
1. A clear, concise TITLE (5-8 words max)
2. 3-4 SECTIONS, each with:
   - heading: Short heading (2-4 words)
   - content: Brief description (10-15 words)

Focus on the most important information that addresses the user's request.

Output format (JSON):
{{
    "title": "Main Title Here",
    "sections": [
        {{"heading": "Section 1", "content": "Brief description here"}},
        {{"heading": "Section 2", "content": "Brief description here"}},
        {{"heading": "Section 3", "content": "Brief description here"}}
    ]
}}

Output ONLY valid JSON, nothing else."""

            llm = OpenAI(model="gpt-4-turbo", temperature=0.3, timeout=300.0)
            response = llm.complete(extraction_prompt)

            # Parse JSON response
            import json
            text_structure = json.loads(str(response).strip())

            logger.info(f"Extracted text structure: {text_structure}")
            return text_structure

        except Exception as e:
            logger.error(f"Error extracting text structure: {e}")
            # Fallback structure
            return {
                "title": "Retail Solutions",
                "sections": [
                    {"heading": "Overview", "content": document_content[:100]},
                ]
            }

    def _setup_routes(self):
        """Set up Flask routes."""

        @self._app.route("/")
        def index():
            return render_template("index.html")

        @self._app.route("/chat", methods=["POST"])
        def chat():
            data = request.json
            message = data.get("message", "")
            history = data.get("history", [])
            model = data.get("model", "")
            mode = data.get("mode", "chat")
            # Hybrid mode: support both offerings (traditional) and notebooks
            selected_offerings = data.get("selected_offerings", [])
            selected_notebooks = data.get("selected_notebooks", [])

            if not message:
                return jsonify({"error": "No message provided"}), 400

            # Log hybrid selection
            if selected_notebooks:
                logger.info(f"Received query with {len(selected_notebooks)} selected notebooks: {selected_notebooks}")
            elif selected_offerings:
                logger.info(f"Received query with {len(selected_offerings)} selected offerings: {selected_offerings}")
            else:
                logger.info("Received query with no selections")

            # Set model if provided and different
            if model and model != self._pipeline.get_model_name():
                try:
                    self._pipeline.set_model_name(model)
                    self._pipeline.set_model()
                    # Set engine with hybrid filter support (notebooks or offerings)
                    # Note: query_sales_mode() will manage engine state during query execution
                    offering_filter = selected_notebooks if selected_notebooks else selected_offerings
                    if offering_filter:
                        self._pipeline.set_engine(offering_filter=offering_filter)
                    else:
                        self._pipeline.set_engine()
                except Exception as e:
                    logger.error(f"Error setting model: {e}")

            # Ensure model is set
            if not self._pipeline.get_model_name():
                self._pipeline.set_model_name("")
                self._pipeline.set_model()

            # Engine management is now handled automatically by query_sales_mode()
            # which preserves conversation history when offerings change

            # STEP 1: Always query documents first to get context
            def process_request() -> Generator[str, None, None]:
                try:
                    # Query RAG pipeline to get relevant document content
                    yield f"data: {json.dumps({'token': ''})}\n\n"

                    # Choose query method based on whether notebooks are selected
                    if selected_notebooks:
                        # NOTEBOOK MODE: Use simple query() method for direct Q&A with notebook documents
                        # Set engine with notebook filter before querying
                        self._pipeline.set_engine(offering_filter=selected_notebooks)
                        rag_response = self._pipeline.query(
                            mode=mode,
                            message=message,
                            chatbot=history
                        )
                    else:
                        # SALES MODE: Use query_sales_mode for intelligent classification
                        # Hybrid mode: pass both offerings and notebooks
                        rag_response = self._pipeline.query_sales_mode(
                            message=message,
                            selected_offerings=selected_offerings,
                            selected_notebooks=selected_notebooks,
                            chatbot=history
                        )

                    # Get the full response text from RAG
                    document_context = ""

                    # Check if there's a response prefix from sales mode
                    response_prefix = getattr(rag_response, 'response_prefix', '')
                    if response_prefix:
                        # Stream the prefix first
                        for token in response_prefix:
                            yield f"data: {json.dumps({'token': token})}\n\n"

                    for token in rag_response.response_gen:
                        document_context += token

                    logger.info(f"Retrieved document context: {document_context[:200]}...")

                    # STEP 2: Check if image generation is requested
                    if self._is_image_generation_request(message):
                        msg1 = "\n\n**APPROACH 1: Improved AI-Generated Text**\n"
                        yield f"data: {json.dumps({'token': msg1})}\n\n"
                        yield f"data: {json.dumps({'token': 'Creating explicit prompt with letter-by-letter spelling...'})}\n\n"

                        # APPROACH 1: Generate with improved explicit prompt
                        enhanced_prompt = self._create_image_prompt_with_context(
                            user_message=message,
                            document_content=document_context
                        )

                        yield f"data: {json.dumps({'token': 'Generating image with AI text...'})}\n\n"

                        image_paths_v1 = self._image_generator.generate_image(
                            prompt=enhanced_prompt,
                            num_images=1
                        )

                        if image_paths_v1:
                            image_url_v1 = f"/image/{os.path.basename(image_paths_v1[0])}"
                            msg2 = "\n✓ Approach 1 complete!\n"
                            yield f"data: {json.dumps({'token': msg2})}\n\n"
                            yield f"data: {json.dumps({'image': image_url_v1, 'message': '**Approach 1:** AI-generated text'})}\n\n"

                        # APPROACH 2: Generate with hybrid text overlay
                        msg3 = "\n\n**APPROACH 2: Hybrid (AI Design + Perfect Text Overlay)**\n"
                        yield f"data: {json.dumps({'token': msg3})}\n\n"
                        yield f"data: {json.dumps({'token': 'Extracting text structure from documents...'})}\n\n"

                        text_structure = self._extract_text_structure(message, document_context)

                        yield f"data: {json.dumps({'token': 'Generating base image design...'})}\n\n"

                        # Generate base image with minimal/no text
                        base_prompt = """Professional business infographic layout with clean design.
Style: Modern, minimal, professional
Color scheme: Blue gradients, white, gray accents
Layout: Clear sections with visual hierarchy
Elements: Icons, graphics, charts representing business concepts
NO TEXT - text will be added separately
High quality, business presentation style"""

                        image_paths_v2 = self._image_generator.generate_image(
                            prompt=base_prompt,
                            num_images=1
                        )

                        if image_paths_v2:
                            yield f"data: {json.dumps({'token': 'Adding perfect text overlay...'})}\n\n"

                            # Add text overlay
                            overlay_path = self._image_generator.add_text_overlay(
                                image_path=image_paths_v2[0],
                                text_elements=text_structure
                            )

                            image_url_v2 = f"/image/{os.path.basename(overlay_path)}"
                            msg4 = "\n✓ Approach 2 complete!\n\n"
                            yield f"data: {json.dumps({'token': msg4})}\n\n"
                            yield f"data: {json.dumps({'image': image_url_v2, 'message': '**Approach 2:** Perfect text overlay'})}\n\n"

                        msg5 = "\n\n**Compare both approaches and let me know which works better!**\n"
                        yield f"data: {json.dumps({'token': msg5})}\n\n"
                        yield f"data: {json.dumps({'done': True})}\n\n"

                    else:
                        # STEP 5: Return normal RAG response
                        for token in document_context:
                            yield f"data: {json.dumps({'token': token})}\n\n"
                        yield f"data: {json.dumps({'done': True})}\n\n"

                except Exception as e:
                    logger.error(f"Error during chat: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return Response(
                stream_with_context(process_request()),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no"
                }
            )

        @self._app.route("/upload", methods=["POST"])
        def upload():
            if "files" not in request.files:
                return jsonify({"success": False, "error": "No files provided"})

            files = request.files.getlist("files")
            if not files or files[0].filename == "":
                return jsonify({"success": False, "error": "No files selected"})

            # Get notebook_id from form (notebook-based architecture)
            notebook_id = request.form.get("notebook_id", "")
            user_id = "00000000-0000-0000-0000-000000000001"  # Default user

            # Legacy metadata (still captured for backwards compatibility)
            it_practice = request.form.get("it_practice", "")
            offering_name = request.form.get("offering_name", "")
            offering_id = ""
            if offering_name:
                offering_id = offering_name.lower().replace(" ", "-").replace("_", "-")

            uploaded_files = []
            try:
                for file in files:
                    if file.filename:
                        # Save file
                        filepath = self._upload_dir / file.filename
                        file.save(str(filepath))
                        uploaded_files.append(str(filepath))
                        logger.info(f"Uploaded: {file.filename} [Notebook: {notebook_id}]")

                # Process documents with notebook-based architecture
                if uploaded_files:
                    self._pipeline.store_nodes(
                        input_files=uploaded_files,
                        notebook_id=notebook_id if notebook_id else None,
                        user_id=user_id
                    )
                    self._pipeline.set_chat_mode()
                    # Track processed files and save metadata
                    for f in uploaded_files:
                        filename = os.path.basename(f)
                        if filename not in self._processed_files:
                            self._processed_files.append(filename)
                        # Save document metadata (legacy support)
                        self._add_document_metadata(filename, it_practice, offering_name, offering_id)
                    logger.info(f"Processed {len(uploaded_files)} documents for notebook {notebook_id}")

                return jsonify({
                    "success": True,
                    "count": len(uploaded_files),
                    "files": [os.path.basename(f) for f in uploaded_files],
                    "all_files": self._processed_files,
                    "notebook_id": notebook_id,
                    "metadata": {
                        "it_practice": it_practice,
                        "offering_name": offering_name,
                        "offering_id": offering_id
                    }
                })

            except Exception as e:
                logger.error(f"Error uploading files: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/clear", methods=["POST"])
        def clear():
            try:
                self._pipeline.clear_conversation()
                return jsonify({"success": True})
            except Exception as e:
                logger.error(f"Error clearing conversation: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/reset", methods=["POST"])
        def reset():
            try:
                self._pipeline.reset_documents()
                self._pipeline.reset_conversation()

                # Clear upload directory
                for file in self._upload_dir.iterdir():
                    try:
                        file.unlink()
                    except Exception:
                        pass

                # Clear tracked files
                self._processed_files.clear()

                return jsonify({"success": True})
            except Exception as e:
                logger.error(f"Error resetting: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/model", methods=["POST"])
        def set_model():
            data = request.json
            model = data.get("model", "")

            if not model:
                return jsonify({"success": False, "error": "No model specified"})

            try:
                # Skip existence check for API-based models
                is_api_model = (
                    model.startswith("gpt-") or
                    model.startswith("claude-") or
                    model.startswith("gemini-")
                )

                # Check if model exists (only for Ollama models)
                if not is_api_model and not self._pipeline.check_exist(model):
                    return jsonify({
                        "success": False,
                        "error": f"Model {model} not found. Pull it first."
                    })

                self._pipeline.set_model_name(model)
                self._pipeline.set_model()
                self._pipeline.set_engine()
                logger.info(f"Model set to: {model}")

                return jsonify({"success": True, "model": model})

            except Exception as e:
                logger.error(f"Error setting model: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/notebooks")
        def notebooks_page():
            """Serve the notebooks management page."""
            return render_template("notebooks.html")

        @self._app.route("/documents")
        def documents_page():
            """Serve the documents management page."""
            return render_template("documents.html")

        @self._app.route("/api/documents/list", methods=["GET"])
        def list_documents():
            """Get list of uploaded documents with metadata."""
            try:
                documents = []
                # Get all files from upload directory
                if self._upload_dir.exists():
                    for file_path in self._upload_dir.iterdir():
                        if file_path.is_file():
                            # Get file size
                            file_size = file_path.stat().st_size
                            size_str = self._format_file_size(file_size)

                            # Get document metadata
                            doc_metadata = self._get_document_metadata(file_path.name)
                            documents.append({
                                "name": file_path.name,
                                "size": size_str,
                                "it_practice": doc_metadata.get("it_practice", "N/A"),
                                "offering_name": doc_metadata.get("offering_name", "N/A")
                            })

                return jsonify({
                    "success": True,
                    "documents": documents,
                    "count": len(documents)
                })
            except Exception as e:
                logger.error(f"Error listing documents: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/api/documents/<filename>", methods=["DELETE"])
        def delete_document(filename):
            """Delete a document."""
            try:
                file_path = self._upload_dir / filename

                if not file_path.exists():
                    return jsonify({
                        "success": False,
                        "error": "File not found"
                    }), 404

                # Delete the file
                file_path.unlink()

                # Remove from processed files list
                if filename in self._processed_files:
                    self._processed_files.remove(filename)

                # Remove document metadata
                self._remove_document_metadata(filename)

                logger.info(f"Deleted document: {filename}")

                return jsonify({
                    "success": True,
                    "message": f"Document '{filename}' deleted successfully"
                })

            except Exception as e:
                logger.error(f"Error deleting document: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self._app.route("/health", methods=["GET"])
        def health():
            """Comprehensive health check endpoint (MVP 6)."""
            import time
            import psutil
            import requests

            start_time = time.time()
            health_status = {
                "status": "healthy",
                "version": "2.0.0",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "components": {}
            }

            # Check database connection
            try:
                if self._db_manager:
                    with self._db_manager.get_session() as session:
                        session.execute("SELECT 1")
                    health_status["components"]["database"] = {
                        "status": "healthy",
                        "type": "postgresql"
                    }
                else:
                    health_status["components"]["database"] = {
                        "status": "not_configured",
                        "type": "none"
                    }
            except Exception as e:
                health_status["status"] = "degraded"
                health_status["components"]["database"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }

            # Check Ollama connection
            try:
                ollama_url = f"http://{self._host}:11434/api/tags"
                response = requests.get(ollama_url, timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    health_status["components"]["ollama"] = {
                        "status": "healthy",
                        "models_available": len(models)
                    }
                else:
                    health_status["components"]["ollama"] = {
                        "status": "degraded",
                        "http_status": response.status_code
                    }
            except Exception as e:
                health_status["components"]["ollama"] = {
                    "status": "unavailable",
                    "error": str(e)
                }

            # Check vector store
            try:
                if self._pipeline and self._pipeline._vector_store:
                    stats = self._pipeline._vector_store.get_collection_stats()
                    health_status["components"]["vector_store"] = {
                        "status": "healthy",
                        "type": "pgvector",
                        "document_count": stats.get("count", 0)
                    }
                else:
                    health_status["components"]["vector_store"] = {
                        "status": "not_initialized"
                    }
            except Exception as e:
                health_status["components"]["vector_store"] = {
                    "status": "error",
                    "error": str(e)
                }

            # System resources
            try:
                health_status["system"] = {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage('/').percent
                }
            except Exception:
                health_status["system"] = {"status": "unavailable"}

            # Response time
            health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)

            # Overall status
            component_statuses = [c.get("status") for c in health_status["components"].values()]
            if "unhealthy" in component_statuses:
                health_status["status"] = "unhealthy"
            elif "degraded" in component_statuses or "unavailable" in component_statuses:
                health_status["status"] = "degraded"

            status_code = 200 if health_status["status"] == "healthy" else 503
            return jsonify(health_status), status_code

        @self._app.route("/api/health", methods=["GET"])
        def api_health():
            """Simple health check for load balancers."""
            return jsonify({"status": "ok"})

        @self._app.route("/generate-image", methods=["POST"])
        def generate_image():
            try:
                data = request.json
                prompt = data.get("prompt", "")
                num_images = data.get("num_images", 1)
                aspect_ratio = data.get("aspect_ratio", "1:1")

                if not prompt or not prompt.strip():
                    return jsonify({"success": False, "error": "Prompt cannot be empty"})

                # Generate images
                image_paths = self._image_generator.generate_image(
                    prompt=prompt,
                    num_images=num_images,
                    aspect_ratio=aspect_ratio
                )

                # Get image info
                images_info = []
                for path in image_paths:
                    info = self._image_generator.get_image_info(path)
                    info["path"] = path
                    info["url"] = f"/image/{Path(path).name}"
                    images_info.append(info)

                return jsonify({
                    "success": True,
                    "count": len(image_paths),
                    "images": images_info
                })

            except Exception as e:
                logger.error(f"Error generating image: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/image/<filename>", methods=["GET"])
        def get_image(filename):
            try:
                image_dir = Path(self._image_generator._output_dir)
                filepath = image_dir / filename

                if not filepath.exists():
                    return jsonify({"error": "Image not found"}), 404

                return send_file(str(filepath), mimetype="image/png")

            except Exception as e:
                logger.error(f"Error serving image: {e}")
                return jsonify({"error": str(e)}), 500

        @self._app.route("/images", methods=["GET"])
        def list_images():
            try:
                image_paths = self._image_generator.list_generated_images()
                images_info = []

                for path in image_paths:
                    info = self._image_generator.get_image_info(path)
                    info["url"] = f"/image/{Path(path).name}"
                    images_info.append(info)

                return jsonify({
                    "success": True,
                    "count": len(images_info),
                    "images": images_info
                })

            except Exception as e:
                logger.error(f"Error listing images: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/clear-images", methods=["POST"])
        def clear_images():
            try:
                deleted_count = self._image_generator.clear_output_dir()
                return jsonify({
                    "success": True,
                    "deleted_count": deleted_count
                })

            except Exception as e:
                logger.error(f"Error clearing images: {e}")
                return jsonify({"success": False, "error": str(e)})

        # === Sales Enablement Metadata Endpoints ===

        @self._app.route("/api/practices", methods=["GET"])
        def get_practices():
            """Get all IT practices."""
            try:
                practices = self._metadata_manager.get_all_practices()
                return jsonify({
                    "success": True,
                    "practices": practices,
                    "count": len(practices)
                })
            except Exception as e:
                logger.error(f"Error getting practices: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/api/offerings", methods=["GET"])
        def get_offerings():
            """Get all unique offerings from uploaded documents."""
            try:
                # Load document metadata
                metadata = self._load_document_metadata()

                # Extract unique offerings with their IT practices
                offerings_map = {}
                for filename, doc_meta in metadata.items():
                    offering_name = doc_meta.get("offering_name", "")
                    it_practice = doc_meta.get("it_practice", "")

                    # Skip N/A or empty offerings
                    if offering_name and offering_name != "N/A":
                        if offering_name not in offerings_map:
                            offerings_map[offering_name] = {
                                "name": offering_name,
                                "it_practice": it_practice,
                                "document_count": 0
                            }
                        offerings_map[offering_name]["document_count"] += 1

                # Convert to list sorted by name
                offerings = sorted(offerings_map.values(), key=lambda x: x["name"])

                return jsonify({
                    "success": True,
                    "offerings": offerings,
                    "count": len(offerings)
                })
            except Exception as e:
                logger.error(f"Error getting offerings: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/api/models", methods=["GET"])
        def get_available_models():
            """Get all available LLM models from Ollama and configured API providers."""
            try:
                import os
                from rag_chatbot.core.model import LocalRAGModel

                models = []

                # Get Ollama models
                ollama_models = LocalRAGModel.list_available_models(self._host)
                for model in ollama_models:
                    models.append({
                        "name": model,
                        "provider": "Ollama",
                        "type": "local"
                    })

                # Get OpenAI models if API key is configured
                openai_key = os.getenv("OPENAI_API_KEY", "")
                if openai_key and openai_key != "your_openai_api_key_here":
                    # Use the OPENAI_MODELS set from LocalRAGModel
                    for model in sorted(LocalRAGModel.OPENAI_MODELS):
                        if model not in [m["name"] for m in models]:
                            models.append({
                                "name": model,
                                "provider": "OpenAI",
                                "type": "api"
                            })

                # Get Anthropic (Claude) models if API key is configured
                anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
                if anthropic_key and anthropic_key != "your_anthropic_api_key_here":
                    # Use the CLAUDE_MODELS set from LocalRAGModel
                    for model in sorted(LocalRAGModel.CLAUDE_MODELS):
                        if model not in [m["name"] for m in models]:
                            models.append({
                                "name": model,
                                "provider": "Anthropic",
                                "type": "api"
                            })

                # Get Google (Gemini) models if API key is configured
                google_key = os.getenv("GOOGLE_API_KEY", "")
                if google_key and google_key != "your_google_api_key_here":
                    # Use the GEMINI_MODELS set from LocalRAGModel
                    for model in sorted(LocalRAGModel.GEMINI_MODELS):
                        if model not in [m["name"] for m in models]:
                            models.append({
                                "name": model,
                                "provider": "Google",
                                "type": "api"
                            })

                # Remove duplicates while preserving order
                seen = set()
                unique_models = []
                for model in models:
                    if model["name"] not in seen:
                        seen.add(model["name"])
                        unique_models.append(model)

                return jsonify({
                    "success": True,
                    "models": unique_models,
                    "count": len(unique_models)
                })

            except Exception as e:
                logger.error(f"Error getting models: {e}")
                return jsonify({"success": False, "error": str(e), "models": []})
        @self._app.route("/api/practices/<practice_name>/offerings", methods=["GET"])
        def get_practice_offerings(practice_name):
            """Get offerings for a specific practice."""
            try:
                offerings = self._metadata_manager.get_offerings_by_practice(practice_name)
                return jsonify({
                    "success": True,
                    "practice": practice_name,
                    "offerings": offerings,
                    "count": len(offerings)
                })
            except Exception as e:
                logger.error(f"Error getting practice offerings: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/api/practices", methods=["POST"])
        def add_practice():
            """Add a new IT practice."""
            try:
                data = request.json
                practice_name = data.get("name", "")

                if not practice_name:
                    return jsonify({"success": False, "error": "Practice name required"})

                success = self._metadata_manager.add_practice(practice_name)

                if success:
                    return jsonify({
                        "success": True,
                        "practice": practice_name
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Practice already exists or invalid name"
                    })

            except Exception as e:
                logger.error(f"Error adding practice: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/api/offerings", methods=["POST"])
        def add_offering():
            """Add a new offering."""
            try:
                data = request.json
                practice = data.get("practice", "")
                offering_name = data.get("name", "")
                description = data.get("description", "")

                if not practice or not offering_name:
                    return jsonify({
                        "success": False,
                        "error": "Practice and offering name required"
                    })

                offering_id = self._metadata_manager.add_offering(
                    practice=practice,
                    offering_name=offering_name,
                    description=description
                )

                if offering_id:
                    return jsonify({
                        "success": True,
                        "offering_id": offering_id,
                        "offering_name": offering_name,
                        "practice": practice
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Failed to add offering (practice may not exist or offering already exists)"
                    })

            except Exception as e:
                logger.error(f"Error adding offering: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/api/metadata/stats", methods=["GET"])
        def get_metadata_stats():
            """Get metadata statistics."""
            try:
                stats = self._metadata_manager.get_statistics()
                return jsonify({
                    "success": True,
                    "stats": stats
                })
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                return jsonify({"success": False, "error": str(e)})

        # Register chat API routes
        create_chat_routes(self._app, self._pipeline)

        # === Query Logging & Observability Endpoints ===

        @self._app.route("/api/usage-stats", methods=["GET"])
        def get_usage_stats():
            """Get usage statistics for current session."""
            try:
                if not self._pipeline._query_logger:
                    return jsonify({
                        "success": False,
                        "error": "Query logger not initialized"
                    })

                stats = self._pipeline._query_logger.get_usage_stats()
                return jsonify({
                    "success": True,
                    "stats": stats
                })
            except Exception as e:
                logger.error(f"Error getting usage stats: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/api/recent-queries", methods=["GET"])
        def get_recent_queries():
            """Get recent query history."""
            try:
                if not self._pipeline._query_logger:
                    return jsonify({
                        "success": False,
                        "error": "Query logger not initialized"
                    })

                limit = request.args.get("limit", 50, type=int)
                recent = self._pipeline._query_logger.get_recent_logs(limit=limit)

                # Convert datetime objects to strings for JSON serialization
                for log in recent:
                    if "timestamp" in log:
                        log["timestamp"] = log["timestamp"].isoformat()

                return jsonify({
                    "success": True,
                    "queries": recent,
                    "count": len(recent)
                })
            except Exception as e:
                logger.error(f"Error getting recent queries: {e}")
                return jsonify({"success": False, "error": str(e)})

        @self._app.route("/api/model-pricing", methods=["GET"])
        def get_model_pricing():
            """Get pricing information for all supported models."""
            try:
                if not self._pipeline._query_logger:
                    return jsonify({
                        "success": False,
                        "error": "Query logger not initialized"
                    })

                models = self._pipeline._query_logger.list_supported_models()
                pricing = {}
                for model in models:
                    model_pricing = self._pipeline._query_logger.get_model_pricing(model)
                    if model_pricing:
                        pricing[model] = model_pricing

                return jsonify({
                    "success": True,
                    "pricing": pricing,
                    "count": len(pricing)
                })
            except Exception as e:
                logger.error(f"Error getting model pricing: {e}")
                return jsonify({"success": False, "error": str(e)})

        # =============================================
        # Notebook API Routes
        # =============================================

        @self._app.route("/api/notebooks", methods=["GET"])
        def list_notebooks():
            """List all notebooks for the default user."""
            try:
                if not self._notebook_manager:
                    return jsonify({
                        "success": False,
                        "error": "Notebook feature not available"
                    }), 503

                # Use default user ID (UUID format)
                user_id = "00000000-0000-0000-0000-000000000001"
                notebooks = self._notebook_manager.list_notebooks(user_id)

                return jsonify({
                    "success": True,
                    "notebooks": notebooks,
                    "count": len(notebooks)
                })
            except Exception as e:
                logger.error(f"Error listing notebooks: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self._app.route("/api/notebooks", methods=["POST"])
        def create_notebook():
            """Create a new notebook."""
            try:
                if not self._notebook_manager:
                    return jsonify({
                        "success": False,
                        "error": "Notebook feature not available"
                    }), 503

                data = request.json
                name = data.get("name")
                description = data.get("description", "")

                if not name:
                    return jsonify({
                        "success": False,
                        "error": "Notebook name is required"
                    }), 400

                # Use default user ID
                user_id = "00000000-0000-0000-0000-000000000001"

                notebook_data = self._notebook_manager.create_notebook(
                    user_id=user_id,
                    name=name,
                    description=description
                )

                return jsonify({
                    "success": True,
                    "notebook": {
                        "id": notebook_data["id"],
                        "name": notebook_data["name"]
                    },
                    "message": f"Notebook '{name}' created successfully"
                })
            except Exception as e:
                logger.error(f"Error creating notebook: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self._app.route("/api/notebooks/<notebook_id>", methods=["DELETE"])
        def delete_notebook(notebook_id):
            """Delete a notebook."""
            try:
                if not self._notebook_manager:
                    return jsonify({
                        "success": False,
                        "error": "Notebook feature not available"
                    }), 503

                success = self._notebook_manager.delete_notebook(notebook_id)

                if success:
                    return jsonify({
                        "success": True,
                        "message": f"Notebook deleted successfully"
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Failed to delete notebook"
                    }), 404
            except Exception as e:
                logger.error(f"Error deleting notebook: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self._app.route("/api/notebooks/<notebook_id>/documents", methods=["POST"])
        def upload_to_notebook(notebook_id):
            """Upload documents to a notebook."""
            try:
                if not self._notebook_manager:
                    return jsonify({
                        "success": False,
                        "error": "Notebook feature not available"
                    }), 503

                # Get uploaded files
                if 'files' not in request.files:
                    return jsonify({
                        "success": False,
                        "error": "No files provided"
                    }), 400

                files = request.files.getlist('files')
                if not files or files[0].filename == '':
                    return jsonify({
                        "success": False,
                        "error": "No files selected"
                    }), 400

                uploaded_files = []

                # Collect file paths for batch processing
                file_paths = []
                file_info = {}

                for file in files:
                    if file and file.filename:
                        # Save file to data directory
                        file_path = os.path.join(str(self._data_dir), file.filename)
                        file.save(file_path)

                        # Get file stats for response
                        file_size = os.path.getsize(file_path)

                        file_paths.append(file_path)
                        file_info[file.filename] = file_size

                # Process all files at once with notebook_id metadata
                # store_nodes() handles:
                # 1. Document registration in PostgreSQL with correct chunk_count
                # 2. Node metadata (notebook_id, source_id, user_id)
                # 3. pgvector persistence
                logger.info(f"Processing {len(file_paths)} files for notebook {notebook_id}")
                returned_nodes = self._pipeline.store_nodes(
                    input_files=file_paths,
                    notebook_id=notebook_id,
                    user_id="00000000-0000-0000-0000-000000000001"  # Default user UUID
                )

                # Build response with file information
                for filename, file_size in file_info.items():
                    # Track processed file
                    if filename not in self._processed_files:
                        self._processed_files.append(filename)

                    # Get source_id from database for this file
                    docs = self._notebook_manager.get_documents(notebook_id)
                    source_id = None
                    for doc in docs:
                        if doc['file_name'] == filename:
                            source_id = doc['source_id']
                            break

                    uploaded_files.append({
                        "filename": filename,
                        "source_id": source_id,
                        "size": file_size
                    })

                    logger.info(f"Uploaded {filename} to notebook {notebook_id} (source_id: {source_id})")

                # Force rebuild chat engine after loading documents (load nodes from pgvector)
                logger.info("Rebuilding chat engine with newly loaded documents from pgvector")
                self._pipeline.set_chat_mode(force_reset=True)

                return jsonify({
                    "success": True,
                    "uploaded": uploaded_files,
                    "count": len(uploaded_files),
                    "message": f"Successfully uploaded {len(uploaded_files)} document(s)"
                })
            except Exception as e:
                logger.error(f"Error uploading to notebook: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self._app.route("/api/notebooks/<notebook_id>/documents", methods=["GET"])
        def list_notebook_documents(notebook_id):
            """List all documents in a notebook."""
            try:
                if not self._notebook_manager:
                    return jsonify({
                        "success": False,
                        "error": "Notebook feature not available"
                    }), 503

                documents = self._notebook_manager.get_documents(notebook_id)

                return jsonify({
                    "success": True,
                    "documents": documents,
                    "count": len(documents)
                })
            except Exception as e:
                logger.error(f"Error listing notebook documents: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self._app.route("/api/notebooks/<notebook_id>/documents/<source_id>", methods=["DELETE"])
        def delete_notebook_document(notebook_id, source_id):
            """Delete a document from a notebook."""
            try:
                if not self._notebook_manager:
                    return jsonify({
                        "success": False,
                        "error": "Notebook feature not available"
                    }), 503

                # Delete from PostgreSQL database
                success = self._notebook_manager.remove_document(notebook_id, source_id)

                if not success:
                    return jsonify({
                        "success": False,
                        "error": "Document not found or deletion failed"
                    }), 404

                # Delete from pgvector embeddings table
                if self._pipeline and self._pipeline._vector_store:
                    pgvector_success = self._pipeline._vector_store.delete_document_nodes(source_id)

                    if not pgvector_success:
                        logger.warning(f"pgvector deletion failed for document {source_id}, but PostgreSQL deletion succeeded")

                logger.info(f"Deleted document {source_id} from notebook {notebook_id}")

                return jsonify({
                    "success": True,
                    "message": f"Document deleted successfully"
                })
            except Exception as e:
                logger.error(f"Error deleting notebook document: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

    def run(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
        """Run the Flask application."""
        logger.info(f"Starting Flask server on {host}:{port}")
        self._app.run(host=host, port=port, debug=debug, threaded=True)

    def get_app(self):
        """Return the Flask app for WSGI servers."""
        return self._app
