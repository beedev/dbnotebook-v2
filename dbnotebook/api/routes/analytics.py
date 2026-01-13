"""Analytics API routes for Excel data profiling and visualization.

Provides endpoints for:
- Uploading Excel files for analysis
- Parsing and profiling data with ydata-profiling
- Retrieving profiling HTML reports
- Managing analysis sessions
- Exporting dashboards to PDF
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

from ...core.analytics import AnalyticsService, DashboardConfigGenerator
from ...core.constants import DEFAULT_USER_ID

logger = logging.getLogger(__name__)

# Blueprint for analytics endpoints
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

# Project root directory for resolving relative paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Allowed Excel extensions
ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv'}

# Analytics service instance (initialized in create_analytics_routes)
_analytics_service: Optional[AnalyticsService] = None

# Pipeline instance for LLM access (set in create_analytics_routes)
_pipeline = None


def allowed_file(filename: str) -> bool:
    """Check if file has an allowed extension for analysis."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def get_current_user_id() -> str:
    """Get current user ID from request context.

    Returns:
        User ID string. Currently returns default user ID.
        Will be replaced with proper auth integration.
    """
    # TODO: Integrate with actual authentication system
    return DEFAULT_USER_ID


def get_service() -> AnalyticsService:
    """Get the analytics service instance."""
    global _analytics_service
    if _analytics_service is None:
        # Initialize with default directories
        _analytics_service = AnalyticsService(
            upload_dir=PROJECT_ROOT / 'uploads' / 'analytics',
            profile_dir=PROJECT_ROOT / 'uploads' / 'analytics' / 'profiles',
        )
    return _analytics_service


@analytics_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload an Excel file for analysis.

    Request:
        Multipart form data with:
        - file: Excel file (.xlsx, .xls, .csv)

        Query params:
        - notebook_id: Optional notebook UUID to associate with

    Response JSON:
        {
            "success": true,
            "session_id": "uuid",
            "status": "uploaded",
            "metadata": {
                "file_name": "data.xlsx",
                "file_size": 12345,
                "uploaded_at": "2024-01-01T00:00:00"
            }
        }
    """
    try:
        service = get_service()

        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Supported: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # Get optional notebook_id
        notebook_id = request.args.get('notebook_id')

        # Get current user
        user_id = get_current_user_id()

        # Create session
        session_id = service.create_session(
            user_id=user_id,
            notebook_id=notebook_id,
        )

        # Secure the filename
        filename = secure_filename(file.filename)

        # Create upload directory for this session
        upload_dir = PROJECT_ROOT / 'uploads' / 'analytics' / session_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save the file
        file_path = upload_dir / filename
        file.save(str(file_path))

        # Register file with session
        service.upload_file(
            session_id=session_id,
            file_path=file_path,
            file_name=filename,
        )

        # Get session for response
        session = service.get_session(session_id)

        logger.info(f"Analytics file uploaded: {filename} (session: {session_id})")

        return jsonify({
            'success': True,
            'sessionId': session_id,
            'status': 'uploaded',
            'metadata': {
                'fileName': filename,
                'fileSize': session.get('file_size', 0),
                'uploadedAt': session.get('created_at', '')
            }
        })

    except Exception as e:
        logger.error(f"Error uploading analytics file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/parse/<session_id>', methods=['POST'])
def parse_file(session_id: str):
    """
    Parse an uploaded Excel/CSV file.

    Response JSON:
        {
            "success": true,
            "session_id": "uuid",
            "status": "parsed",
            "parsed_data": {
                "row_count": 1000,
                "column_count": 15,
                "columns": [...],
                "sample_data": [...]
            }
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        # Parse the file
        parsed_data = service.parse_file(session_id)

        # Debug logging for parse response
        logger.info(f"[PARSE API] parsed_data type: {type(parsed_data)}")
        logger.info(f"[PARSE API] parsed_data keys: {parsed_data.keys() if parsed_data else 'None'}")
        if parsed_data:
            data_val = parsed_data.get('data', [])
            logger.info(f"[PARSE API] data length: {len(data_val) if data_val else 0}")
            logger.info(f"[PARSE API] row_count: {parsed_data.get('row_count', 0)}")

        if not parsed_data:
            session = service.get_session(session_id)
            return jsonify({
                'success': False,
                'error': session.get('error_message', 'Failed to parse file'),
                'status': session.get('status')
            }), 400

        # Return parsed data with full data array for dashboard rendering
        return jsonify({
            'success': True,
            'sessionId': session_id,
            'status': 'parsed',
            'parsedData': {
                'data': parsed_data.get('data', []),
                'rowCount': parsed_data.get('row_count', 0),
                'columnCount': parsed_data.get('column_count', 0),
                'columns': parsed_data.get('columns', []),
                'sampleData': parsed_data.get('sample_data', []),
                'fileName': parsed_data.get('file_name', ''),
                'fileSize': parsed_data.get('file_size', 0),
                'parsingErrors': parsed_data.get('parsing_errors', []),
            }
        })

    except Exception as e:
        logger.error(f"Error parsing file for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/profile/<session_id>', methods=['POST'])
def generate_profile(session_id: str):
    """
    Generate ydata profiling report for a session.

    Query params:
        - minimal: If "true", generate faster minimal profile

    Response JSON:
        {
            "success": true,
            "session_id": "uuid",
            "status": "profiled",
            "profiling_result": {
                "overview": {...},
                "columns": [...],
                "correlations": [...],
                "quality_score": 8.5,
                "html_report": "/api/analytics/profile/uuid/html"
            }
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        # Check if minimal mode
        minimal = request.args.get('minimal', 'false').lower() == 'true'

        # Generate profile
        profiling_result = service.profile_data(session_id, minimal=minimal)

        if not profiling_result:
            session = service.get_session(session_id)
            return jsonify({
                'success': False,
                'error': session.get('error_message', 'Failed to generate profile'),
                'status': session.get('status')
            }), 400

        # Build response with camelCase keys
        overview = profiling_result.get('overview', {})
        overview_camel = {
            'rowCount': overview.get('row_count', 0),
            'columnCount': overview.get('column_count', 0),
            'missingCellsPercent': overview.get('missing_cells_percent', 0),
            'duplicateRowsPercent': overview.get('duplicate_rows_percent', 0),
            'memorySize': overview.get('memory_size', 'N/A'),
        }
        response_data = {
            'success': True,
            'sessionId': session_id,
            'status': 'profiled',
            'profilingResult': {
                'overview': overview_camel,
                'columns': profiling_result.get('columns', []),
                'correlations': profiling_result.get('correlations', []),
                'qualityAlerts': profiling_result.get('quality_alerts', []),
                'qualityScore': profiling_result.get('quality_score', 0),
            }
        }

        # Add HTML report URL if available
        if profiling_result.get('html_report'):
            response_data['profilingResult']['htmlReportUrl'] = f"/api/analytics/profile/{session_id}/html"

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error generating profile for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/profile/<session_id>/html', methods=['GET'])
def get_profile_html(session_id: str):
    """
    Get ydata HTML profiling report for a session.

    Response:
        HTML file (ydata profile report) or 404 if not found/not ready.
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        # Get profile HTML path
        profile_path = service.get_profile_html(session_id)

        if not profile_path:
            return jsonify({
                'success': False,
                'error': 'Profile not yet generated',
                'status': session.get('status')
            }), 404

        # Check if file exists
        profile_file = Path(profile_path)
        if not profile_file.exists():
            return jsonify({
                'success': False,
                'error': 'Profile file not found'
            }), 404

        # Serve the HTML report
        return send_file(
            profile_file,
            mimetype='text/html',
            as_attachment=False
        )

    except Exception as e:
        logger.error(f"Error getting profile HTML for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/analyze/<session_id>', methods=['POST'])
def analyze_dashboard(session_id: str):
    """
    Generate AI-powered dashboard configuration for a session.

    This endpoint uses the LLM to analyze the profiled data and
    generate an optimal dashboard configuration with KPIs, charts,
    and filters.

    Request JSON (optional):
        {
            "title": "Custom Dashboard Title",
            "requirements": "Show me sales trends and top performers"
        }

    Response JSON:
        {
            "success": true,
            "session_id": "uuid",
            "status": "complete",
            "dashboard_config": {
                "kpis": [...],
                "charts": [...],
                "filters": [...],
                "metadata": {...}
            }
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        # Check if we have parsed data and profiling result
        parsed_data = session.get('parsed_data')
        profiling_result = session.get('profiling_result')

        if not parsed_data:
            return jsonify({
                'success': False,
                'error': 'Data not parsed yet. Call /parse first.',
                'status': session.get('status')
            }), 400

        if not profiling_result:
            return jsonify({
                'success': False,
                'error': 'Data not profiled yet. Call /profile first.',
                'status': session.get('status')
            }), 400

        # Get optional parameters
        data = request.get_json() or {}
        title = data.get('title')
        initial_requirements = data.get('requirements') or session.get('initial_requirements')

        # Update session status
        session['status'] = 'analyzing'
        session['progress'] = 80

        # Get LLM provider from pipeline if available
        llm_provider = None
        if _pipeline is not None:
            try:
                llm_provider = _pipeline._default_model
                logger.info(f"Using pipeline LLM for dashboard generation: {type(llm_provider).__name__}")
                # Set LLM provider on service for modifications
                service.set_llm_provider(llm_provider)
            except Exception as e:
                logger.warning(f"Could not get LLM from pipeline: {e}")

        # Generate dashboard configuration
        generator = DashboardConfigGenerator(llm_provider=llm_provider)
        dashboard_config, generation_prompt = generator.generate(
            parsed_data=parsed_data,
            profiling_result=profiling_result,
            title=title,
            initial_requirements=initial_requirements,
        )

        # Complete the analysis with generation prompt stored
        service.complete_analysis_with_prompt(session_id, dashboard_config, generation_prompt)

        logger.info(f"Dashboard analysis completed for session {session_id}")

        # Debug logging
        logger.info(f"[ANALYZE API] dashboard_config keys: {dashboard_config.keys()}")
        logger.info(f"[ANALYZE API] kpis count: {len(dashboard_config.get('kpis', []))}")
        logger.info(f"[ANALYZE API] charts count: {len(dashboard_config.get('charts', []))}")
        logger.info(f"[ANALYZE API] filters count: {len(dashboard_config.get('filters', []))}")
        logger.info(f"[ANALYZE API] kpis: {dashboard_config.get('kpis', [])}")
        logger.info(f"[ANALYZE API] charts: {dashboard_config.get('charts', [])}")

        # Get modification state
        mod_state = service.get_modification_state(session_id)

        return jsonify({
            'success': True,
            'sessionId': session_id,
            'status': 'complete',
            'dashboardConfig': dashboard_config,
            'modificationState': mod_state
        })

    except Exception as e:
        logger.error(f"Error analyzing dashboard for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/sessions/<session_id>/requirements', methods=['POST'])
def set_requirements(session_id: str):
    """
    Set initial dashboard requirements before generation.

    Request JSON:
        {
            "requirements": "Show me sales trends and top customers by region"
        }

    Response JSON:
        {
            "success": true,
            "message": "Requirements set successfully"
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        data = request.get_json() or {}
        requirements = data.get('requirements', '').strip()

        if not requirements:
            return jsonify({
                'success': False,
                'error': 'requirements field is required'
            }), 400

        # Set requirements
        success = service.set_requirements(session_id, requirements)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to set requirements'
            }), 500

        logger.info(f"Requirements set for session {session_id}")

        return jsonify({
            'success': True,
            'message': 'Requirements set successfully',
            'requirements': requirements
        })

    except Exception as e:
        logger.error(f"Error setting requirements for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/sessions/<session_id>/modify', methods=['POST'])
def modify_dashboard(session_id: str):
    """
    Modify dashboard via NLP instruction.

    The LLM receives the original generation context + current config +
    the modification instruction, allowing it to make any changes
    (add, remove, edit elements).

    Request JSON:
        {
            "instruction": "Add a pie chart showing distribution by region"
        }

    Response JSON:
        {
            "success": true,
            "dashboardConfig": {...},
            "changes": ["Added pie chart 'Region Distribution'"],
            "canUndo": true,
            "canRedo": false
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        # Ensure LLM provider is set
        if _pipeline is not None:
            try:
                llm_provider = _pipeline._default_model
                service.set_llm_provider(llm_provider)
            except Exception as e:
                logger.warning(f"Could not set LLM provider: {e}")

        data = request.get_json() or {}
        instruction = data.get('instruction', '').strip()

        if not instruction:
            return jsonify({
                'success': False,
                'error': 'instruction field is required'
            }), 400

        # Modify dashboard
        result = service.modify_dashboard(session_id, instruction)

        if result.get('success'):
            return jsonify({
                'success': True,
                'dashboardConfig': result.get('dashboard_config'),
                'changes': result.get('changes', []),
                'canUndo': result.get('can_undo', False),
                'canRedo': result.get('can_redo', False)
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Modification failed'),
                'canUndo': result.get('can_undo', False),
                'canRedo': result.get('can_redo', False)
            }), 400

    except Exception as e:
        logger.error(f"Error modifying dashboard for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/sessions/<session_id>/undo', methods=['POST'])
def undo_modification(session_id: str):
    """
    Undo the last dashboard modification.

    Response JSON:
        {
            "success": true,
            "dashboardConfig": {...},
            "changes": ["Undid last modification"],
            "canUndo": false,
            "canRedo": true
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        # Undo modification
        result = service.undo_modification(session_id)

        return jsonify({
            'success': result.get('success', False),
            'dashboardConfig': result.get('dashboard_config'),
            'changes': result.get('changes', []),
            'canUndo': result.get('can_undo', False),
            'canRedo': result.get('can_redo', False),
            'error': result.get('error')
        })

    except Exception as e:
        logger.error(f"Error undoing modification for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/sessions/<session_id>/redo', methods=['POST'])
def redo_modification(session_id: str):
    """
    Redo a previously undone modification.

    Response JSON:
        {
            "success": true,
            "dashboardConfig": {...},
            "changes": ["Redid modification"],
            "canUndo": true,
            "canRedo": false
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        # Redo modification
        result = service.redo_modification(session_id)

        return jsonify({
            'success': result.get('success', False),
            'dashboardConfig': result.get('dashboard_config'),
            'changes': result.get('changes', []),
            'canUndo': result.get('can_undo', False),
            'canRedo': result.get('can_redo', False),
            'error': result.get('error')
        })

    except Exception as e:
        logger.error(f"Error redoing modification for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/sessions/<session_id>/modification-state', methods=['GET'])
def get_modification_state(session_id: str):
    """
    Get current modification state for UI.

    Response JSON:
        {
            "success": true,
            "canUndo": true,
            "canRedo": false,
            "lastChanges": ["Added chart..."],
            "initialRequirements": "Show sales trends..."
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        # Get modification state
        state = service.get_modification_state(session_id)

        return jsonify({
            'success': True,
            **state
        })

    except Exception as e:
        logger.error(f"Error getting modification state for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/status/<session_id>', methods=['GET'])
def get_status(session_id: str):
    """
    Get current status and progress of an analysis session.

    Response JSON:
        {
            "success": true,
            "session_id": "uuid",
            "status": "profiling",
            "progress": 50,
            "file_name": "data.xlsx"
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        return jsonify({
            'success': True,
            'sessionId': session_id,
            'status': session.get('status', 'unknown'),
            'progress': session.get('progress', 0),
            'fileName': session.get('file_name', ''),
            'errorMessage': session.get('error_message'),
        })

    except Exception as e:
        logger.error(f"Error getting status for session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """
    List user's analysis sessions.

    Query params:
        - limit: Max results (default 50, max 100)
        - offset: Pagination offset (default 0)
        - notebook_id: Optional filter by notebook

    Response JSON:
        {
            "success": true,
            "sessions": [
                {
                    "session_id": "uuid",
                    "file_name": "data.xlsx",
                    "status": "completed",
                    "created_at": "2024-01-01T00:00:00",
                    "notebook_id": "uuid" | null
                }
            ],
            "total": 10,
            "limit": 50,
            "offset": 0
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Parse query params
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        notebook_id = request.args.get('notebook_id')

        # Get sessions
        sessions = service.list_sessions(
            user_id=user_id,
            notebook_id=notebook_id,
            limit=limit,
            offset=offset,
        )

        # Format response
        sessions_list = [
            {
                'sessionId': s.get('session_id'),
                'fileName': s.get('file_name'),
                'status': s.get('status'),
                'progress': s.get('progress', 0),
                'createdAt': s.get('created_at'),
                'notebookId': s.get('notebook_id')
            }
            for s in sessions
        ]

        return jsonify({
            'success': True,
            'sessions': sessions_list,
            'total': len(sessions_list),
            'limit': limit,
            'offset': offset
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'Invalid parameter: {e}'
        }), 400
    except Exception as e:
        logger.error(f"Error listing analytics sessions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """
    Get details for a specific session including all data.

    Response JSON:
        {
            "success": true,
            "session": {
                "session_id": "uuid",
                "file_name": "data.xlsx",
                "file_size": 12345,
                "status": "completed",
                "created_at": "2024-01-01T00:00:00",
                "notebook_id": "uuid" | null,
                "profile_url": "/api/analytics/profile/uuid/html",
                "parsed_data": {...},
                "profiling_result": {...},
                "dashboard_config": {...}
            }
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        # Build response
        response_data = {
            'sessionId': session.get('session_id'),
            'fileName': session.get('file_name'),
            'fileSize': session.get('file_size'),
            'status': session.get('status'),
            'progress': session.get('progress', 0),
            'createdAt': session.get('created_at'),
            'updatedAt': session.get('updated_at'),
            'notebookId': session.get('notebook_id'),
            'errorMessage': session.get('error_message'),
        }

        # Add parsed data if available
        if session.get('parsed_data'):
            parsed = session['parsed_data']
            response_data['parsedData'] = {
                'rowCount': parsed.get('row_count', 0),
                'columnCount': parsed.get('column_count', 0),
                'columns': parsed.get('columns', []),
            }

        # Add profiling result if available
        if session.get('profiling_result'):
            result = session['profiling_result']
            response_data['profilingResult'] = {
                'overview': result.get('overview', {}),
                'qualityScore': result.get('quality_score', 0),
                'correlations': result.get('correlations', []),
                'qualityAlerts': result.get('quality_alerts', []),
            }
            response_data['profileUrl'] = f"/api/analytics/profile/{session_id}/html"

        # Add dashboard config if available
        if session.get('dashboard_config'):
            response_data['dashboardConfig'] = session['dashboard_config']

        return jsonify({
            'success': True,
            'session': response_data
        })

    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/sessions/<session_id>/data', methods=['GET'])
def get_session_data(session_id: str):
    """
    Get all data needed to render the dashboard.

    Response JSON:
        {
            "success": true,
            "session_id": "uuid",
            "status": "complete",
            "file_name": "data.xlsx",
            "parsed_data": {...},
            "profiling_result": {...},
            "dashboard_config": {...}
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        # Get dashboard data
        data = service.get_data_for_dashboard(session_id)

        if not data:
            return jsonify({
                'success': False,
                'error': 'Session data not available'
            }), 404

        return jsonify({
            'success': True,
            **data
        })

    except Exception as e:
        logger.error(f"Error getting session data {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """
    Delete an analysis session and its associated files.

    Response JSON:
        {
            "success": true,
            "message": "Session deleted successfully"
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Delete session
        success = service.delete_session(session_id, user_id)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Session not found or access denied'
            }), 404

        logger.info(f"Analytics session deleted: {session_id}")

        return jsonify({
            'success': True,
            'message': 'Session deleted successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/export', methods=['POST'])
def export_dashboard():
    """
    Export dashboard visualization to PDF.

    Request JSON:
        {
            "session_id": "uuid",
            "dashboard_state": {
                "selected_charts": [...],
                "filters": {...},
                "layout": {...}
            }
        }

    Response:
        PDF file download or error JSON
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        data = request.get_json() or {}

        session_id = data.get('session_id')
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id is required'
            }), 400

        # Get session
        session = service.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        # Check user access
        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        dashboard_state = data.get('dashboard_state', {})

        # TODO: Implement actual PDF export
        # For now, return a placeholder response
        logger.info(f"PDF export requested for session {session_id}")

        return jsonify({
            'success': False,
            'error': 'PDF export not yet implemented',
            'message': 'This feature will be available in a future release'
        }), 501

    except Exception as e:
        logger.error(f"Error exporting dashboard: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/health', methods=['GET'])
def health():
    """
    Health check for analytics service.

    Response JSON:
        {
            "success": true,
            "status": "healthy",
            "service_initialized": true
        }
    """
    try:
        service = get_service()
        return jsonify({
            'success': True,
            'status': 'healthy',
            'service_initialized': service is not None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


def create_analytics_routes(app, db_manager=None, analytics_service=None, pipeline=None):
    """
    Register analytics routes with Flask app.

    Args:
        app: Flask application instance
        db_manager: Optional DatabaseManager instance for persistence
        analytics_service: Optional AnalyticsService for data processing
        pipeline: Optional LocalRAGPipeline for LLM access in dashboard generation
    """
    global _analytics_service, _pipeline

    # Store pipeline reference for LLM access
    _pipeline = pipeline

    # Use provided service or create new one
    if analytics_service:
        _analytics_service = analytics_service
    else:
        _analytics_service = AnalyticsService(
            upload_dir=PROJECT_ROOT / 'uploads' / 'analytics',
            profile_dir=PROJECT_ROOT / 'uploads' / 'analytics' / 'profiles',
        )

    # Register blueprint
    app.register_blueprint(analytics_bp)
    logger.info("Analytics API routes registered")

    return app
