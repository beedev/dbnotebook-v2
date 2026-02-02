/**
 * Documents Management Page
 *
 * Dedicated page for managing documents within a notebook.
 * Accessed via the "Manage Documents" button in notebook header.
 */

import { Header } from '../components/Header';
import { MainLayout } from '../components/Layout';
import { DocumentsPage } from '../components/Documents';
import { useNotebooks } from '../hooks/useNotebooks';
import { useToast } from '../hooks/useToast';
import { ToastContainer } from '../components/ui';
import { useNotebook } from '../contexts';

export function DocumentsManagementPage() {
  const { toasts, removeToast, success, error: showError } = useToast();
  const { selectedNotebook, selectNotebook } = useNotebook();
  const {
    uploadDocument,
    deleteDocument,
    toggleDocumentActive,
  } = useNotebooks();

  const handleUpload = async (file: File): Promise<boolean> => {
    const result = await uploadDocument(file);
    if (result) {
      success(`Uploaded: ${file.name}`);
    } else {
      showError(`Failed to upload: ${file.name}`);
    }
    return result;
  };

  const handleDelete = async (sourceId: string): Promise<boolean> => {
    const result = await deleteDocument(sourceId);
    if (result) {
      success('Document removed');
    } else {
      showError('Failed to remove document');
    }
    return result;
  };

  const handleWebSourcesAdded = () => {
    // Refresh documents by re-selecting the notebook
    if (selectedNotebook) {
      selectNotebook(selectedNotebook);
    }
    success('Web content added');
  };

  return (
    <MainLayout header={<Header />}>
      <DocumentsPage
        onUploadDocument={handleUpload}
        onDeleteDocument={handleDelete}
        onToggleDocument={toggleDocumentActive}
        onWebSourcesAdded={handleWebSourcesAdded}
      />
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </MainLayout>
  );
}

export default DocumentsManagementPage;
