import { useEffect, useState } from 'react';
import { MainLayout } from './components/Layout';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/Chat';
import { ToastContainer } from './components/ui';
import { AppProviders, useNotebook, useDocument, SQLChatProvider } from './contexts';
import { useNotebooks } from './hooks/useNotebooks';
import { useModels } from './hooks/useModels';
import { useToast } from './hooks/useToast';
import { AnalyticsPage } from './pages';
import { SQLChatPage } from './components/SQLChat';

type AppView = 'chat' | 'analytics' | 'sql-chat';

function AppContent() {
  // View state for navigation
  const [currentView, setCurrentView] = useState<AppView>('chat');

  // Use hooks for API logic
  const {
    notebooks,
    selectedNotebook,
    documents,
    isLoadingDocs,
    error: notebooksError,
    selectNotebook,
    createNotebook,
    updateNotebook,
    deleteNotebook,
    uploadDocument,
    deleteDocument,
    toggleDocumentActive,
  } = useNotebooks();

  const {
    models,
    selectedModel,
    selectedProvider,
    isLoading: isLoadingModels,
    error: modelsError,
    selectModel,
  } = useModels();

  const { toasts, removeToast, success, error: showError } = useToast();

  // Get context setters to sync hook state with contexts
  const notebookContext = useNotebook();
  const documentContext = useDocument();

  // Sync notebooks hook state with context
  useEffect(() => {
    notebookContext.setNotebooks(notebooks);
  }, [notebooks, notebookContext]);

  useEffect(() => {
    notebookContext.selectNotebook(selectedNotebook);
  }, [selectedNotebook, notebookContext]);

  // Sync documents hook state with context
  useEffect(() => {
    documentContext.setDocuments(documents);
  }, [documents, documentContext]);

  useEffect(() => {
    documentContext.setLoading(isLoadingDocs);
  }, [isLoadingDocs, documentContext]);

  // Show errors from hooks as toasts
  useEffect(() => {
    if (notebooksError) {
      console.error('Notebooks API error:', notebooksError);
      showError(`Notebooks: ${notebooksError}`);
    }
  }, [notebooksError, showError]);

  useEffect(() => {
    if (modelsError) {
      console.error('Models API error:', modelsError);
      showError(`Models: ${modelsError}`);
    }
  }, [modelsError, showError]);

  // Handle file upload with toast notifications
  const handleFileUpload = async (file: File): Promise<boolean> => {
    const result = await uploadDocument(file);
    if (result) {
      success(`Uploaded: ${file.name}`);
    } else {
      showError(`Failed to upload: ${file.name}`);
    }
    return result;
  };

  // Handle document deletion with toast
  const handleDeleteDocument = async (sourceId: string): Promise<boolean> => {
    const result = await deleteDocument(sourceId);
    if (result) {
      success('Document removed');
    } else {
      showError('Failed to remove document');
    }
    return result;
  };

  // Handle copy to clipboard
  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
    success('Copied to clipboard');
  };

  // Handle web sources added - refresh documents
  const handleWebSourcesAdded = () => {
    if (selectedNotebook) {
      selectNotebook(selectedNotebook);
    }
  };

  // Render Analytics page
  if (currentView === 'analytics') {
    return (
      <>
        <AnalyticsPage
          onBack={() => setCurrentView('chat')}
          notebookId={selectedNotebook?.id}
        />
        <ToastContainer toasts={toasts} onDismiss={removeToast} />
      </>
    );
  }

  // Render SQL Chat page
  if (currentView === 'sql-chat') {
    return (
      <SQLChatProvider>
        <SQLChatPage />
        <ToastContainer toasts={toasts} onDismiss={removeToast} />
      </SQLChatProvider>
    );
  }

  // Render main Chat view
  return (
    <>
      <MainLayout
        sidebar={
          <Sidebar
            // Models (not in context yet)
            models={models}
            selectedModel={selectedModel}
            selectedProvider={selectedProvider}
            onSelectModel={selectModel}
            isLoadingModels={isLoadingModels}
            // Document operations (still needed for toasts)
            onUploadDocument={handleFileUpload}
            onDeleteDocument={handleDeleteDocument}
            onToggleDocument={toggleDocumentActive}
            // Notebook operations
            onSelectNotebook={selectNotebook}
            onCreateNotebook={createNotebook}
            onDeleteNotebook={deleteNotebook}
            onUpdateNotebook={updateNotebook}
            // Web search callback
            onWebSourcesAdded={handleWebSourcesAdded}
            // Analytics navigation
            onNavigateAnalytics={() => setCurrentView('analytics')}
            // SQL Chat navigation
            onNavigateSQLChat={() => setCurrentView('sql-chat')}
          />
        }
      >
        <ChatArea
          notebookId={selectedNotebook?.id}
          notebookName={selectedNotebook?.name}
          selectedModel={selectedModel}
          onCopy={handleCopy}
          onFileUpload={handleFileUpload}
        />
      </MainLayout>

      {/* Toast notifications */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </>
  );
}

function App() {
  return (
    <AppProviders>
      <AppContent />
    </AppProviders>
  );
}

export default App;
