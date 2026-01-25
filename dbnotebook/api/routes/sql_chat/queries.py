"""SQL Chat query execution routes.

Endpoints for natural language to SQL query execution:
- Execute queries (sync)
- Execute queries with SSE streaming
- Get query history
"""

import json
import logging
import asyncio

from flask import Blueprint, Response, request

from dbnotebook.api.core.response import (
    success_response, error_response, validation_error
)

from .utils import get_service, get_current_user_id, SQLChatJSONEncoder

logger = logging.getLogger(__name__)

# Blueprint for query endpoints
queries_bp = Blueprint('sql_chat_queries', __name__)


@queries_bp.route('/query/<session_id>', methods=['POST'])
def execute_query(session_id: str):
    """
    Execute a natural language query against the database.

    Request JSON:
        {
            "query": "Show me the top 10 customers by revenue",
            "user_id": "uuid",  // Optional for multi-user (uses default if omitted)
            "use_reranker": true,  // Optional: enable/disable reranking for few-shot
            "reranker_model": "base",  // Optional: xsmall, base, large
            "top_k": 5,  // Optional: number of few-shot examples
            "use_hybrid": true  // Optional: enable hybrid BM25+vector search
        }

    Response JSON:
        {
            "success": true,
            "result": {
                "sqlGenerated": "SELECT ...",
                "data": [...],
                "columns": [...],
                "rowCount": 10,
                "executionTimeMs": 45,
                "confidence": {
                    "score": 0.85,
                    "level": "high",
                    "factors": {...}
                },
                "intent": {
                    "type": "top_k",
                    "confidence": 0.9
                }
            }
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}
        user_id = get_current_user_id()

        nl_query = data.get('query', '').strip()
        if not nl_query:
            return validation_error('query is required')

        # Extract query settings
        query_settings = {
            'use_reranker': data.get('use_reranker'),
            'reranker_model': data.get('reranker_model'),
            'top_k': data.get('top_k'),
            'use_hybrid': data.get('use_hybrid'),
        }
        # Remove None values
        query_settings = {k: v for k, v in query_settings.items() if v is not None}

        # Execute query with user validation (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.execute_query(session_id, nl_query, user_id, **query_settings)
            )
        finally:
            loop.close()

        # Format response
        response_data = {
            'result': {
                'sqlGenerated': result.sql_generated,
                'data': result.data,
                'columns': [
                    {
                        'name': c.name,
                        'type': c.type
                    }
                    for c in result.columns
                ],
                'rowCount': result.row_count,
                'executionTimeMs': result.execution_time_ms,
                'errorMessage': result.error_message
            }
        }

        # Add confidence if available
        if result.confidence:
            response_data['result']['confidence'] = {
                'score': result.confidence.score,
                'level': result.confidence.level,
                'factors': result.confidence.factors
            }

        # Add intent if available
        if result.intent:
            response_data['result']['intent'] = {
                'type': result.intent.intent.value,
                'confidence': result.intent.confidence,
                'hints': result.intent.prompt_hints
            }

        # Add cost estimate if available
        if result.cost_estimate:
            response_data['result']['costEstimate'] = {
                'totalCost': result.cost_estimate.total_cost,
                'estimatedRows': result.cost_estimate.estimated_rows,
                'hasSeqScan': result.cost_estimate.has_seq_scan,
                'hasCartesian': result.cost_estimate.has_cartesian
            }

        # Add validation warnings if available
        if result.validation_warnings:
            response_data['result']['validationWarnings'] = result.validation_warnings

        # Add per-stage timings if available
        if result.timings:
            response_data['result']['timings'] = result.timings

        if result.success:
            return success_response(response_data)
        else:
            return error_response(result.error_message or 'Query failed', 400, **response_data)

    except Exception as e:
        logger.error(f"Error executing query in session {session_id}: {e}")
        return error_response(str(e), 500)


@queries_bp.route('/query/<session_id>/stream', methods=['POST'])
def execute_query_stream(session_id: str):
    """
    Execute a natural language query with SSE streaming.

    Request JSON:
        {
            "query": "Show me the top 10 customers by revenue",
            "user_id": "uuid",  // Optional for multi-user (uses default if omitted)
            "use_reranker": true,  // Optional: enable/disable reranking for few-shot
            "reranker_model": "base",  // Optional: xsmall, base, large
            "top_k": 5,  // Optional: number of few-shot examples
            "use_hybrid": true  // Optional: enable hybrid BM25+vector search
        }

    Response:
        SSE stream with events:
        - status: Current processing status
        - sql: Generated SQL query
        - result: Final query result
        - error: Error message if failed
    """
    try:
        service = get_service()
        data = request.get_json() or {}
        user_id = get_current_user_id()

        nl_query = data.get('query', '').strip()
        if not nl_query:
            return validation_error('query is required')

        # Extract query settings
        query_settings = {
            'use_reranker': data.get('use_reranker'),
            'reranker_model': data.get('reranker_model'),
            'top_k': data.get('top_k'),
            'use_hybrid': data.get('use_hybrid'),
        }
        # Remove None values
        query_settings = {k: v for k, v in query_settings.items() if v is not None}

        def generate():
            """Generate SSE events for query execution."""
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'status': 'generating'}, cls=SQLChatJSONEncoder)}\n\n"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    service.execute_query(session_id, nl_query, user_id, **query_settings)
                )

                # Send SQL generated
                yield f"data: {json.dumps({'type': 'sql', 'sql': result.sql_generated}, cls=SQLChatJSONEncoder)}\n\n"

                # Send final result (uses custom encoder to handle UUID, datetime, Decimal)
                response = {
                    'type': 'result',
                    'success': result.success,
                    'sql': result.sql_generated,
                    'data': result.data,
                    'columns': [{'name': c.name, 'type': c.type} for c in result.columns],
                    'rowCount': result.row_count,
                    'executionTimeMs': result.execution_time_ms,
                    'errorMessage': result.error_message
                }

                if result.confidence:
                    response['confidence'] = {
                        'score': result.confidence.score,
                        'level': result.confidence.level
                    }

                if result.explanation:
                    response['explanation'] = result.explanation

                # Add validation warnings if available
                if result.validation_warnings:
                    response['validationWarnings'] = result.validation_warnings

                # Add per-stage timings if available
                if result.timings:
                    response['timings'] = result.timings

                yield f"data: {json.dumps(response, cls=SQLChatJSONEncoder)}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, cls=SQLChatJSONEncoder)}\n\n"
            finally:
                loop.close()

            yield "data: [DONE]\n\n"

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )

    except Exception as e:
        logger.error(f"Error streaming query in session {session_id}: {e}")
        return error_response(str(e), 500)


@queries_bp.route('/history/<session_id>', methods=['GET'])
def get_query_history(session_id: str):
    """
    Get query history for a session.

    Multi-user safe: Validates user has access to the session.

    Query params:
        - limit: Max results (default 50)
        - user_id: Optional user ID for access validation

    Response JSON:
        {
            "success": true,
            "history": [
                {
                    "userQuery": "...",
                    "sqlGenerated": "...",
                    "rowCount": 10,
                    "success": true,
                    "executionTimeMs": 45,
                    "createdAt": "..."
                }
            ]
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        limit = int(request.args.get('limit', 50))

        history = service.get_query_history(session_id, user_id)

        # Limit results
        history = history[:limit]

        return success_response({
            'history': [
                {
                    'sqlGenerated': h.sql_generated,
                    'data': h.data[:5] if h.data else [],  # Only first 5 rows for history
                    'rowCount': h.row_count,
                    'success': h.success,
                    'executionTimeMs': h.execution_time_ms,
                    'errorMessage': h.error_message
                }
                for h in history
            ]
        })

    except Exception as e:
        logger.error(f"Error getting history for session {session_id}: {e}")
        return error_response(str(e), 500)
