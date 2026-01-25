"""SQL Chat schema management routes.

Endpoints for:
- Schema introspection
- Dictionary generation and management
- Telemetry and metrics
- Health checks
- Few-shot dataset management
- Schema linking
- Query learning
- Schema change detection
"""

import logging
import asyncio

from flask import Blueprint, request

from dbnotebook.api.core.response import (
    success_response, error_response, validation_error, not_found
)
from dbnotebook.core.services.document_service import DocumentService

from .utils import get_service, get_current_user_id

logger = logging.getLogger(__name__)

# Blueprint for schema endpoints
schema_bp = Blueprint('sql_chat_schema', __name__)


# =============================================================================
# Schema Endpoints
# =============================================================================

@schema_bp.route('/schema/<connection_id>', methods=['GET'])
def get_schema(connection_id: str):
    """
    Get database schema for a connection.

    Query params:
        - refresh: If "true", force cache refresh

    Response JSON:
        {
            "success": true,
            "schema": {
                "tables": [
                    {
                        "name": "users",
                        "columns": [...],
                        "rowCount": 1000
                    }
                ],
                "relationships": [...],
                "cachedAt": "2024-01-01T00:00:00"
            },
            "formatted": "Table: users\\n  - id (INTEGER)\\n  - name (VARCHAR)..."
        }
    """
    try:
        service = get_service()

        force_refresh = request.args.get('refresh', 'false').lower() == 'true'

        schema = service.get_schema(connection_id, force_refresh=force_refresh)

        if not schema:
            return error_response('Schema not available. Check connection.', 404)

        # Format schema for display
        formatted = service.get_schema_formatted(connection_id)

        return success_response({
            'schema': {
                'tables': [
                    {
                        'name': t.name,
                        'columns': [
                            {
                                'name': c.name,
                                'dataType': c.type,
                                'nullable': c.nullable,
                                'isPrimaryKey': c.primary_key,
                                'isForeignKey': bool(c.foreign_key)
                            }
                            for c in t.columns
                        ],
                        'rowCount': t.row_count,
                        'sampleValues': t.sample_values
                    }
                    for t in schema.tables
                ],
                'relationships': [
                    {
                        'fromTable': r.from_table,
                        'fromColumn': r.from_column,
                        'toTable': r.to_table,
                        'toColumn': r.to_column
                    }
                    for r in schema.relationships
                ],
                'cachedAt': schema.cached_at.isoformat() if schema.cached_at else None
            },
            'formatted': formatted
        })

    except Exception as e:
        logger.error(f"Error getting schema for connection {connection_id}: {e}")
        return error_response(str(e), 500)


# =============================================================================
# Telemetry Endpoints
# =============================================================================

@schema_bp.route('/metrics', methods=['GET'])
def get_accuracy_metrics():
    """
    Get accuracy metrics from telemetry.

    Query params:
        - days: Number of days to look back (default 30)
        - session_id: Optional session filter

    Response JSON:
        {
            "success": true,
            "metrics": {
                "successRate": 0.92,
                "avgRetries": 0.3,
                "avgConfidence": 0.85,
                "emptyResultRate": 0.05
            }
        }
    """
    try:
        service = get_service()

        days = int(request.args.get('days', 30))
        session_id = request.args.get('session_id')

        metrics = service.get_accuracy_metrics(days=days, session_id=session_id)

        return success_response({'metrics': metrics})

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return error_response(str(e), 500)


# =============================================================================
# Health Check
# =============================================================================

@schema_bp.route('/health', methods=['GET'])
def health():
    """
    Health check for SQL Chat service.

    Response JSON:
        {
            "success": true,
            "status": "healthy",
            "serviceInitialized": true
        }
    """
    try:
        service = get_service()
        return success_response({
            'status': 'healthy',
            'serviceInitialized': service is not None
        })
    except Exception as e:
        return error_response(str(e), 500, status='unhealthy')


# =============================================================================
# Few-Shot Dataset Management
# =============================================================================

@schema_bp.route('/few-shot/status', methods=['GET'])
def get_few_shot_status():
    """
    Get status of few-shot examples dataset.

    Response JSON:
        {
            "success": true,
            "initialized": false,
            "exampleCount": 0,
            "minRequired": 50000
        }
    """
    try:
        service = get_service()
        status = service.get_few_shot_status()
        return success_response(status)

    except Exception as e:
        logger.error(f"Error getting few-shot status: {e}")
        return error_response(str(e), 500)


@schema_bp.route('/few-shot/initialize', methods=['POST'])
def initialize_few_shot():
    """
    Initialize few-shot examples by loading Gretel dataset.

    This is a long-running operation (~30 min for full dataset).
    Consider using smaller maxExamples for faster setup.

    Request JSON:
        {
            "maxExamples": 10000  // Optional, default loads all ~100K
        }

    Response JSON:
        {
            "success": true,
            "message": "Few-shot initialization started",
            "examplesLoaded": 10000
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        max_examples = data.get('maxExamples')

        # Run initialization (async internally)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(
                service.initialize_few_shot(max_examples=max_examples)
            )
        finally:
            loop.close()

        if success:
            status = service.get_few_shot_status()
            return success_response({
                'message': 'Few-shot dataset loaded successfully',
                'examplesLoaded': status.get('exampleCount', 0)
            })
        else:
            return error_response('Failed to initialize few-shot dataset. Check logs.', 500)

    except Exception as e:
        logger.error(f"Error initializing few-shot dataset: {e}")
        return error_response(str(e), 500)


# =============================================================================
# Dictionary Management Endpoints
# =============================================================================

@schema_bp.route('/connections/<connection_id>/dictionary', methods=['GET'])
def get_dictionary(connection_id: str):
    """
    Generate dictionary Markdown for a database connection and create notebook.

    This endpoint:
    1. Creates a "SQL: <connection_name>" notebook if it doesn't exist
    2. Generates the schema dictionary from current database
    3. Saves the dictionary as a source document in the notebook

    Query params:
        - connection_name: Optional display name for the dictionary

    Response JSON:
        {
            "success": true,
            "dictionary": "# Database Dictionary: ...",
            "connectionName": "My Database",
            "tableCount": 15,
            "columnCount": 85,
            "notebookId": "uuid-of-notebook"
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        connection_name = request.args.get('connection_name')

        # Get connection info
        connection = service._connections.get_connection(connection_id)
        if not connection:
            return not_found('Connection', connection_id)

        conn_name = connection.name if connection else connection_name or 'Unknown'

        # Check if notebook exists for this connection
        notebook_manager = service.notebook_manager
        notebook_id = None

        if notebook_manager:
            # Look for existing SQL dictionary notebook
            notebooks = notebook_manager.list_notebooks(user_id)
            sql_notebook_name = f"SQL: {conn_name}"

            for nb in notebooks:
                if nb.get('name') == sql_notebook_name:
                    notebook_id = nb.get('id')
                    break

            # Check if dictionary already exists - return lightweight version
            if notebook_id:
                existing_docs = notebook_manager.get_documents(notebook_id)
                has_dictionary = any(
                    'dictionary' in doc.get('file_name', '').lower() or
                    'schema' in doc.get('file_name', '').lower()
                    for doc in existing_docs
                )

                if has_dictionary:
                    # Dictionary already ingested - generate fast schema-only version
                    schema = service.get_schema(connection_id)
                    if schema:
                        fast_dictionary = service._schema.generate_schema_dictionary(
                            service._connections.get_engine(connection_id),
                            conn_name
                        )
                        logger.info(f"Returning cached dictionary for {conn_name} (schema-only)")
                        return success_response({
                            'dictionary': fast_dictionary,
                            'connectionName': conn_name,
                            'tableCount': len(schema.tables),
                            'columnCount': sum(len(t.columns) for t in schema.tables),
                            'notebookId': notebook_id,
                            'cached': True
                        })

            # Create notebook if it doesn't exist
            if not notebook_id:
                logger.info(f"Creating SQL dictionary notebook for connection {conn_name}")
                notebook = notebook_manager.create_notebook(
                    user_id=user_id,
                    name=sql_notebook_name,
                    description=f"Schema dictionary and query examples for {conn_name}"
                )
                notebook_id = notebook.get('id')

        # Generate dictionary from current schema
        dictionary, error = service.generate_dictionary(
            connection_id=connection_id,
            connection_name=conn_name
        )

        if error:
            return error_response(error, 500)

        # Get schema for table/column counts
        schema = service.get_schema(connection_id)

        # Save dictionary as source document if notebook exists
        source_id = None
        if notebook_id and notebook_manager and dictionary:
            dict_filename = f"{conn_name}_dictionary.md"
            pipeline = service.pipeline

            # Delete old dictionary if exists
            document_service = DocumentService(
                pipeline=pipeline,
                db_manager=service.db_manager,
                notebook_manager=notebook_manager
            )
            existing_docs = notebook_manager.get_documents(notebook_id)
            for doc in existing_docs:
                if doc.get('file_name') == dict_filename:
                    old_source_id = doc.get('source_id')
                    logger.info(f"Removing existing dictionary (source_id: {old_source_id})")
                    document_service.delete(old_source_id, notebook_id, user_id)
                    break

            try:
                # 1. Register in database
                source_id = notebook_manager.add_document(
                    notebook_id=notebook_id,
                    file_name=dict_filename,
                    file_content=dictionary.encode('utf-8'),
                    file_type="md",
                    chunk_count=0
                )
                logger.info(f"Registered dictionary: source_id={source_id}")

                # 2. Create nodes from content
                from llama_index.core.schema import Document as LlamaDocument
                from llama_index.core.node_parser import SentenceSplitter
                from llama_index.core import Settings

                splitter = SentenceSplitter(chunk_size=512, chunk_overlap=32)
                doc = LlamaDocument(
                    text=dictionary,
                    metadata={
                        "file_name": dict_filename,
                        "source_id": source_id,
                        "notebook_id": notebook_id,
                        "user_id": user_id,
                        "tree_level": 0
                    }
                )
                nodes = splitter.get_nodes_from_documents([doc])

                # 3. Add notebook metadata to nodes
                for node in nodes:
                    if hasattr(node, 'metadata'):
                        node.metadata["notebook_id"] = notebook_id
                        node.metadata["source_id"] = source_id
                        node.metadata["tree_level"] = 0

                # 4. Embed and store
                if nodes and pipeline and hasattr(pipeline, "_vector_store"):
                    embed_model = Settings.embed_model
                    if embed_model:
                        texts = [node.get_content() for node in nodes]
                        embeddings = embed_model.get_text_embedding_batch(texts)
                        for node, embedding in zip(nodes, embeddings):
                            node.embedding = embedding
                        added = pipeline._vector_store.add_nodes(nodes, notebook_id=notebook_id)
                        logger.info(f"Added {added} embeddings for dictionary")

                # 5. Update chunk count
                notebook_manager.update_document_chunk_count(source_id, len(nodes))

                # 6. Queue transformation
                if hasattr(pipeline, '_ingestion') and pipeline._ingestion._transformation_callback:
                    pipeline._ingestion._transformation_callback(
                        source_id=source_id,
                        document_text=dictionary,
                        notebook_id=notebook_id,
                        file_name=dict_filename
                    )
                    logger.info(f"Queued transformation for dictionary: source_id={source_id}")

                logger.info(f"Dictionary uploaded: source_id={source_id}, nodes={len(nodes)}")

            except ValueError as e:
                logger.warning(f"Dictionary already exists: {e}")
            except Exception as e:
                logger.error(f"Failed to upload dictionary: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # Get table/column counts
        table_count = len(schema.tables) if schema else 0
        column_count = sum(len(t.columns) for t in schema.tables) if schema else 0

        return success_response({
            'dictionary': dictionary,
            'connectionName': conn_name,
            'tableCount': table_count,
            'columnCount': column_count,
            'notebookId': notebook_id,
            'sourceId': source_id
        })

    except Exception as e:
        logger.error(f"Error generating dictionary for connection {connection_id}: {e}")
        return error_response(str(e), 500)


@schema_bp.route('/connections/<connection_id>/dictionary/regenerate', methods=['POST'])
def regenerate_dictionary(connection_id: str):
    """
    Regenerate dictionary for a connection (used when schema changes).

    Response JSON:
        {
            "success": true,
            "message": "Dictionary regenerated successfully",
            "tableCount": 15
        }
    """
    try:
        service = get_service()
        user_id = get_current_user_id()

        # Get connection
        connection = service._connections.get_connection(connection_id)
        if not connection:
            return not_found('Connection', connection_id)

        conn_name = connection.name
        engine = service._connections.get_engine(connection_id)
        if not engine:
            return error_response('Could not connect to database', 500)

        # Generate fresh dictionary files
        logger.info(f"Regenerating dictionary for {conn_name}")
        schema_md = service._schema.generate_schema_dictionary(engine, conn_name)
        samples_md = service._schema.generate_sample_values(engine, conn_name, limit=5)

        # Get or create SQL notebook
        notebook_manager = service.notebook_manager
        notebook_id = None

        if notebook_manager:
            notebooks = notebook_manager.list_notebooks(user_id)
            sql_notebook_name = f"SQL: {conn_name}"

            for nb in notebooks:
                if nb.get('name') == sql_notebook_name:
                    notebook_id = nb.get('id')
                    break

            if not notebook_id:
                notebook = notebook_manager.create_notebook(
                    user_id=user_id,
                    name=sql_notebook_name,
                    description=f"Schema dictionary and sample data for {conn_name}"
                )
                notebook_id = notebook.get('id')

        # Save and ingest dictionary files
        if notebook_id:
            from pathlib import Path

            upload_dir = Path("uploads") / "sql_dictionaries"
            upload_dir.mkdir(parents=True, exist_ok=True)

            # Save schema dictionary
            schema_file = upload_dir / f"schema_dictionary_{connection_id}.md"
            schema_file.write_text(schema_md, encoding='utf-8')

            # Save sample values
            samples_file = upload_dir / f"sample_values_{connection_id}.md"
            samples_file.write_text(samples_md, encoding='utf-8')

            # Store in vector store
            try:
                service.pipeline.store_nodes(
                    input_files=[str(schema_file), str(samples_file)],
                    notebook_id=notebook_id,
                    user_id=user_id
                )
                logger.info(f"Dictionary regenerated for {conn_name}")
            except Exception as e:
                logger.warning(f"Could not store dictionary nodes: {e}")

        # Get table count
        schema = service.get_schema(connection_id)
        table_count = len(schema.tables) if schema else 0

        return success_response({
            'message': f'Dictionary regenerated for {conn_name}',
            'tableCount': table_count,
            'notebookId': notebook_id
        })

    except Exception as e:
        logger.error(f"Error regenerating dictionary for {connection_id}: {e}")
        return error_response(str(e), 500)


@schema_bp.route('/connections/<connection_id>/dictionary/delta', methods=['POST'])
def get_dictionary_delta(connection_id: str):
    """
    Get schema changes (delta) between existing dictionary and current database schema.

    Request JSON:
        {
            "existingDictionary": "# Database Dictionary: ...",
            "connectionName": "My Database" (optional)
        }

    Response JSON:
        {
            "success": true,
            "delta": {
                "hasChanges": true,
                "addedTables": ["new_table"],
                "removedTables": [],
                "modifiedTables": {...}
            }
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        existing_dictionary = data.get('existingDictionary', '')
        connection_name = data.get('connectionName')

        if not existing_dictionary:
            return validation_error('existingDictionary is required')

        delta = service.get_schema_delta(
            connection_id=connection_id,
            existing_dictionary=existing_dictionary,
            connection_name=connection_name
        )

        return success_response({'delta': delta})

    except Exception as e:
        logger.error(f"Error computing dictionary delta for connection {connection_id}: {e}")
        return error_response(str(e), 500)


@schema_bp.route('/connections/<connection_id>/dictionary/merge', methods=['POST'])
def merge_dictionary(connection_id: str):
    """
    Merge schema changes into existing dictionary while preserving user edits.

    Request JSON:
        {
            "existingDictionary": "# Database Dictionary: ..."
        }

    Response JSON:
        {
            "success": true,
            "dictionary": "# Database Dictionary: ... (merged)",
            "message": "Merged 2 new tables, 5 new columns"
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        existing_dictionary = data.get('existingDictionary', '')

        if not existing_dictionary:
            return validation_error('existingDictionary is required')

        merged_dictionary, message = service.merge_dictionary(
            connection_id=connection_id,
            existing_dictionary=existing_dictionary
        )

        return success_response({
            'dictionary': merged_dictionary,
            'message': message
        })

    except Exception as e:
        logger.error(f"Error merging dictionary for connection {connection_id}: {e}")
        return error_response(str(e), 500)


# =============================================================================
# Schema Linking Endpoints
# =============================================================================

@schema_bp.route('/sessions/<session_id>/table-relevance', methods=['POST'])
def get_table_relevance(session_id: str):
    """
    Get table relevance scores for a query.

    Request JSON:
        {
            "query": "Show me total sales by region"
        }

    Response JSON:
        {
            "success": true,
            "relevance": [
                {"table": "sales", "score": 0.92},
                {"table": "regions", "score": 0.85}
            ]
        }
    """
    try:
        service = get_service()
        data = request.get_json() or {}

        query = data.get('query', '').strip()
        if not query:
            return validation_error('query is required')

        scores = service.get_table_relevance_scores(session_id, query)

        return success_response({
            'relevance': [
                {'table': table, 'score': round(score, 3)}
                for table, score in scores
            ]
        })

    except Exception as e:
        logger.error(f"Error getting table relevance for session {session_id}: {e}")
        return error_response(str(e), 500)


# =============================================================================
# Query Learning Endpoints
# =============================================================================

@schema_bp.route('/connections/<connection_id>/learned-joins', methods=['GET'])
def get_learned_joins(connection_id: str):
    """
    Get learned JOIN patterns for a connection.

    Response JSON:
        {
            "success": true,
            "patterns": [
                {
                    "table1": "orders",
                    "column1": "customer_id",
                    "table2": "customers",
                    "column2": "id",
                    "joinType": "INNER",
                    "usageCount": 15
                }
            ]
        }
    """
    try:
        service = get_service()
        patterns = service.get_learned_join_patterns(connection_id)
        return success_response({'patterns': patterns})

    except Exception as e:
        logger.error(f"Error getting learned joins for connection {connection_id}: {e}")
        return error_response(str(e), 500)


@schema_bp.route('/connections/<connection_id>/learned-joins', methods=['DELETE'])
def clear_learned_joins(connection_id: str):
    """
    Clear learned JOIN patterns for a connection.

    Response JSON:
        {
            "success": true,
            "message": "Learned patterns cleared"
        }
    """
    try:
        service = get_service()
        service._query_learner.clear_cache(connection_id)

        logger.info(f"Cleared learned patterns for connection {connection_id}")

        return success_response({'message': 'Learned patterns cleared'})

    except Exception as e:
        logger.error(f"Error clearing learned joins for connection {connection_id}: {e}")
        return error_response(str(e), 500)


# =============================================================================
# Schema Change Detection Endpoints
# =============================================================================

@schema_bp.route('/connections/<connection_id>/schema-changed', methods=['GET'])
def check_schema_changed(connection_id: str):
    """
    Check if database schema has changed since last introspection.

    Response JSON:
        {
            "success": true,
            "changed": false,
            "fingerprint": "abc123..."
        }
    """
    try:
        service = get_service()

        # Get engine for this connection
        connection = service._connections.get_connection(connection_id)
        if not connection:
            return not_found('Connection', connection_id)

        engine = service._connections.get_engine(connection)
        if not engine:
            return error_response('Could not create database engine', 400)

        # Check if schema changed
        changed = service._schema.has_schema_changed(engine, connection_id)
        fingerprint = service._schema.get_fingerprint(engine)

        return success_response({
            'changed': changed,
            'fingerprint': fingerprint
        })

    except Exception as e:
        logger.error(f"Error checking schema change for connection {connection_id}: {e}")
        return error_response(str(e), 500)
