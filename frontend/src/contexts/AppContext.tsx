/**
 * App Context - Global application state
 *
 * Manages:
 * - Current view (RAG Chat, Analytics, Chat with Data)
 * - Global model selection across all features
 * - Pending analytics file (for SQL Chat → Analytics integration)
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import type { ModelGroup, ModelProvider } from '../types';

export type AppView = 'chat' | 'analytics' | 'sql-chat';

interface AppContextValue {
  // Navigation
  currentView: AppView;
  setCurrentView: (view: AppView) => void;

  // Pending analytics file (for cross-feature integration)
  pendingAnalyticsFile: File | null;
  setPendingAnalyticsFile: (file: File | null) => void;
  analyzeInDashboard: (file: File) => void;

  // Model state (passed down from useModels hook)
  models: ModelGroup[];
  selectedModel: string;
  selectedProvider: ModelProvider;
  isLoadingModels: boolean;
  selectModel: (model: string, provider: ModelProvider) => void;
  setModelsState: (state: {
    models: ModelGroup[];
    selectedModel: string;
    selectedProvider: ModelProvider;
    isLoadingModels: boolean;
    selectModel: (model: string, provider: ModelProvider) => void;
  }) => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [currentView, setCurrentView] = useState<AppView>('chat');
  const [pendingAnalyticsFile, setPendingAnalyticsFile] = useState<File | null>(null);

  // Model state (synced from useModels hook in AppContent)
  const [modelsState, setModelsStateInternal] = useState<{
    models: ModelGroup[];
    selectedModel: string;
    selectedProvider: ModelProvider;
    isLoadingModels: boolean;
    selectModel: (model: string, provider: ModelProvider) => void;
  }>({
    models: [],
    selectedModel: '',
    selectedProvider: 'ollama',
    isLoadingModels: true,
    selectModel: () => {},
  });

  const setModelsState = useCallback((state: typeof modelsState) => {
    setModelsStateInternal(state);
  }, []);

  // Helper to set pending file and switch to analytics view
  const analyzeInDashboard = useCallback((file: File) => {
    setPendingAnalyticsFile(file);
    setCurrentView('analytics');
  }, []);

  const value: AppContextValue = {
    currentView,
    setCurrentView,
    pendingAnalyticsFile,
    setPendingAnalyticsFile,
    analyzeInDashboard,
    ...modelsState,
    setModelsState,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}

export { AppContext };
