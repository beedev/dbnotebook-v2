import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { Message, ModelProvider } from '../types';

interface ChatContextType {
  // State
  messages: Message[];
  isStreaming: boolean;
  isLoading: boolean;
  selectedModel: string;
  selectedProvider: ModelProvider;
  error: string | null;

  // Actions
  addMessage: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  clearMessages: () => void;
  setMessages: (messages: Message[]) => void;
  setStreaming: (streaming: boolean) => void;
  setLoading: (loading: boolean) => void;
  setModel: (model: string, provider: ModelProvider) => void;
  removeMessage: (id: string) => void;
  clearError: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessagesState] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState<string>('llama3.1:latest');
  const [selectedProvider, setSelectedProvider] = useState<ModelProvider>('ollama');
  const [error, setError] = useState<string | null>(null);

  // Add a new message to the conversation
  const addMessage = useCallback((message: Message) => {
    setMessagesState((prev) => [...prev, message]);
    setError(null);
  }, []);

  // Update an existing message (useful for streaming updates)
  const updateMessage = useCallback((id: string, updates: Partial<Message>) => {
    setMessagesState((prev) =>
      prev.map((msg) =>
        msg.id === id
          ? { ...msg, ...updates }
          : msg
      )
    );
    setError(null);
  }, []);

  // Clear all messages
  const clearMessages = useCallback(() => {
    setMessagesState([]);
    setError(null);
  }, []);

  // Set messages from external source (e.g., loading conversation history)
  const setMessages = useCallback((newMessages: Message[]) => {
    setMessagesState(newMessages);
    setError(null);
  }, []);

  // Control streaming state
  const setStreaming = useCallback((streaming: boolean) => {
    setIsStreaming(streaming);
    if (streaming) {
      setError(null);
    }
  }, []);

  // Control loading state
  const setLoading = useCallback((loading: boolean) => {
    setIsLoading(loading);
    if (loading) {
      setError(null);
    }
  }, []);

  // Update selected model and provider
  const setModel = useCallback((model: string, provider: ModelProvider) => {
    setSelectedModel(model);
    setSelectedProvider(provider);
    setError(null);
  }, []);

  // Remove a specific message
  const removeMessage = useCallback((id: string) => {
    setMessagesState((prev) => prev.filter((msg) => msg.id !== id));
    setError(null);
  }, []);

  // Clear error state
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: ChatContextType = {
    messages,
    isStreaming,
    isLoading,
    selectedModel,
    selectedProvider,
    error,
    addMessage,
    updateMessage,
    clearMessages,
    setMessages,
    setStreaming,
    setLoading,
    setModel,
    removeMessage,
    clearError,
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChat() {
  const context = useContext(ChatContext);

  if (!context) {
    throw new Error('useChat must be used within ChatProvider');
  }

  return context;
}
