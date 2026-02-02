import { ArrowLeft, FileText, Loader2 } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { useNotebook, useDocument } from '../../contexts';
import { DocumentCard } from './DocumentCard';
import { DocumentUploader } from './DocumentUploader';
import { WebSearchPanel } from '../Sidebar/WebSearchPanel';

interface DocumentsPageProps {
  onUploadDocument: (file: File) => Promise<boolean>;
  onDeleteDocument: (sourceId: string) => Promise<boolean>;
  onToggleDocument: (sourceId: string, active: boolean) => Promise<boolean>;
  onWebSourcesAdded?: () => void;
}

export function DocumentsPage({
  onUploadDocument,
  onDeleteDocument,
  onToggleDocument,
  onWebSourcesAdded,
}: DocumentsPageProps) {
  const navigate = useNavigate();
  const { notebookId } = useParams<{ notebookId: string }>();
  const { notebooks, selectedNotebook } = useNotebook();
  const { documents, isLoading } = useDocument();

  // Find the notebook
  const notebook = selectedNotebook || notebooks.find(n => n.id === notebookId);

  if (!notebook) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-text-muted hover:text-text mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Chat
        </button>
        <div className="text-center py-12 bg-void-surface rounded-lg border border-void-lighter">
          <FileText className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <h2 className="text-lg font-medium text-text mb-2">No notebook selected</h2>
          <p className="text-text-muted">
            Select a notebook first to manage its documents.
          </p>
        </div>
      </div>
    );
  }

  const activeCount = documents.filter(d => d.active !== false).length;

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate('/')}
          className="p-2 hover:bg-void-surface rounded-lg text-text-muted hover:text-text transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-semibold text-text">
            Documents
          </h1>
          <p className="text-sm text-text-muted">
            {notebook.name} • {activeCount} of {documents.length} active
          </p>
        </div>
      </div>

      {/* Upload Section */}
      <div className="mb-8">
        <h2 className="text-lg font-medium text-text mb-4">Upload Documents</h2>
        <DocumentUploader onUpload={onUploadDocument} />
      </div>

      {/* Web Search Section */}
      <div className="mb-8">
        <h2 className="text-lg font-medium text-text mb-4">Add from Web</h2>
        <div className="bg-void-surface rounded-lg border border-void-lighter p-4">
          <WebSearchPanel
            notebookId={notebook.id}
            onSourcesAdded={onWebSourcesAdded}
          />
        </div>
      </div>

      {/* Documents List */}
      <div>
        <h2 className="text-lg font-medium text-text mb-4">
          Documents ({documents.length})
        </h2>

        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12 bg-void-surface rounded-lg border border-void-lighter">
            <FileText className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h3 className="text-lg font-medium text-text mb-2">No documents yet</h3>
            <p className="text-text-muted">
              Upload documents to use them in RAG queries.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <DocumentCard
                key={doc.source_id}
                document={doc}
                onDelete={onDeleteDocument}
                onToggleActive={onToggleDocument}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
