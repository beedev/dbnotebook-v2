"""Quiz API routes for adaptive Q&A feature.

This module provides REST endpoints for:
- Admin: Create, list, delete quizzes and view results
- Public: Take quizzes via shareable links
"""

import logging
from flask import request, jsonify, session

from ...core.services.quiz_service import QuizService

logger = logging.getLogger(__name__)


def create_quiz_routes(app, pipeline, db_manager, notebook_manager):
    """Create Quiz API routes.

    Args:
        app: Flask application instance
        pipeline: LocalRAGPipeline instance
        db_manager: DatabaseManager instance
        notebook_manager: NotebookManager instance
    """
    # Initialize quiz service
    quiz_service = QuizService(pipeline, db_manager, notebook_manager)

    # === Admin Routes (require auth) ===

    @app.route('/api/quiz/create', methods=['POST'])
    def create_quiz():
        """Create a new quiz from notebook content.

        Request JSON:
            {
                "notebook_id": "uuid",
                "title": "Quiz Title",
                "num_questions": 10,
                "difficulty_mode": "adaptive",  # adaptive|easy|medium|hard
                "time_limit": null,  # Optional minutes
                "llm_model": null,  # Optional: "provider:model" or just "model"
                "question_source": "notebook_only",  # notebook_only|extended
                "include_code_questions": false  # Enable code-based questions
            }

        Response JSON:
            {
                "success": true,
                "quiz_id": "uuid",
                "link": "/quiz/uuid",
                "title": "Quiz Title",
                "question_source": "notebook_only",
                "include_code_questions": false
            }
        """
        try:
            # Get user from session
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401

            data = request.json or {}

            notebook_id = data.get('notebook_id')
            title = data.get('title')

            if not notebook_id:
                return jsonify({
                    'success': False,
                    'error': 'notebook_id is required'
                }), 400

            if not title or not title.strip():
                return jsonify({
                    'success': False,
                    'error': 'title is required'
                }), 400

            result = quiz_service.create_quiz(
                notebook_id=notebook_id,
                user_id=user_id,
                title=title.strip(),
                num_questions=data.get('num_questions', 10),
                difficulty_mode=data.get('difficulty_mode', 'adaptive'),
                time_limit=data.get('time_limit'),
                llm_model=data.get('llm_model'),
                question_source=data.get('question_source', 'notebook_only'),
                include_code_questions=data.get('include_code_questions', False)
            )

            return jsonify({
                'success': True,
                **result
            })

        except ValueError as e:
            logger.warning(f"Quiz creation validation error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Error creating quiz: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/quiz/list', methods=['GET'])
    def list_quizzes():
        """List all quizzes created by current user.

        Response JSON:
            {
                "success": true,
                "quizzes": [
                    {
                        "id": "uuid",
                        "title": "Quiz Title",
                        "notebook_name": "Source Notebook",
                        "num_questions": 10,
                        "difficulty_mode": "adaptive",
                        "attempt_count": 5,
                        "link": "/quiz/uuid",
                        "created_at": "2025-01-31T00:00:00"
                    }
                ]
            }
        """
        try:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401

            quizzes = quiz_service.list_quizzes(user_id)

            return jsonify({
                'success': True,
                'quizzes': quizzes
            })

        except Exception as e:
            logger.error(f"Error listing quizzes: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/quiz/<quiz_id>/results', methods=['GET'])
    def get_quiz_results(quiz_id):
        """Get all attempts and statistics for a quiz (creator only).

        Response JSON:
            {
                "success": true,
                "quiz": {...},
                "statistics": {
                    "total_attempts": 15,
                    "avg_score": 7.5,
                    "avg_percentage": 75.0,
                    "pass_rate": 80.0
                },
                "attempts": [...]
            }
        """
        try:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401

            results = quiz_service.get_quiz_results(quiz_id, user_id)

            return jsonify({
                'success': True,
                **results
            })

        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 404
        except PermissionError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 403
        except Exception as e:
            logger.error(f"Error getting quiz results: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/quiz/<quiz_id>', methods=['DELETE'])
    def delete_quiz(quiz_id):
        """Deactivate a quiz (soft delete).

        Response JSON:
            {
                "success": true,
                "message": "Quiz deleted"
            }
        """
        try:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401

            quiz_service.delete_quiz(quiz_id, user_id)

            return jsonify({
                'success': True,
                'message': 'Quiz deleted'
            })

        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 404
        except PermissionError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 403
        except Exception as e:
            logger.error(f"Error deleting quiz: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # === Public Routes (no auth required, for test-takers) ===

    @app.route('/api/quiz/<quiz_id>/info', methods=['GET'])
    def get_quiz_info(quiz_id):
        """Get public quiz info for landing page (no auth required).

        Response JSON:
            {
                "success": true,
                "quiz_id": "uuid",
                "title": "Quiz Title",
                "num_questions": 10,
                "difficulty_mode": "adaptive",
                "time_limit": null,
                "has_time_limit": false,
                "question_source": "notebook_only",
                "include_code_questions": false
            }
        """
        try:
            info = quiz_service.get_quiz_info(quiz_id)

            return jsonify({
                'success': True,
                **info
            })

        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 404
        except Exception as e:
            logger.error(f"Error getting quiz info: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/quiz/<quiz_id>/start', methods=['POST'])
    def start_quiz_attempt(quiz_id):
        """Start a quiz attempt (no auth required).

        If email is provided and there's an incomplete attempt, resumes it.

        Request JSON:
            {
                "taker_name": "John Smith",
                "taker_email": "john@example.com"  // Optional, enables resume
            }

        Response JSON:
            {
                "success": true,
                "attempt_id": "uuid",
                "quiz_title": "Quiz Title",
                "resumed": false,  // true if resuming existing attempt
                "question": {
                    "type": "multiple_choice",  // or code_output, code_fill_blank, code_bug_fix
                    "question": "...",
                    "options": ["A", "B", "C", "D"],
                    "code_snippet": "..."  // Only for code questions
                },
                "question_num": 1,
                "total": 10,
                "time_limit": null,
                "difficulty": "medium"
            }
        """
        try:
            data = request.json or {}
            taker_name = data.get('taker_name', '').strip()
            taker_email = data.get('taker_email', '').strip() or None

            if not taker_name:
                return jsonify({
                    'success': False,
                    'error': 'taker_name is required'
                }), 400

            result = quiz_service.start_attempt(quiz_id, taker_name, taker_email)

            return jsonify({
                'success': True,
                **result
            })

        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Error starting quiz attempt: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/quiz/attempt/<attempt_id>/answer', methods=['POST'])
    def submit_quiz_answer(attempt_id):
        """Submit an answer and get next question or results (no auth required).

        Request JSON:
            {
                "answer": "A"  # A, B, C, or D
            }

        Response JSON (during quiz):
            {
                "success": true,
                "correct": true,
                "explanation": "...",
                "correct_answer": "A",
                "completed": false,
                "next_question": {
                    "type": "multiple_choice",  // or code_output, code_fill_blank, code_bug_fix
                    "question": "...",
                    "options": ["A", "B", "C", "D"],
                    "code_snippet": "...",  // Only for code questions
                    "question_num": 2,
                    "total": 10,
                    "difficulty": "hard"
                }
            }

        Response JSON (quiz complete):
            {
                "success": true,
                "correct": true,
                "explanation": "...",
                "correct_answer": "A",
                "completed": true,
                "results": {
                    "score": 8,
                    "total": 10,
                    "percentage": 80.0,
                    "passed": true,
                    "answers": [...]  // Each answer includes type and optional code_snippet
                }
            }
        """
        try:
            data = request.json or {}
            answer = data.get('answer', '').strip().upper()

            if not answer:
                return jsonify({
                    'success': False,
                    'error': 'answer is required'
                }), 400

            result = quiz_service.submit_answer(attempt_id, answer)

            return jsonify({
                'success': True,
                **result
            })

        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Error submitting quiz answer: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/quiz/attempt/<attempt_id>/status', methods=['GET'])
    def get_attempt_status(attempt_id):
        """Get current status of an attempt (for resuming, no auth required).

        Response JSON:
            {
                "success": true,
                "completed": false,
                "quiz_title": "...",
                "taker_name": "...",
                "question_num": 3,
                "total": 10,
                "score": 2,
                "current_question": {...}
            }
        """
        try:
            status = quiz_service.get_attempt_status(attempt_id)

            return jsonify({
                'success': True,
                **status
            })

        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 404
        except Exception as e:
            logger.error(f"Error getting attempt status: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/quiz/attempt/<attempt_id>/suggestions', methods=['GET'])
    def get_improvement_suggestions(attempt_id):
        """Get personalized improvement suggestions for a completed quiz attempt.

        For 'extended' quizzes: Returns LLM-generated study recommendations.
        For 'notebook_only' quizzes: Returns links to relevant document sections.

        Response JSON (LLM-generated):
            {
                "success": true,
                "type": "llm_generated",
                "wrong_count": 3,
                "summary": "Brief assessment...",
                "weak_areas": ["topic1", "topic2"],
                "suggestions": [
                    {
                        "title": "Review fundamentals",
                        "description": "Focus on...",
                        "priority": "high",
                        "topics": ["topic1"]
                    }
                ],
                "resources": [
                    {
                        "type": "concept",
                        "title": "Resource name",
                        "description": "What to study"
                    }
                ]
            }

        Response JSON (Document-linked):
            {
                "success": true,
                "type": "document_linked",
                "wrong_count": 3,
                "summary": "Review these sections...",
                "weak_areas": ["topic1", "topic2"],
                "sections": [
                    {
                        "topic": "topic1",
                        "documents": [
                            {
                                "source_id": "uuid",
                                "filename": "document.pdf",
                                "preview": "Content preview...",
                                "relevance_score": 0.85
                            }
                        ]
                    }
                ]
            }
        """
        try:
            suggestions = quiz_service.generate_improvement_suggestions(attempt_id)

            return jsonify({
                'success': True,
                **suggestions
            })

        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Error generating improvement suggestions: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    return app
