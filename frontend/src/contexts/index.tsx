/**
 * Context System for DBNotebook
 *
 * Centralized state management to eliminate prop drilling across the application.
 *
 * Usage:
 *
 * 1. Wrap your app with providers:
 *    <AppProviders>
 *      <App />
 *    </AppProviders>
 *
 * 2. Use hooks in components:
 *    const { notebooks, selectNotebook } = useNotebook();
 *    const { messages, addMessage } = useChat();
 *    const { documents, toggleDocument } = useDocument();
 */

import type { ReactNode } from 'react';
import { ThemeProvider } from './ThemeProvider';
import { NotebookProvider } from './NotebookContext';
import { ChatProvider } from './ChatContext';
import { DocumentProvider } from './DocumentContext';
import { AppProvider } from './AppContext';
import { AuthProvider } from './AuthContext';

/* eslint-disable react-refresh/only-export-components */

// Theme Context (existing)
export { ThemeContext } from './ThemeContext';
export type { Theme, ThemeContextType } from './ThemeContext';
export { ThemeProvider } from './ThemeProvider';
export { useTheme } from './useTheme';

// Notebook Context
export { NotebookProvider, useNotebook } from './NotebookContext';

// Chat Context
export { ChatProvider, useChat } from './ChatContext';

// Document Context
export { DocumentProvider, useDocument } from './DocumentContext';

// Analytics Context
export { AnalyticsProvider, useAnalytics, useCrossFilter } from './AnalyticsContext';

// SQL Chat Context
export { SQLChatProvider, useSQLChat } from './SQLChatContext';

// App Context (global view and model state)
export { AppProvider, useApp } from './AppContext';
export type { AppView } from './AppContext';

// Auth Context
export { AuthProvider, useAuth } from './AuthContext';

/* eslint-enable react-refresh/only-export-components */

/**
 * Combined Provider Component
 *
 * Convenience wrapper that combines all context providers in the correct order.
 *
 * Usage:
 *   <AppProviders>
 *     <App />
 *   </AppProviders>
 */
interface AppProvidersProps {
  children: ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppProvider>
          <NotebookProvider>
            <ChatProvider>
              <DocumentProvider>
                {children}
              </DocumentProvider>
            </ChatProvider>
          </NotebookProvider>
        </AppProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
