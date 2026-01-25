/**
 * V2 Chat Hook - Multi-user safe with conversation memory.
 *
 * Features:
 * - Session ID tracking for conversation continuity
 * - User ID for multi-user support
 * - Automatic history loading on notebook switch
 * - Database-backed conversation persistence
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import type { Message, SourceCitation, MessageMetadata } from '../types';
import * as api from '../services/api';

// Generate a UUID for session tracking
function generateSessionId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Default user ID that exists in the database
// TODO: Replace with actual auth when implemented
const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001';

// Get user ID - currently uses default until auth is implemented
function getUserId(): string {
  return DEFAULT_USER_ID;
}

interface ChatV2State {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;
  sessionId: string | null;
  userId: string;
}

let messageId = 0;

function generateMessageId(): string {
  return `msg_${Date.now()}_${++messageId}`;
}

export interface ChatV2Options {
  model?: string;
  provider?: string;
  // Retrieval settings
  useReranker?: boolean;
  rerankerModel?: 'xsmall' | 'base' | 'large';
  useRaptor?: boolean;
  topK?: number;
}

export function useChatV2(notebookId?: string, options?: ChatV2Options) {
  const { model, provider, useReranker, rerankerModel, useRaptor, topK } = options || {};
  const [state, setState] = useState<ChatV2State>({
    messages: [],
    isLoading: false,
    isStreaming: false,
    error: null,
    sessionId: null,
    userId: getUserId(),
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const loadedNotebookRef = useRef<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  // Load conversation history when notebook changes
  useEffect(() => {
    if (!notebookId || loadedNotebookRef.current === notebookId) {
      return;
    }

    loadedNotebookRef.current = notebookId;

    // Generate new session ID for this notebook
    const newSessionId = generateSessionId();
    sessionIdRef.current = newSessionId;

    // Load history from backend
    const loadHistory = async () => {
      try {
        setState((prev) => ({ ...prev, isLoading: true, error: null }));

        const response = await api.getChatV2History(notebookId, state.userId, 50);

        if (response.success && response.history.length > 0) {
          // Convert history to Message format
          const messages: Message[] = response.history.map((item) => ({
            id: generateMessageId(),
            role: item.role,
            content: item.content,
            timestamp: item.timestamp ? new Date(item.timestamp) : new Date(),
          }));

          setState((prev) => ({
            ...prev,
            messages,
            sessionId: newSessionId,
            isLoading: false,
          }));
        } else {
          // No history, start fresh
          setState((prev) => ({
            ...prev,
            messages: [],
            sessionId: newSessionId,
            isLoading: false,
          }));
        }
      } catch (error) {
        console.error('Failed to load chat history:', error);
        // Start fresh on error
        setState((prev) => ({
          ...prev,
          messages: [],
          sessionId: newSessionId,
          isLoading: false,
          error: null, // Don't show error for history load failure
        }));
      }
    };

    loadHistory();
  }, [notebookId, state.userId]);

  // Add a user message
  const addUserMessage = useCallback((content: string): Message => {
    const message: Message = {
      id: generateMessageId(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, message],
    }));

    return message;
  }, []);

  // Add an assistant message (starts streaming)
  const addAssistantMessage = useCallback((): Message => {
    const message: Message = {
      id: generateMessageId(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };

    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, message],
      isStreaming: true,
    }));

    return message;
  }, []);

  // Update the streaming message content
  const updateStreamingMessage = useCallback((token: string) => {
    setState((prev) => ({
      ...prev,
      messages: prev.messages.map((msg) =>
        msg.isStreaming ? { ...msg, content: msg.content + token } : msg
      ),
    }));
  }, []);

  // Complete the streaming message
  const completeStreamingMessage = useCallback(
    (sources?: SourceCitation[], metadata?: MessageMetadata, sessionId?: string) => {
      setState((prev) => ({
        ...prev,
        isStreaming: false,
        sessionId: sessionId || prev.sessionId,
        messages: prev.messages.map((msg) =>
          msg.isStreaming
            ? {
                ...msg,
                isStreaming: false,
                sources: sources || msg.sources,
                metadata: metadata || msg.metadata,
              }
            : msg
        ),
      }));
    },
    []
  );

  // Send a message using V2 API with memory
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || !notebookId) return;

      // Cancel any ongoing request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      // Add user message
      addUserMessage(content);

      // Add placeholder assistant message
      addAssistantMessage();

      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      let receivedSources: SourceCitation[] = [];

      try {
        await api.sendChatV2Message(
          {
            notebook_id: notebookId,
            query: content,
            user_id: state.userId,
            // Always include session for conversation memory (mandatory feature)
            session_id: sessionIdRef.current || undefined,
            include_history: true,
            max_history: 10,
            include_sources: true,
            max_sources: 6,
            // Pass selected model and provider from UI
            model: model,
            provider: provider,
            // Retrieval settings
            use_reranker: useReranker,
            reranker_model: rerankerModel,
            use_raptor: useRaptor,
            top_k: topK,
          },
          {
            onContent: (token) => {
              updateStreamingMessage(token);
            },
            onSources: (sources) => {
              receivedSources = sources;
            },
            onComplete: (sessionId, metadata) => {
              sessionIdRef.current = sessionId;
              completeStreamingMessage(receivedSources, metadata, sessionId);
              setState((prev) => ({ ...prev, isLoading: false }));
            },
            onError: (error) => {
              setState((prev) => ({
                ...prev,
                isLoading: false,
                isStreaming: false,
                error,
                // Remove the empty assistant message on error
                messages: prev.messages.filter((m) => !m.isStreaming || m.content),
              }));
            },
          }
        );
      } catch (error) {
        setState((prev) => ({
          ...prev,
          isLoading: false,
          isStreaming: false,
          error: error instanceof Error ? error.message : 'Failed to send message',
        }));
      }
    },
    [
      notebookId,
      state.userId,
      model,
      provider,
      useReranker,
      rerankerModel,
      useRaptor,
      topK,
      addUserMessage,
      addAssistantMessage,
      updateStreamingMessage,
      completeStreamingMessage,
    ]
  );

  // Clear all messages (both local and backend)
  const clearMessages = useCallback(async () => {
    if (!notebookId) return;

    try {
      await api.clearChatV2History(notebookId, state.userId);

      // Generate new session ID
      const newSessionId = generateSessionId();
      sessionIdRef.current = newSessionId;

      setState((prev) => ({
        ...prev,
        messages: [],
        sessionId: newSessionId,
        error: null,
      }));
    } catch (error) {
      console.error('Failed to clear chat history:', error);
      // Clear locally anyway
      setState((prev) => ({
        ...prev,
        messages: [],
        error: null,
      }));
    }
  }, [notebookId, state.userId]);

  // Stop streaming
  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    completeStreamingMessage();
    setState((prev) => ({ ...prev, isLoading: false, isStreaming: false }));
  }, [completeStreamingMessage]);

  // Edit a message (resend from that point)
  const editMessage = useCallback(
    async (messageId: string, newContent: string) => {
      const index = state.messages.findIndex((m) => m.id === messageId);
      if (index === -1 || state.messages[index].role !== 'user') return;

      // Remove all messages after this one
      setState((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, index),
      }));

      // Send the edited message
      await sendMessage(newContent);
    },
    [state.messages, sendMessage]
  );

  // Remove a message
  const removeMessage = useCallback((messageId: string) => {
    setState((prev) => ({
      ...prev,
      messages: prev.messages.filter((m) => m.id !== messageId),
    }));
  }, []);

  return {
    messages: state.messages,
    isLoading: state.isLoading,
    isStreaming: state.isStreaming,
    error: state.error,
    sessionId: state.sessionId,
    userId: state.userId,
    sendMessage,
    clearMessages,
    stopStreaming,
    editMessage,
    removeMessage,
  };
}
