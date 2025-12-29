"""API routes for agentic features - query analysis and document suggestions."""

import logging
from flask import Blueprint, request, jsonify

from dbnotebook.core.agents import QueryAnalyzer, DocumentAnalyzer

logger = logging.getLogger(__name__)

# Blueprint for agent endpoints
agents_bp = Blueprint('agents', __name__, url_prefix='/api/agents')

# Lazy initialization of agents
_query_analyzer = None
_document_analyzer = None


def get_query_analyzer(pipeline=None):
    """
    Get or create QueryAnalyzer instance.

    Args:
        pipeline: Optional LocalRAGPipeline instance

    Returns:
        QueryAnalyzer instance
    """
    global _query_analyzer
    if _query_analyzer is None:
        _query_analyzer = QueryAnalyzer(pipeline)
    elif pipeline and _query_analyzer.pipeline != pipeline:
        # Update pipeline if changed
        _query_analyzer.pipeline = pipeline
    return _query_analyzer


def get_document_analyzer(pipeline=None):
    """
    Get or create DocumentAnalyzer instance.

    Args:
        pipeline: Optional LocalRAGPipeline instance

    Returns:
        DocumentAnalyzer instance
    """
    global _document_analyzer
    if _document_analyzer is None:
        _document_analyzer = DocumentAnalyzer(pipeline)
    elif pipeline and _document_analyzer.pipeline != pipeline:
        # Update pipeline if changed
        _document_analyzer.pipeline = pipeline
    return _document_analyzer


@agents_bp.route('/analyze-query', methods=['POST'])
def analyze_query():
    """
    Analyze a query for intent and suggest refinements.

    Request body:
        {
            "query": "user query text",
            "history": [] (optional)
        }

    Response:
        {
            "query": "original query",
            "intent": "factual|comparison|exploration|action|clarification",
            "complexity": 0.0-1.0,
            "suggested_refinements": ["refinement 1", ...],
            "confidence": 0.0-1.0
        }
    """
    try:
        data = request.get_json()
        query = data.get('query', '')

        if not query:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400

        analyzer = get_query_analyzer()
        result = analyzer.analyze(query)

        return jsonify({
            'success': True,
            **result
        })

    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/suggest-sources', methods=['POST'])
def suggest_sources():
    """
    Suggest documents to add based on notebook context.

    Request body:
        {
            "notebook_id": "uuid",
            "query_history": ["query1", "query2", ...] (optional),
            "documents": [{"file_name": "...", ...}, ...] (optional)
        }

    Response:
        {
            "success": true,
            "notebook_id": "uuid",
            "document_count": 5,
            "coverage_score": 0.75,
            "gaps": ["gap1", "gap2", ...],
            "suggestions": [
                {
                    "type": "add_document",
                    "reason": "Missing coverage for X",
                    "action": "search_web",
                    "query": "search query"
                },
                ...
            ]
        }
    """
    try:
        data = request.get_json()
        notebook_id = data.get('notebook_id')
        query_history = data.get('query_history', [])
        documents = data.get('documents', [])

        if not notebook_id:
            return jsonify({
                'success': False,
                'error': 'Notebook ID is required'
            }), 400

        analyzer = get_document_analyzer()
        result = analyzer.analyze({
            'notebook_id': notebook_id,
            'query_history': query_history,
            'documents': documents
        })

        return jsonify({
            'success': True,
            **result
        })

    except Exception as e:
        logger.error(f"Error suggesting sources: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/refine-query', methods=['POST'])
def refine_query():
    """
    Get refined query suggestions based on context.

    Request body:
        {
            "query": "user query text",
            "history": [] (optional),
            "notebook_context": {} (optional)
        }

    Response:
        {
            "success": true,
            "suggestions": [
                {
                    "type": "specificity|follow_up|...",
                    "text": "suggested query text",
                    "reason": "why this suggestion is made"
                },
                ...
            ]
        }
    """
    try:
        data = request.get_json()
        query = data.get('query', '')
        history = data.get('history', [])
        notebook_context = data.get('notebook_context', {})

        if not query:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400

        analyzer = get_query_analyzer()
        suggestions = analyzer.suggest({
            'query': query,
            'history': history,
            'notebook_context': notebook_context
        })

        return jsonify({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        logger.error(f"Error refining query: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/health', methods=['GET'])
def health():
    """
    Health check for agent services.

    Response:
        {
            "success": true,
            "agents": {
                "query_analyzer": "initialized|not_initialized",
                "document_analyzer": "initialized|not_initialized"
            }
        }
    """
    return jsonify({
        'success': True,
        'agents': {
            'query_analyzer': 'initialized' if _query_analyzer else 'not_initialized',
            'document_analyzer': 'initialized' if _document_analyzer else 'not_initialized'
        }
    })


def create_agent_routes(app, pipeline=None):
    """
    Register agent routes with Flask app.

    Args:
        app: Flask application instance
        pipeline: Optional LocalRAGPipeline instance for LLM access
    """
    # Initialize agents with pipeline if provided
    if pipeline:
        get_query_analyzer(pipeline)
        get_document_analyzer(pipeline)

    # Register blueprint
    app.register_blueprint(agents_bp)
    logger.info("Agent API routes registered")
