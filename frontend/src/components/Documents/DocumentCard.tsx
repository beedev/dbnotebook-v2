import { useState } from 'react';
import {
  FileText,
  Trash2,
  ToggleRight,
  ToggleLeft,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react';
import type { Document } from '../../types';

interface DocumentCardProps {
  document: Document;
  onDelete: (sourceId: string) => Promise<boolean>;
  onToggleActive: (sourceId: string, active: boolean) => Promise<boolean>;
}

export function DocumentCard({ document, onDelete, onToggleActive }: DocumentCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isToggling, setIsToggling] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete "${document.filename}"?`)) return;
    setIsDeleting(true);
    try {
      await onDelete(document.source_id);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleToggle = async () => {
    setIsToggling(true);
    try {
      await onToggleActive(document.source_id, !document.active);
    } finally {
      setIsToggling(false);
    }
  };

  const isActive = document.active !== false;

  return (
    <div className={`bg-void-surface rounded-lg border transition-colors ${
      isActive ? 'border-void-lighter' : 'border-void-lighter/50 opacity-60'
    }`}>
      {/* Header */}
      <div className="flex items-center gap-3 p-4">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
          isActive ? 'bg-primary/10' : 'bg-void-lighter'
        }`}>
          <FileText className={`w-5 h-5 ${isActive ? 'text-primary' : 'text-text-muted'}`} />
        </div>

        <div className="flex-1 min-w-0">
          <h3 className={`font-medium truncate ${isActive ? 'text-text' : 'text-text-muted'}`}>
            {document.filename}
          </h3>
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <span>{document.chunk_count || 0} chunks</span>
            {document.file_type && (
              <>
                <span>•</span>
                <span>{document.file_type.toUpperCase()}</span>
              </>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleToggle}
            disabled={isToggling}
            className={`p-2 rounded-lg transition-colors ${
              isActive
                ? 'text-green-400 hover:bg-green-400/10'
                : 'text-text-muted hover:bg-void-lighter'
            }`}
            title={isActive ? 'Disable in RAG' : 'Enable in RAG'}
          >
            {isToggling ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : isActive ? (
              <ToggleRight className="w-5 h-5" />
            ) : (
              <ToggleLeft className="w-5 h-5" />
            )}
          </button>

          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="p-2 rounded-lg text-text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors"
            title="Delete document"
          >
            {isDeleting ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Trash2 className="w-5 h-5" />
            )}
          </button>

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 rounded-lg text-text-muted hover:text-text hover:bg-void-lighter transition-colors"
          >
            {isExpanded ? (
              <ChevronUp className="w-5 h-5" />
            ) : (
              <ChevronDown className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-void-lighter/50 pt-3">
          {document.dense_summary ? (
            <p className="text-sm text-text-muted line-clamp-3">
              {document.dense_summary}
            </p>
          ) : (
            <p className="text-sm text-text-muted italic">
              No summary available
            </p>
          )}
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            {document.file_type && (
              <span className="px-2 py-1 bg-void-lighter rounded text-text-muted">
                {document.file_type.toUpperCase()}
              </span>
            )}
            {document.uploadedAt && (
              <span className="px-2 py-1 bg-void-lighter rounded text-text-muted">
                Added {formatDate(document.uploadedAt.toString())}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
