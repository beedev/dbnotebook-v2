"""Analytics Service for Excel data analysis and dashboard generation.

Orchestrates:
- File parsing (Excel/CSV)
- Data profiling (ydata-profiling)
- LLM dashboard configuration generation
"""

import logging
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
import json

from .types import (
    ParsedData,
    ColumnMetadata,
    ProfilingResult,
    DashboardConfig,
    AnalysisSession,
    ModificationResult,
)
from .profiler import DataProfiler
from .dashboard_modifier import DashboardModifier

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Main service for analytics operations."""

    # In-memory session store (will be replaced with database)
    _sessions: Dict[str, AnalysisSession] = {}

    def __init__(
        self,
        upload_dir: Optional[Path] = None,
        profile_dir: Optional[Path] = None,
        max_file_size_mb: int = 50,
        sample_size: int = 100,
    ):
        """Initialize the analytics service.

        Args:
            upload_dir: Directory for uploaded files
            profile_dir: Directory for profile reports
            max_file_size_mb: Maximum file size in MB
            sample_size: Number of rows to sample for LLM
        """
        self._upload_dir = upload_dir or Path("uploads/analytics")
        self._profile_dir = profile_dir or Path("uploads/analytics/profiles")
        self._max_file_size = max_file_size_mb * 1024 * 1024
        self._sample_size = sample_size

        # Create directories
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._profile_dir.mkdir(parents=True, exist_ok=True)

        # Initialize profiler
        self._profiler = DataProfiler(output_dir=self._profile_dir)

        # Initialize modifier (LLM provider set later)
        self._modifier: Optional[DashboardModifier] = None
        self._llm_provider = None

        logger.info(f"AnalyticsService initialized (upload_dir={self._upload_dir})")

    def set_llm_provider(self, llm_provider: Any) -> None:
        """Set the LLM provider for dashboard modification.

        Args:
            llm_provider: LLM provider instance for modifications
        """
        self._llm_provider = llm_provider
        self._modifier = DashboardModifier(llm_provider=llm_provider)
        logger.info(f"LLM provider set for dashboard modification: {type(llm_provider).__name__}")

    def create_session(
        self,
        user_id: str,
        notebook_id: Optional[str] = None,
    ) -> str:
        """Create a new analysis session.

        Args:
            user_id: User identifier
            notebook_id: Optional notebook association

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())

        session = AnalysisSession(
            session_id=session_id,
            user_id=user_id,
            notebook_id=notebook_id,
            file_name="",
            file_path="",
            file_size=0,
            status="uploaded",
            created_at=datetime.utcnow().isoformat(),
            progress=0,
            # NLP-driven analytics agent fields
            initial_requirements=None,
            generation_prompt=None,
            modification_history=[],
            redo_stack=[],
            last_changes=[],
        )

        self._sessions[session_id] = session
        logger.info(f"Created analytics session: {session_id}")

        return session_id

    def get_session(self, session_id: str) -> Optional[AnalysisSession]:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        user_id: str,
        notebook_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AnalysisSession]:
        """List sessions for a user.

        Args:
            user_id: User identifier
            notebook_id: Optional filter by notebook
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of sessions
        """
        sessions = [
            s for s in self._sessions.values()
            if s.get("user_id") == user_id
        ]

        if notebook_id:
            sessions = [s for s in sessions if s.get("notebook_id") == notebook_id]

        # Sort by created_at descending
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return sessions[offset:offset + limit]

    def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session and its files.

        Args:
            session_id: Session to delete
            user_id: User making the request

        Returns:
            True if deleted, False if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        if session.get("user_id") != user_id:
            return False

        # Delete files
        try:
            file_path = session.get("file_path")
            if file_path:
                Path(file_path).unlink(missing_ok=True)

            # Delete profile report
            profile_path = self._profile_dir / f"{session_id}_profile.html"
            profile_path.unlink(missing_ok=True)

            # Delete session directory
            session_dir = self._upload_dir / session_id
            if session_dir.exists():
                import shutil
                shutil.rmtree(str(session_dir), ignore_errors=True)

        except Exception as e:
            logger.warning(f"Error cleaning up session files: {e}")

        del self._sessions[session_id]
        logger.info(f"Deleted analytics session: {session_id}")

        return True

    def upload_file(
        self,
        session_id: str,
        file_path: Path,
        file_name: str,
    ) -> bool:
        """Register an uploaded file with a session.

        Args:
            session_id: Session ID
            file_path: Path to uploaded file
            file_name: Original filename

        Returns:
            True if successful
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        file_size = file_path.stat().st_size

        session["file_name"] = file_name
        session["file_path"] = str(file_path)
        session["file_size"] = file_size
        session["status"] = "uploaded"
        session["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"File registered for session {session_id}: {file_name}")
        return True

    def parse_file(self, session_id: str) -> Optional[ParsedData]:
        """Parse an uploaded Excel/CSV file.

        Args:
            session_id: Session with uploaded file

        Returns:
            ParsedData or None if error
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return None

        file_path = Path(session.get("file_path", ""))
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            self._update_session_error(session_id, "File not found")
            return None

        try:
            session["status"] = "parsing"
            session["progress"] = 10

            # Read file based on extension
            suffix = file_path.suffix.lower()
            if suffix == ".csv":
                df = pd.read_csv(file_path)
            elif suffix in [".xlsx", ".xls"]:
                df = pd.read_excel(file_path, engine="openpyxl")
            else:
                self._update_session_error(session_id, f"Unsupported file type: {suffix}")
                return None

            logger.info(f"Parsed {len(df)} rows, {len(df.columns)} columns from {file_path.name}")
            session["progress"] = 30

            # Build parsed data
            parsed = self._build_parsed_data(df, session)

            session["parsed_data"] = parsed
            session["progress"] = 40
            session["updated_at"] = datetime.utcnow().isoformat()

            return parsed

        except Exception as e:
            logger.error(f"Error parsing file: {e}")
            self._update_session_error(session_id, str(e))
            return None

    def _build_parsed_data(
        self,
        df: pd.DataFrame,
        session: AnalysisSession,
    ) -> ParsedData:
        """Build ParsedData from DataFrame."""
        # Normalize column names
        df.columns = [str(c).strip() for c in df.columns]

        # Build column metadata
        columns = []
        for col_name in df.columns:
            col = df[col_name]
            inferred_type = self._infer_type(col)

            columns.append(ColumnMetadata(
                name=col_name,
                inferred_type=inferred_type,
                unique_count=int(col.nunique()),
                null_count=int(col.isna().sum()),
                null_percent=round((col.isna().sum() / len(df)) * 100, 2) if len(df) > 0 else 0,
                sample_values=col.dropna().head(5).tolist(),
                statistics=None,
                categorical=None,
            ))

        # Convert to records, handling non-serializable types
        data = df.replace({pd.NA: None, pd.NaT: None}).to_dict("records")
        for row in data:
            for k, v in row.items():
                if pd.isna(v):
                    row[k] = None
                elif hasattr(v, "isoformat"):
                    row[k] = v.isoformat()

        # Sample for LLM
        sample_df = df.head(self._sample_size)
        sample_data = sample_df.replace({pd.NA: None, pd.NaT: None}).to_dict("records")
        # Handle NaN values in sample data (numpy NaN not caught by pd.NA)
        for row in sample_data:
            for k, v in row.items():
                if pd.isna(v):
                    row[k] = None
                elif hasattr(v, "isoformat"):
                    row[k] = v.isoformat()

        return ParsedData(
            data=data,
            columns=columns,
            row_count=len(df),
            column_count=len(df.columns),
            sample_data=sample_data,
            file_name=session.get("file_name", ""),
            file_size=session.get("file_size", 0),
            parsing_errors=[],
        )

    def _infer_type(self, col: pd.Series) -> str:
        """Infer column type."""
        if pd.api.types.is_numeric_dtype(col):
            if col.nunique() < 20 and col.nunique() < len(col) * 0.1:
                return "categorical"
            return "numeric"
        elif pd.api.types.is_datetime64_any_dtype(col):
            return "datetime"
        elif pd.api.types.is_bool_dtype(col):
            return "boolean"
        elif col.nunique() < 50:
            return "categorical"
        return "text"

    def profile_data(self, session_id: str, minimal: bool = False) -> Optional[ProfilingResult]:
        """Generate data profile for a session.

        Args:
            session_id: Session with parsed data
            minimal: If True, generate faster minimal profile

        Returns:
            ProfilingResult or None if error
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        file_path = Path(session.get("file_path", ""))
        if not file_path.exists():
            self._update_session_error(session_id, "File not found for profiling")
            return None

        try:
            session["status"] = "profiling"
            session["progress"] = 50

            # Read data
            suffix = file_path.suffix.lower()
            if suffix == ".csv":
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path, engine="openpyxl")

            # Generate profile
            result = self._profiler.profile(
                df=df,
                session_id=session_id,
                title=f"Profile: {session.get('file_name', 'Dataset')}",
                minimal=minimal,
            )

            session["profiling_result"] = result
            session["progress"] = 70
            session["updated_at"] = datetime.utcnow().isoformat()

            logger.info(f"Profile generated for session {session_id}, quality score: {result.get('quality_score')}")
            return result

        except Exception as e:
            logger.error(f"Error profiling data: {e}")
            self._update_session_error(session_id, str(e))
            return None

    def get_profile_html(self, session_id: str) -> Optional[str]:
        """Get the path to HTML profile report.

        Args:
            session_id: Session ID

        Returns:
            Path to HTML file or None
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        result = session.get("profiling_result")
        if result:
            return result.get("html_report")

        # Check if file exists
        profile_path = self._profile_dir / f"{session_id}_profile.html"
        if profile_path.exists():
            return str(profile_path)

        return None

    def complete_analysis(
        self,
        session_id: str,
        dashboard_config: DashboardConfig,
    ) -> bool:
        """Complete analysis with dashboard configuration.

        Args:
            session_id: Session ID
            dashboard_config: LLM-generated config

        Returns:
            True if successful
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session["dashboard_config"] = dashboard_config
        session["status"] = "complete"
        session["progress"] = 100
        session["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Analysis completed for session {session_id}")
        return True

    def get_data_for_dashboard(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get all data needed to render the dashboard.

        Args:
            session_id: Session ID

        Returns:
            Dict with parsedData, profilingResult, dashboardConfig (camelCase)
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Convert parsed_data to camelCase
        parsed_data = session.get("parsed_data")
        parsed_data_camel = None
        if parsed_data:
            parsed_data_camel = {
                "data": parsed_data.get("data", []),
                "columns": parsed_data.get("columns", []),
                "rowCount": parsed_data.get("row_count", 0),
                "columnCount": parsed_data.get("column_count", 0),
                "sampleData": parsed_data.get("sample_data", []),
                "fileName": parsed_data.get("file_name", ""),
                "fileSize": parsed_data.get("file_size", 0),
                "parsingErrors": parsed_data.get("parsing_errors", []),
            }

        # Convert profiling_result to camelCase
        profiling_result = session.get("profiling_result")
        profiling_result_camel = None
        if profiling_result:
            # Convert overview keys to camelCase
            overview = profiling_result.get("overview", {})
            overview_camel = {
                "rowCount": overview.get("row_count", 0),
                "columnCount": overview.get("column_count", 0),
                "missingCellsPercent": overview.get("missing_cells_percent", 0),
                "duplicateRowsPercent": overview.get("duplicate_rows_percent", 0),
                "memorySize": overview.get("memory_size", "N/A"),
            }
            profiling_result_camel = {
                "overview": overview_camel,
                "columns": profiling_result.get("columns", []),
                "correlations": profiling_result.get("correlations", []),
                "qualityAlerts": profiling_result.get("quality_alerts", []),
                "qualityScore": profiling_result.get("quality_score", 0),
                "htmlReportUrl": profiling_result.get("html_report"),
            }

        return {
            "sessionId": session_id,
            "status": session.get("status"),
            "fileName": session.get("file_name"),
            "parsedData": parsed_data_camel,
            "profilingResult": profiling_result_camel,
            "dashboardConfig": session.get("dashboard_config"),
        }

    def _update_session_error(self, session_id: str, error: str) -> None:
        """Update session with error status."""
        session = self._sessions.get(session_id)
        if session:
            session["status"] = "error"
            session["error_message"] = error
            session["updated_at"] = datetime.utcnow().isoformat()

    # ========================================
    # NLP-Driven Analytics Agent Methods
    # ========================================

    def set_requirements(
        self,
        session_id: str,
        requirements: str,
    ) -> bool:
        """Set initial dashboard requirements before generation.

        Args:
            session_id: Session ID
            requirements: User's natural language requirements

        Returns:
            True if successful
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session["initial_requirements"] = requirements
        session["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Requirements set for session {session_id}: {requirements[:100]}...")
        return True

    def complete_analysis_with_prompt(
        self,
        session_id: str,
        dashboard_config: DashboardConfig,
        generation_prompt: str,
    ) -> bool:
        """Complete analysis with dashboard configuration and store generation prompt.

        Args:
            session_id: Session ID
            dashboard_config: LLM-generated config
            generation_prompt: The prompt used for generation (for modifications)

        Returns:
            True if successful
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session["dashboard_config"] = dashboard_config
        session["generation_prompt"] = generation_prompt
        session["status"] = "complete"
        session["progress"] = 100
        session["updated_at"] = datetime.utcnow().isoformat()
        # Clear modification history on new generation
        session["modification_history"] = []
        session["redo_stack"] = []
        session["last_changes"] = []

        logger.info(f"Analysis completed for session {session_id} with prompt stored")
        return True

    def modify_dashboard(
        self,
        session_id: str,
        instruction: str,
    ) -> ModificationResult:
        """Modify dashboard via NLP instruction.

        The modifier receives:
        - Original generation prompt (data schema + initial requirements)
        - Current dashboard config
        - User's modification instruction

        Args:
            session_id: Session ID
            instruction: Natural language modification instruction

        Returns:
            ModificationResult with new config and changes
        """
        session = self._sessions.get(session_id)
        if not session:
            return ModificationResult(
                success=False,
                dashboard_config=None,
                changes=[],
                error="Session not found",
                can_undo=False,
                can_redo=False,
            )

        current_config = session.get("dashboard_config")
        if not current_config:
            return ModificationResult(
                success=False,
                dashboard_config=None,
                changes=[],
                error="No dashboard configuration to modify",
                can_undo=False,
                can_redo=False,
            )

        generation_prompt = session.get("generation_prompt", "")
        parsed_data = session.get("parsed_data")

        # Initialize modifier if needed
        if self._modifier is None:
            if self._llm_provider:
                self._modifier = DashboardModifier(llm_provider=self._llm_provider)
            else:
                return ModificationResult(
                    success=False,
                    dashboard_config=None,
                    changes=[],
                    error="LLM provider not configured for modifications",
                    can_undo=False,
                    can_redo=False,
                )

        try:
            # Call the modifier
            result = self._modifier.modify(
                current_config=current_config,
                instruction=instruction,
                generation_prompt=generation_prompt,
                parsed_data=parsed_data,
            )

            if result.get("success"):
                # Push current config to history for undo
                history = session.get("modification_history", [])
                history.append(current_config)
                session["modification_history"] = history

                # Clear redo stack (new branch of history)
                session["redo_stack"] = []

                # Update session with new config
                session["dashboard_config"] = result["dashboard_config"]
                session["last_changes"] = result.get("changes", [])
                session["updated_at"] = datetime.utcnow().isoformat()

                logger.info(f"Dashboard modified for session {session_id}: {len(result.get('changes', []))} changes")

                return ModificationResult(
                    success=True,
                    dashboard_config=result["dashboard_config"],
                    changes=result.get("changes", []),
                    error=None,
                    can_undo=len(session.get("modification_history", [])) > 0,
                    can_redo=False,
                )

            return result

        except Exception as e:
            logger.error(f"Error modifying dashboard: {e}")
            return ModificationResult(
                success=False,
                dashboard_config=None,
                changes=[],
                error=str(e),
                can_undo=len(session.get("modification_history", [])) > 0,
                can_redo=len(session.get("redo_stack", [])) > 0,
            )

    def undo_modification(self, session_id: str) -> ModificationResult:
        """Undo the last dashboard modification.

        Args:
            session_id: Session ID

        Returns:
            ModificationResult with restored config
        """
        session = self._sessions.get(session_id)
        if not session:
            return ModificationResult(
                success=False,
                dashboard_config=None,
                changes=[],
                error="Session not found",
                can_undo=False,
                can_redo=False,
            )

        history = session.get("modification_history", [])
        if not history:
            return ModificationResult(
                success=False,
                dashboard_config=session.get("dashboard_config"),
                changes=[],
                error="Nothing to undo",
                can_undo=False,
                can_redo=len(session.get("redo_stack", [])) > 0,
            )

        # Pop from history, push current to redo
        current_config = session.get("dashboard_config")
        redo_stack = session.get("redo_stack", [])
        redo_stack.append(current_config)
        session["redo_stack"] = redo_stack

        # Restore previous config
        previous_config = history.pop()
        session["modification_history"] = history
        session["dashboard_config"] = previous_config
        session["last_changes"] = ["Undid last modification"]
        session["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Undo performed for session {session_id}")

        return ModificationResult(
            success=True,
            dashboard_config=previous_config,
            changes=["Undid last modification"],
            error=None,
            can_undo=len(history) > 0,
            can_redo=True,
        )

    def redo_modification(self, session_id: str) -> ModificationResult:
        """Redo a previously undone modification.

        Args:
            session_id: Session ID

        Returns:
            ModificationResult with restored config
        """
        session = self._sessions.get(session_id)
        if not session:
            return ModificationResult(
                success=False,
                dashboard_config=None,
                changes=[],
                error="Session not found",
                can_undo=False,
                can_redo=False,
            )

        redo_stack = session.get("redo_stack", [])
        if not redo_stack:
            return ModificationResult(
                success=False,
                dashboard_config=session.get("dashboard_config"),
                changes=[],
                error="Nothing to redo",
                can_undo=len(session.get("modification_history", [])) > 0,
                can_redo=False,
            )

        # Pop from redo, push current to history
        current_config = session.get("dashboard_config")
        history = session.get("modification_history", [])
        history.append(current_config)
        session["modification_history"] = history

        # Restore redo config
        next_config = redo_stack.pop()
        session["redo_stack"] = redo_stack
        session["dashboard_config"] = next_config
        session["last_changes"] = ["Redid modification"]
        session["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Redo performed for session {session_id}")

        return ModificationResult(
            success=True,
            dashboard_config=next_config,
            changes=["Redid modification"],
            error=None,
            can_undo=True,
            can_redo=len(redo_stack) > 0,
        )

    def get_modification_state(self, session_id: str) -> Dict[str, Any]:
        """Get current modification state for UI.

        Args:
            session_id: Session ID

        Returns:
            Dict with canUndo, canRedo, lastChanges
        """
        session = self._sessions.get(session_id)
        if not session:
            return {
                "canUndo": False,
                "canRedo": False,
                "lastChanges": [],
                "initialRequirements": None,
            }

        return {
            "canUndo": len(session.get("modification_history", [])) > 0,
            "canRedo": len(session.get("redo_stack", [])) > 0,
            "lastChanges": session.get("last_changes", []),
            "initialRequirements": session.get("initial_requirements"),
        }
