import logging
from typing import Optional

from llama_index.core import Settings
from llama_index.core.chat_engine.types import StreamingAgentChatResponse
from llama_index.core.prompts import ChatMessage, MessageRole

from .core import (
    LocalChatEngine,
    LocalDataIngestion,
    LocalRAGModel,
    LocalEmbedding,
    LocalVectorStore,
    get_system_prompt
)
from .core.sales import QueryClassifier, OfferingAnalyzer
from .setting import get_settings

logger = logging.getLogger(__name__)


class LocalRAGPipeline:
    """
    Main RAG pipeline orchestrating model, embedding, ingestion, and chat engine.

    Optimized for:
    - Single model/embedding initialization
    - Cached vector index
    - Proper logging
    """

    def __init__(self, host: str = "host.docker.internal") -> None:
        self._host = host
        self._language = "eng"
        self._model_name = ""
        self._system_prompt = get_system_prompt("eng", is_rag_prompt=False)
        self._query_engine = None
        self._settings = get_settings()

        # Engine state management for conversation history preservation
        self._current_offering_filter: Optional[list[str]] = None
        self._engine_initialized: bool = False

        # Initialize components once
        self._engine = LocalChatEngine(
            setting=self._settings,
            host=host
        )
        self._ingestion = LocalDataIngestion(
            setting=self._settings,
            max_workers=4,
            use_cache=True
        )
        self._vector_store = LocalVectorStore(
            host=host,
            setting=self._settings,
            persist=True
        )

        # Initialize models once and cache in Settings
        self._default_model = LocalRAGModel.set(
            model_name=self._model_name,
            host=host,
            setting=self._settings
        )
        Settings.llm = self._default_model
        Settings.embed_model = LocalEmbedding.set(
            host=host,
            setting=self._settings
        )

        # Initialize sales enablement components
        self._query_classifier = QueryClassifier(llm=self._default_model)
        self._offering_analyzer = OfferingAnalyzer(llm=self._default_model)

        logger.info(f"Pipeline initialized - Host: {host}")
        logger.debug(f"LLM Model: {self._model_name or self._settings.ollama.llm}")
        logger.debug(f"Embed Model: {self._settings.ingestion.embed_llm}")

    def get_model_name(self) -> str:
        return self._model_name

    def set_model_name(self, model_name: str) -> None:
        self._model_name = model_name
        logger.debug(f"Model name set to: {model_name}")

    def get_language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        self._language = language
        logger.debug(f"Language set to: {language}")

    def get_system_prompt(self) -> str:
        return self._system_prompt

    def set_system_prompt(self, system_prompt: Optional[str] = None) -> None:
        self._system_prompt = system_prompt or get_system_prompt(
            language=self._language,
            is_rag_prompt=self._ingestion.check_nodes_exist()
        )
        logger.debug("System prompt updated")

    def set_model(self) -> None:
        """Update the LLM model with current settings."""
        self._default_model = LocalRAGModel.set(
            model_name=self._model_name,
            system_prompt=self._system_prompt,
            host=self._host,
            setting=self._settings
        )
        Settings.llm = self._default_model
        logger.info(f"Model updated: {self._model_name}")

    def reset_engine(self) -> None:
        """Reset the chat engine without documents."""
        self._query_engine = self._engine.set_engine(
            llm=self._default_model,
            nodes=[],
            language=self._language
        )
        logger.debug("Engine reset (no documents)")

    def reset_documents(self) -> None:
        """Reset all ingested documents."""
        self._ingestion.reset()
        self._vector_store.reset()
        logger.info("Documents reset")

    def clear_conversation(self) -> None:
        """Clear conversation history."""
        if self._query_engine:
            self._query_engine.reset()
            logger.debug("Conversation cleared")

    def reset_conversation(self) -> None:
        """Reset conversation and switch to non-RAG mode."""
        self.reset_engine()
        self.set_system_prompt(
            get_system_prompt(language=self._language, is_rag_prompt=False)
        )
        logger.info("Conversation reset to non-RAG mode")

    def set_embed_model(self, model_name: str) -> None:
        """Update the embedding model."""
        Settings.embed_model = LocalEmbedding.set(
            model_name=model_name,
            host=self._host,
            setting=self._settings
        )
        logger.info(f"Embedding model updated: {model_name}")

    def pull_model(self, model_name: str):
        """Pull an LLM model from Ollama."""
        logger.info(f"Pulling model: {model_name}")
        return LocalRAGModel.pull(self._host, model_name)

    def pull_embed_model(self, model_name: str):
        """Pull an embedding model from Ollama."""
        logger.info(f"Pulling embedding model: {model_name}")
        return LocalEmbedding.pull(self._host, model_name)

    def check_exist(self, model_name: str) -> bool:
        """Check if an LLM model exists on Ollama."""
        return LocalRAGModel.check_model_exist(self._host, model_name)

    def check_exist_embed(self, model_name: str) -> bool:
        """Check if an embedding model exists on Ollama."""
        return LocalEmbedding.check_model_exist(self._host, model_name)

    def store_nodes(
        self,
        input_files: Optional[list[str]] = None,
        it_practice: Optional[str] = None,
        offering_name: Optional[str] = None,
        offering_id: Optional[str] = None
    ) -> None:
        """
        Process and store document nodes with metadata.

        Args:
            input_files: List of file paths to process
            it_practice: IT Practice classification (e.g., "Cloud Services")
            offering_name: Offering name (e.g., "Cloud Migration")
            offering_id: Unique offering identifier (UUID)

        Uses parallel processing and caching for efficiency.
        """
        if not input_files:
            logger.warning("No input files provided")
            return

        logger.info(f"Processing {len(input_files)} files")
        self._ingestion.store_nodes(
            input_files=input_files,
            it_practice=it_practice,
            offering_name=offering_name,
            offering_id=offering_id
        )
        logger.info("Document processing complete")

        # Generate synopsis for the offering if offering metadata provided
        if offering_id and offering_name:
            logger.info(f"Generating synopsis for offering: {offering_name}")
            synopsis = self._ingestion.generate_synopsis_for_offering(
                offering_id=offering_id,
                offering_name=offering_name,
                llm=self._default_model,
                file_list=input_files
            )
            if synopsis:
                logger.info(f"Synopsis generated successfully for {offering_name}")
            else:
                logger.warning(f"Failed to generate synopsis for {offering_name}")

    def set_chat_mode(self, system_prompt: Optional[str] = None) -> None:
        """Configure chat mode with current documents and settings."""
        self.set_language(self._language)
        self.set_system_prompt(system_prompt)
        self.set_model()
        self.set_engine()
        logger.debug("Chat mode configured")

    def set_engine(
        self,
        offering_filter: Optional[list[str]] = None,
        force_reset: bool = False
    ) -> None:
        """Set up the chat engine with current nodes, optionally filtered by offerings.
        Only recreates engine if filter changes or force_reset is True.

        Args:
            offering_filter: List of offering names to filter by (Sales Pitch mode)
            force_reset: Force recreation of engine even if filter unchanged
        """
        # Check if engine needs to be recreated
        filter_changed = offering_filter != self._current_offering_filter

        if not self._engine_initialized or filter_changed or force_reset:
            logger.info(f"Creating new engine with filter: {offering_filter}")
            logger.info(f"Filter changed: {filter_changed}, Previous filter: {self._current_offering_filter}")

            # PRESERVE chat history from existing engine before recreating
            preserved_history = []
            if self._query_engine is not None and hasattr(self._query_engine, 'memory'):
                try:
                    # Extract all chat messages from the memory buffer
                    preserved_history = self._query_engine.memory.get_all()
                    logger.info(f"✓ Preserved {len(preserved_history)} messages from chat history")

                    # Log details of preserved messages for debugging
                    if preserved_history:
                        logger.info("--- Preserved History Details ---")
                        for i, msg in enumerate(preserved_history):
                            logger.info(f"  Message {i+1}: role={msg.role}, content_preview={str(msg.content)[:100]}...")
                        logger.info("--- End History Details ---")
                    else:
                        logger.warning("⚠ No history to preserve (memory was empty)")

                except Exception as e:
                    logger.warning(f"❌ Could not extract chat history: {e}")
                    preserved_history = []
            else:
                logger.info("No existing engine to preserve history from")

            # Get nodes with filter
            nodes = self._ingestion.get_ingested_nodes()

            # Create new engine WITH preserved chat history
            logger.info(f"Creating new engine with {len(preserved_history)} preserved messages")
            self._query_engine = self._engine.set_engine(
                llm=self._default_model,
                nodes=nodes,
                language=self._language,
                offering_filter=offering_filter,
                vector_store=self._vector_store,
                chat_history=preserved_history
            )

            # Verify the new engine has the history
            if hasattr(self._query_engine, 'memory'):
                new_history_count = len(self._query_engine.memory.get_all())
                logger.info(f"✓ New engine memory buffer contains {new_history_count} messages")
                if new_history_count != len(preserved_history):
                    logger.error(f"❌ MISMATCH: Preserved {len(preserved_history)} but new engine has {new_history_count}!")
            else:
                logger.warning("⚠ New engine has no memory attribute!")

            # Update state
            self._current_offering_filter = offering_filter
            self._engine_initialized = True

            filter_msg = f" (filtered by {len(offering_filter)} offerings)" if offering_filter else ""
            logger.info(f"New engine created with {len(nodes)} nodes{filter_msg}")
        else:
            logger.info("Using existing engine - filter unchanged")

    def get_history(self, chatbot: list[dict]) -> list[ChatMessage]:
        """Convert chatbot history to ChatMessage format."""
        history = []
        for chat in chatbot:
            role_str = chat.get('role')
            content = chat.get('content')
            if role_str and content:
                role = MessageRole.USER if role_str == 'user' else MessageRole.ASSISTANT
                history.append(ChatMessage(role=role, content=content))
        return history

    def _is_follow_up_query(self, message: str, chatbot: list) -> bool:
        """
        Detect if a query is a follow-up to previous conversation.

        Args:
            message: Current user message
            chatbot: Conversation history

        Returns:
            True if this is a follow-up query, False if new problem statement
        """
        # If no conversation history, it's not a follow-up
        if not chatbot or len(chatbot) == 0:
            return False

        # Follow-up indicators
        follow_up_keywords = [
            "more details", "explain", "tell me more", "elaborate",
            "what about", "how about", "can you", "could you",
            "specifically", "example", "clarify", "expand"
        ]

        message_lower = message.lower()

        # Check for follow-up keywords
        has_follow_up_keyword = any(kw in message_lower for kw in follow_up_keywords)

        # Check for question words without problem keywords
        question_words = ["what", "how", "why", "when", "where", "which"]
        problem_keywords = ["problem", "issue", "challenge", "need help", "struggling"]

        has_question = any(qw in message_lower for qw in question_words)
        has_problem = any(pk in message_lower for pk in problem_keywords)

        # If it's a question without problem keywords, it's likely a follow-up
        if has_question and not has_problem:
            return True

        # If it has follow-up keywords, it's a follow-up
        if has_follow_up_keyword:
            return True

        # If message is short (< 50 chars) and conversational, likely follow-up
        if len(message) < 50 and has_question:
            return True

        return False

    def query(
        self,
        mode: str,
        message: str,
        chatbot: list[list[str]]
    ) -> StreamingAgentChatResponse:
        """
        Execute a query against the chat engine.

        Args:
            mode: "chat" for conversational, other for single Q&A
            message: User message
            chatbot: Conversation history

        Returns:
            Streaming response from the chat engine
        """
        logger.debug(f"Query mode: {mode}, message length: {len(message)}")

        if mode == "chat":
            history = self.get_history(chatbot)
            return self._query_engine.stream_chat(message, history)
        else:
            self._query_engine.reset()
            return self._query_engine.stream_chat(message)


    def query_sales_mode(
        self,
        message: str,
        selected_offerings: Optional[list[str]] = None,
        chatbot: list = None
    ) -> StreamingAgentChatResponse:
        """
        Execute sales enablement query with intelligent mode detection.

        Workflow:
        1. Classify query (problem_solving vs pitch modes)
        2. If problem_solving: analyze ALL offerings and recommend bundle
        3. If pitch: use selected offerings
        4. Generate response with offering context

        Args:
            message: User's query
            selected_offerings: Pre-selected offerings for pitch mode
            chatbot: Conversation history

        Returns:
            Streaming response with sales-optimized content
        """
        logger.info(f"Sales mode query: {message[:100]}...")

        # Step 1: Classify the query
        classification = self._query_classifier.classify(
            query=message,
            selected_offerings=selected_offerings
        )

        mode = classification["mode"]
        logger.info(f"Query classified as: {mode} (confidence: {classification['confidence']})")

        # Get all nodes for analysis
        all_nodes = self._ingestion.get_ingested_nodes()

        # Get list of available offerings from nodes
        available_offerings = list(set([
            node.metadata.get("offering_name")
            for node in all_nodes
            if node.metadata.get("offering_name")
        ]))

        logger.info(f"Available offerings: {available_offerings}")

        # Step 2: Handle different modes
        if mode == "problem_solving":
            # Check if this is a follow-up query
            is_follow_up = self._is_follow_up_query(message, chatbot)

            if is_follow_up:
                logger.info("Detected follow-up query - skipping analysis, using existing engine")
                # Use existing engine and filter - no need to run analysis again
                offering_filter = self._current_offering_filter
                # ChatMemoryBuffer in CondensePlusContextChatEngine will handle conversation history automatically
                response_prefix = ""
            else:
                # Analyze problem and recommend offering bundle using pre-generated synopses
                logger.info("New problem - running offering analysis")

                # Load pre-generated synopses
                all_synopses = self._ingestion.get_all_synopses()

                # Extract synopsis text for available offerings
                offering_synopses = {}
                for offering_name in available_offerings:
                    # Find synopsis by offering name
                    for offering_id, synopsis_data in all_synopses.items():
                        if synopsis_data.get("offering_name") == offering_name:
                            offering_synopses[offering_name] = synopsis_data.get("synopsis", "")
                            break

                logger.info(f"Loaded {len(offering_synopses)} synopses for problem analysis")

                # If no synopses available, log warning
                if not offering_synopses:
                    logger.warning("No synopses available for problem analysis. Please ensure synopses are generated after document upload.")

                analysis_result = self._offering_analyzer.analyze_problem(
                    problem_description=classification["problem_description"],
                    offering_synopses=offering_synopses,
                    customer_name=classification.get("customer_name"),
                    industry=classification.get("industry"),
                    top_n=3
                )

                recommended_offerings = analysis_result["recommended_offerings"]
                logger.info(f"Recommended offerings: {recommended_offerings}")

                # Generate high-level implementation plan
                implementation_plan = ""
                if recommended_offerings:
                    logger.info("Generating high-level implementation plan...")
                    implementation_plan = self._offering_analyzer.generate_implementation_plan(
                        recommended_offerings=recommended_offerings,
                        offering_synopses=offering_synopses,
                        problem_description=classification["problem_description"],
                        customer_name=classification.get("customer_name"),
                        industry=classification.get("industry")
                    )
                    logger.info(f"Implementation plan generated: {len(implementation_plan)} chars")

                # Refine plan with detailed offering content
                refined_plan = ""
                if implementation_plan and recommended_offerings:
                    logger.info("Refining plan with detailed offering content...")
                    refined_plan = self._refine_plan_with_details(
                        implementation_plan=implementation_plan,
                        recommended_offerings=recommended_offerings,
                        all_nodes=all_nodes,
                        problem_description=classification["problem_description"]
                    )
                    logger.info(f"Refined plan generated: {len(refined_plan)} chars")

                # Use recommended offerings as filter
                offering_filter = recommended_offerings if recommended_offerings else None

                # Let LLM handle response format adaptation based on system prompt
                # Build context message with offering recommendations for LLM
                logger.info("Providing offering context to LLM for adaptive response generation")

                explanations = analysis_result.get("explanations", {})
                bundle_strategy = analysis_result.get("bundle_strategy", "")

                llm_context = f"\n\n**System Context for Response:**\n"
                llm_context += f"Based on the problem analysis, the recommended offerings are:\n"
                for i, offering in enumerate(recommended_offerings, 1):
                    explanation = explanations.get(offering, "")
                    llm_context += f"{i}. {offering}: {explanation}\n"

                llm_context += f"\n**Bundle Strategy:** {bundle_strategy}\n"

                if implementation_plan:
                    llm_context += f"\n**Implementation Overview:** {implementation_plan[:500]}...\n"

                llm_context += f"\n**Note:** Adapt your response format based on the user's query. "
                llm_context += f"If they ask for a specific format (elevator pitch, summary, detailed, etc.), provide it. "
                llm_context += f"Otherwise, use the default comprehensive format with recommended offerings, strategy, and implementation approach.\n"

                # Append context to message for LLM
                message = message + llm_context
                response_prefix = ""

        elif mode == "offering_summary":
            # Comprehensive retrieval for specific offering
            offering_name = classification.get("offering_mentioned")
            if offering_name:
                logger.info(f"Offering summary mode for: {offering_name}")
                offering_filter = [offering_name]
                response_prefix = f"## {offering_name} - Comprehensive Summary\n\n"
            else:
                logger.warning("Offering summary requested but no offering mentioned")
                offering_filter = selected_offerings
                response_prefix = ""

        else:  # pitch_specific or pitch_generic
            logger.info(f"Pitch mode: using selected offerings")
            offering_filter = selected_offerings
            response_prefix = ""

        # Step 3: Set engine with offering filter
        self.set_engine(offering_filter=offering_filter)

        # Step 4: Generate response
        # CondensePlusContextChatEngine's ChatMemoryBuffer automatically manages conversation history
        # We only reset() for the first message in a new conversation
        if not chatbot:
            # First message in conversation - reset memory buffer
            self._query_engine.reset()
            logger.info("Starting new conversation - reset memory buffer")

        # ChatMemoryBuffer will automatically:
        # 1. Store this query and response in memory
        # 2. Use CONDENSED_CONTEXT_PROMPT to condense follow-up questions with history
        # 3. Retrieve relevant context from the memory buffer
        response = self._query_engine.stream_chat(message)

        # Add prefix to response if needed
        if response_prefix:
            # Note: For streaming responses, we'll need to prepend this in the UI layer
            # Store it as an attribute for the UI to access
            response.response_prefix = response_prefix

        return response

    def _refine_plan_with_details(
        self,
        implementation_plan: str,
        recommended_offerings: list[str],
        all_nodes: list,
        problem_description: str
    ) -> str:
        """
        Refine the implementation plan by incorporating detailed offering content.

        This sends the high-level plan along with detailed node content to the LLM
        for sensitization and refinement with specific technical details.

        Args:
            implementation_plan: High-level implementation plan
            recommended_offerings: List of recommended offering names
            all_nodes: All document nodes
            problem_description: Customer's problem statement

        Returns:
            Refined implementation plan with detailed technical content
        """
        # Get detailed content for recommended offerings
        offering_details = {}
        for offering_name in recommended_offerings:
            # Find all nodes for this offering
            offering_nodes = [
                node for node in all_nodes
                if node.metadata.get("offering_name") == offering_name
            ]

            # Combine node content (limit to prevent token overflow)
            if offering_nodes:
                combined_content = "\n\n".join([node.get_content() for node in offering_nodes[:10]])
                # Limit to ~5000 chars per offering
                offering_details[offering_name] = combined_content[:5000]

        # Build context for refinement
        detailed_context = "\n\n---\n\n".join([
            f"# {offering_name}\n\n{content}"
            for offering_name, content in offering_details.items()
        ])

        refinement_prompt = f"""You are a senior solutions architect refining an implementation plan with technical details.

**Customer Problem:**
{problem_description}

**High-Level Implementation Plan:**
{implementation_plan}

**Detailed Offering Documentation:**
{detailed_context}

Your Task:
Refine the implementation plan by:
1. Adding specific technical details from the documentation
2. Incorporating actual features, APIs, and capabilities mentioned in the offering details
3. Providing concrete configuration examples where applicable
4. Highlighting specific integration points and technical dependencies
5. Adding realistic timelines based on the technical complexity

Keep the same structure as the high-level plan but enrich each phase with:
- Specific technical components from the documentation
- Actual feature names and capabilities
- Configuration considerations
- Technical prerequisites and dependencies

Write in a professional, technically accurate tone (400-500 words).

Refined Implementation Plan:"""

        try:
            response = self._default_model.complete(refinement_prompt)
            refined_plan = response.text.strip()
            logger.debug(f"Refined plan: {len(refined_plan)} chars")
            return refined_plan
        except Exception as e:
            logger.error(f"Error refining plan: {e}")
            return implementation_plan  # Fallback to original plan

    def _format_problem_solving_response(
        self,
        analysis_result: dict,
        classification: dict,
        implementation_plan: str = "",
        refined_plan: str = ""
    ) -> str:
        """Format problem-solving analysis results for display."""
        recommended = analysis_result["recommended_offerings"]
        scores = analysis_result["offering_scores"]
        explanations = analysis_result["offering_explanations"]
        bundle_strategy = analysis_result["bundle_strategy"]

        # Build formatted response
        output = "# 🎯 Recommended Solution Bundle\n\n"

        # Customer context
        if classification.get("customer_name"):
            output += f"**Customer:** {classification['customer_name']}\n"
        if classification.get("industry"):
            output += f"**Industry:** {classification['industry']}\n"
        output += "\n"

        # Recommended offerings
        output += "## 📊 Top Recommended Offerings\n\n"
        for i, offering in enumerate(recommended, 1):
            explanation = explanations.get(offering, "No explanation available")
            output += f"### {i}. {offering}\n"
            output += f"{explanation}\n\n"

        # Bundle strategy
        output += "## 💡 Bundle Strategy\n\n"
        output += f"{bundle_strategy}\n\n"

        # Implementation plan (if available)
        if implementation_plan:
            output += "---\n\n"
            output += "## 🗺️ High-Level Implementation Plan\n\n"
            output += f"{implementation_plan}\n\n"

        # Refined plan (if available)
        if refined_plan:
            output += "---\n\n"
            output += "## 🔧 Detailed Implementation Roadmap\n\n"
            output += f"{refined_plan}\n\n"

        output += "---\n\n"
        output += "## 📝 Detailed Information\n\n"

        return output
