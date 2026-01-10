import { useEffect } from 'react';
import { MainLayout } from './components/Layout';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/Chat';
import { ToastContainer } from './components/ui';
import { AppProviders, useNotebook, useDocument, SQLChatProvider, useApp } from './contexts';
import { useNotebooks } from './hooks/useNotebooks';
import { useModels } from './hooks/useModels';
import { useToast } from './hooks/useToast';
import { AnalyticsPage, QueryPage } from './pages';
import { SQLChatPage } from './components/SQLChat';

function AppContent() {
  // Use App context for navigation and model state
  const { currentView, setModelsState } = useApp();

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

  // Sync models state with AppContext for the Header
  useEffect(() => {
    setModelsState({
      models,
      selectedModel,
      selectedProvider,
      isLoadingModels,
      selectModel,
    });
  }, [models, selectedModel, selectedProvider, isLoadingModels, selectModel, setModelsState]);

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
      <MainLayout header={<Header />}>
        <AnalyticsPage notebookId={selectedNotebook?.id} />
        <ToastContainer toasts={toasts} onDismiss={removeToast} />
      </MainLayout>
    );
  }

  // Render SQL Chat page
  if (currentView === 'sql-chat') {
    return (
      <MainLayout header={<Header />}>
        <SQLChatPage />
        <ToastContainer toasts={toasts} onDismiss={removeToast} />
      </MainLayout>
    );
  }

  // Render Query API page
  if (currentView === 'query-api') {
    return (
      <MainLayout header={<Header />}>
        <QueryPage />
        <ToastContainer toasts={toasts} onDismiss={removeToast} />
      </MainLayout>
    );
  }

  // Render main Chat view
  return (
    <MainLayout
      header={<Header />}
      sidebar={
        <Sidebar
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

      {/* Toast notifications */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </MainLayout>
  );
}

function App() {
  return (
    <AppProviders>
      <SQLChatProvider>
        <AppContent />
      </SQLChatProvider>
    </AppProviders>
  );
}

export default App;
