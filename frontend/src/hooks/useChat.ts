import { useState, useCallback, useRef } from 'react';
import type { Message, ChatState, SourceCitation } from '../types';
import * as api from '../services/api';

const initialState: ChatState = {
  messages: [],
  isLoading: false,
  isStreaming: false,
  error: null,
};

let messageId = 0;

function generateId(): string {
  return `msg_${Date.now()}_${++messageId}`;
}

export function useChat(notebookId?: string, model?: string) {
  const [state, setState] = useState<ChatState>(initialState);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Add a user message
  const addUserMessage = useCallback((content: string): Message => {
    const message: Message = {
      id: generateId(),
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
      id: generateId(),
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
  const completeStreamingMessage = useCallback((images?: string[], sources?: SourceCitation[]) => {
    setState((prev) => ({
      ...prev,
      isStreaming: false,
      messages: prev.messages.map((msg) =>
        msg.isStreaming
          ? {
              ...msg,
              isStreaming: false,
              images: images || msg.images,
              sources: sources || msg.sources,
            }
          : msg
      ),
    }));
  }, []);

  // Send a message
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

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

      let generatedImages: string[] = [];

      try {
        await api.sendChatMessage(
          {
            message: content,
            notebook_id: notebookId,
            model: model,
            stream: true,
          },
          {
            onToken: (token) => {
              updateStreamingMessage(token);
            },
            onComplete: (_fullResponse, sources) => {
              completeStreamingMessage(
                generatedImages.length > 0 ? generatedImages : undefined,
                sources
              );
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
            onImages: (images) => {
              generatedImages = images;
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
      model,
      addUserMessage,
      addAssistantMessage,
      updateStreamingMessage,
      completeStreamingMessage,
    ]
  );

  // Clear all messages
  const clearMessages = useCallback(async () => {
    try {
      await api.clearChat();
      setState(initialState);
    } catch (error) {
      console.error('Failed to clear chat:', error);
      // Clear locally anyway
      setState(initialState);
    }
  }, []);

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
    ...state,
    sendMessage,
    clearMessages,
    stopStreaming,
    editMessage,
    removeMessage,
  };
}
