import { useEffect } from 'react';
import { MainLayout } from './components/Layout';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/Chat';
import { ToastContainer } from './components/ui';
import { useNotebooks } from './hooks/useNotebooks';
import { useModels } from './hooks/useModels';
import { useToast } from './hooks/useToast';

function App() {
  const {
    notebooks,
    selectedNotebook,
    documents,
    isLoading: isLoadingNotebooks,
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

  return (
    <>
      <MainLayout
        sidebar={
          <Sidebar
            // Notebooks
            notebooks={notebooks}
            selectedNotebook={selectedNotebook}
            onSelectNotebook={selectNotebook}
            onCreateNotebook={createNotebook}
            onDeleteNotebook={deleteNotebook}
            onUpdateNotebook={updateNotebook}
            isLoadingNotebooks={isLoadingNotebooks}
            // Models
            models={models}
            selectedModel={selectedModel}
            selectedProvider={selectedProvider}
            onSelectModel={selectModel}
            isLoadingModels={isLoadingModels}
            // Documents
            documents={documents}
            onUploadDocument={handleFileUpload}
            onDeleteDocument={handleDeleteDocument}
            onToggleDocument={toggleDocumentActive}
            isLoadingDocs={isLoadingDocs}
            // Web Search - refresh documents after adding web sources
            onWebSourcesAdded={() => {
              // Re-fetch documents to include newly added web sources
              if (selectedNotebook) {
                selectNotebook(selectedNotebook);
              }
            }}
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

export default App;
