"""
Integration test for Conversation Persistence functionality.

Tests end-to-end workflow:
1. Pipeline initialization with database
2. Notebook switching with conversation history
3. Message persistence (save/load)
4. Conversation history retrieval
5. Multi-notebook conversation isolation
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_chatbot.pipeline import LocalRAGPipeline
from rag_chatbot.core.db import DatabaseManager
from rag_chatbot.core.notebook import NotebookManager
from uuid import uuid4


def test_conversation_integration():
    """Test complete conversation persistence workflow."""
    print("\n" + "=" * 60)
    print("CONVERSATION PERSISTENCE INTEGRATION TEST")
    print("=" * 60)

    # Database URL
    DATABASE_URL = "postgresql://postgres:root@localhost:5432/rag_chatbot_dev"

    # Step 1: Initialize pipeline with database
    print("\n[1/8] Initializing pipeline with database...")
    pipeline = LocalRAGPipeline(
        host="localhost",
        database_url=DATABASE_URL
    )
    print("✅ Pipeline initialized with database connection")

    # Verify database components
    assert pipeline._db_manager is not None, "DatabaseManager not initialized"
    assert pipeline._conversation_store is not None, "ConversationStore not initialized"
    print("✅ Database components verified")

    # Step 2: Set up notebooks
    print("\n[2/8] Creating test notebooks...")
    db_manager = DatabaseManager(DATABASE_URL)
    db_manager.init_db()
    notebook_manager = NotebookManager(db_manager)

    # Ensure default user exists
    user_id = notebook_manager.ensure_default_user()
    print(f"✅ Default user: {user_id}")

    # Create two notebooks for testing
    notebook1_name = f"Conversation Test Notebook 1 {uuid4().hex[:8]}"
    notebook2_name = f"Conversation Test Notebook 2 {uuid4().hex[:8]}"

    notebook1 = notebook_manager.create_notebook(
        user_id=user_id,
        name=notebook1_name,
        description="First test notebook for conversation persistence"
    )
    notebook1_id = notebook1["notebook_id"]

    notebook2 = notebook_manager.create_notebook(
        user_id=user_id,
        name=notebook2_name,
        description="Second test notebook for conversation persistence"
    )
    notebook2_id = notebook2["notebook_id"]

    print(f"✅ Created notebook 1: {notebook1_id}")
    print(f"✅ Created notebook 2: {notebook2_id}")

    # Step 3: Switch to notebook 1 and save some messages
    print("\n[3/8] Testing message persistence in notebook 1...")
    pipeline.switch_notebook(notebook1_id, user_id)
    print(f"✅ Switched to notebook 1: {notebook1_id}")

    # Save a conversation exchange
    user_msg_1 = "What is RAG?"
    assistant_msg_1 = "RAG stands for Retrieval-Augmented Generation, a technique that combines information retrieval with language generation."

    success = pipeline.save_conversation_exchange(
        notebook_id=notebook1_id,
        user_id=user_id,
        user_message=user_msg_1,
        assistant_message=assistant_msg_1
    )
    assert success, "Failed to save first conversation exchange"
    print("✅ Saved first conversation exchange")

    # Save another exchange
    user_msg_2 = "Can you give an example?"
    assistant_msg_2 = "Sure! When you ask a question, RAG first retrieves relevant documents, then generates an answer based on those documents."

    success = pipeline.save_conversation_exchange(
        notebook_id=notebook1_id,
        user_id=user_id,
        user_message=user_msg_2,
        assistant_message=assistant_msg_2
    )
    assert success, "Failed to save second conversation exchange"
    print("✅ Saved second conversation exchange")

    # Verify message count
    message_count = pipeline._conversation_store.get_message_count(notebook1_id)
    assert message_count == 4, f"Expected 4 messages, got {message_count}"
    print(f"✅ Message count verified: {message_count} messages")

    # Step 4: Switch to notebook 2 and save different messages
    print("\n[4/8] Testing message persistence in notebook 2...")
    pipeline.switch_notebook(notebook2_id, user_id)
    print(f"✅ Switched to notebook 2: {notebook2_id}")

    # Save messages in notebook 2
    user_msg_3 = "What is LlamaIndex?"
    assistant_msg_3 = "LlamaIndex is a data framework for building LLM applications with external data sources."

    success = pipeline.save_conversation_exchange(
        notebook_id=notebook2_id,
        user_id=user_id,
        user_message=user_msg_3,
        assistant_message=assistant_msg_3
    )
    assert success, "Failed to save conversation in notebook 2"
    print("✅ Saved conversation exchange in notebook 2")

    # Verify message count in notebook 2
    message_count_2 = pipeline._conversation_store.get_message_count(notebook2_id)
    assert message_count_2 == 2, f"Expected 2 messages in notebook 2, got {message_count_2}"
    print(f"✅ Message count verified for notebook 2: {message_count_2} messages")

    # Step 5: Switch back to notebook 1 and verify history is loaded
    print("\n[5/8] Testing conversation history loading...")
    pipeline.switch_notebook(notebook1_id, user_id)
    print(f"✅ Switched back to notebook 1")

    # Retrieve conversation history
    history = pipeline._conversation_store.get_conversation_history(
        notebook_id=notebook1_id,
        user_id=user_id
    )

    print(f"✅ Retrieved {len(history)} messages from notebook 1")
    assert len(history) == 4, f"Expected 4 messages, got {len(history)}"

    # Verify message content
    assert history[0]["role"] == "user", "First message should be user"
    assert history[0]["content"] == user_msg_1, "First message content mismatch"
    assert history[1]["role"] == "assistant", "Second message should be assistant"
    assert history[1]["content"] == assistant_msg_1, "Second message content mismatch"
    print("✅ Message content verified")

    # Verify messages are ordered by timestamp
    timestamps = [msg["timestamp"] for msg in history]
    assert timestamps == sorted(timestamps), "Messages not ordered by timestamp"
    print("✅ Message ordering verified")

    # Step 6: Test conversation isolation
    print("\n[6/8] Testing conversation isolation between notebooks...")
    history_1 = pipeline._conversation_store.get_conversation_history(
        notebook_id=notebook1_id,
        user_id=user_id
    )
    history_2 = pipeline._conversation_store.get_conversation_history(
        notebook_id=notebook2_id,
        user_id=user_id
    )

    assert len(history_1) == 4, "Notebook 1 should have 4 messages"
    assert len(history_2) == 2, "Notebook 2 should have 2 messages"

    # Verify no message content overlap
    notebook1_contents = set(msg["content"] for msg in history_1)
    notebook2_contents = set(msg["content"] for msg in history_2)
    assert not notebook1_contents.intersection(notebook2_contents), \
        "Message content leaked between notebooks"

    print("✅ Conversation isolation verified")

    # Step 7: Test clearing history
    print("\n[7/8] Testing conversation history clearing...")
    cleared = pipeline._conversation_store.clear_notebook_history(notebook2_id)
    assert cleared, "Failed to clear notebook 2 history"
    print("✅ Cleared notebook 2 history")

    # Verify notebook 2 has no messages
    message_count_after_clear = pipeline._conversation_store.get_message_count(notebook2_id)
    assert message_count_after_clear == 0, f"Expected 0 messages after clear, got {message_count_after_clear}"
    print("✅ Verified notebook 2 is empty")

    # Verify notebook 1 still has messages
    message_count_1_after = pipeline._conversation_store.get_message_count(notebook1_id)
    assert message_count_1_after == 4, f"Notebook 1 should still have 4 messages"
    print("✅ Verified notebook 1 still has messages")

    # Step 8: Test last activity tracking
    print("\n[8/8] Testing last activity tracking...")
    last_activity_1 = pipeline._conversation_store.get_last_activity(notebook1_id)
    last_activity_2 = pipeline._conversation_store.get_last_activity(notebook2_id)

    assert last_activity_1 is not None, "Notebook 1 should have last activity"
    assert last_activity_2 is None, "Notebook 2 should have no last activity (cleared)"
    print(f"✅ Last activity for notebook 1: {last_activity_1}")
    print("✅ Last activity tracking verified")

    # Cleanup
    print("\n[CLEANUP] Removing test notebooks...")
    notebook_manager.delete_notebook(notebook1_id)
    notebook_manager.delete_notebook(notebook2_id)
    print("✅ Test notebooks deleted")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_conversation_integration()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
