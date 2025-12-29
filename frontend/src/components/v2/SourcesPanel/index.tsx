import { useState, useRef, type DragEvent } from 'react';
import { Plus, Upload, FileText, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { SourceCard } from './SourceCard';
import type { Document } from '../../../types';

interface SourcesPanelProps {
  documents: Document[];
  onUpload: (file: File) => Promise<boolean>;
  onDelete: (sourceId: string) => Promise<boolean>;
  onToggleActive: (sourceId: string, active: boolean) => Promise<boolean>;
  isLoading?: boolean;
  notebookSelected?: boolean;
}

export function SourcesPanel({
  documents,
  onUpload,
  onDelete,
  onToggleActive,
  isLoading = false,
  notebookSelected = false,
}: SourcesPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeCount = documents.filter((d) => d.active !== false).length;
  const totalCount = documents.length;

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (notebookSelected) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (!notebookSelected) return;

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      setIsUploading(true);
      for (const file of files) {
        await onUpload(file);
      }
      setIsUploading(false);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    for (const file of Array.from(files)) {
      await onUpload(file);
    }
    setIsUploading(false);

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-3">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-1 py-1 text-left group"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-[var(--color-text-muted)]" />
          ) : (
            <ChevronRight className="w-4 h-4 text-[var(--color-text-muted)]" />
          )}
          <span className="text-sm font-semibold text-[var(--color-text-secondary)] font-[family-name:var(--font-display)]">
            Sources
          </span>
          {totalCount > 0 && (
            <span className="badge text-xs">
              {activeCount}/{totalCount}
            </span>
          )}
        </div>

        {/* Add button */}
        {notebookSelected && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleUploadClick();
            }}
            disabled={isUploading}
            className="p-1.5 rounded-[var(--radius-md)] text-[var(--color-accent)] hover:bg-[var(--color-accent-subtle)] opacity-0 group-hover:opacity-100 transition-all disabled:opacity-50"
            title="Add source"
          >
            <Plus className="w-4 h-4" />
          </button>
        )}
      </button>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt,.docx,.epub,.pptx,.png,.jpg,.jpeg,.webp,.md"
        multiple
        className="hidden"
        onChange={handleFileSelect}
      />

      {/* Content */}
      {isExpanded && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className="space-y-2"
        >
          {/* Empty state / Drop zone */}
          {!notebookSelected ? (
            <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
              <div className="w-12 h-12 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-3">
                <FileText className="w-6 h-6 text-[var(--color-text-muted)]" />
              </div>
              <p className="text-sm text-[var(--color-text-tertiary)]">
                Select a notebook to add sources
              </p>
            </div>
          ) : totalCount === 0 ? (
            <button
              onClick={handleUploadClick}
              disabled={isUploading}
              className={`
                w-full flex flex-col items-center justify-center py-8 px-4
                border-2 border-dashed rounded-[var(--radius-lg)]
                transition-all duration-[var(--transition-normal)]
                ${isDragging
                  ? 'border-[var(--color-accent)] bg-[var(--color-accent-subtle)]'
                  : 'border-[var(--color-border)] hover:border-[var(--color-accent)] hover:bg-[var(--color-bg-hover)]'
                }
                disabled:opacity-50 disabled:cursor-not-allowed
              `}
            >
              {isUploading ? (
                <Loader2 className="w-8 h-8 text-[var(--color-accent)] animate-spin mb-2" />
              ) : (
                <Upload className="w-8 h-8 text-[var(--color-text-muted)] mb-2" />
              )}
              <p className="text-sm font-medium text-[var(--color-text-secondary)]">
                {isDragging ? 'Drop files here' : 'Add your first source'}
              </p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                PDF, DOCX, PPTX, TXT, Images
              </p>
            </button>
          ) : (
            <>
              {/* Loading state */}
              {isLoading && (
                <div className="space-y-2">
                  {[1, 2].map((i) => (
                    <div key={i} className="skeleton h-16 rounded-[var(--radius-lg)]" />
                  ))}
                </div>
              )}

              {/* Document list */}
              {!isLoading && (
                <div className="space-y-2">
                  {documents.map((doc) => (
                    <SourceCard
                      key={doc.source_id}
                      document={doc}
                      onToggleActive={onToggleActive}
                      onDelete={onDelete}
                    />
                  ))}
                </div>
              )}

              {/* Drop overlay */}
              {isDragging && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--color-bg-primary)]/80 backdrop-blur-sm">
                  <div className="flex flex-col items-center gap-3 p-8 bg-[var(--color-bg-elevated)] rounded-[var(--radius-xl)] border-2 border-dashed border-[var(--color-accent)] shadow-[var(--shadow-xl)]">
                    <Upload className="w-12 h-12 text-[var(--color-accent)]" />
                    <p className="text-lg font-medium text-[var(--color-text-primary)]">
                      Drop to upload
                    </p>
                  </div>
                </div>
              )}

              {/* Upload progress */}
              {isUploading && (
                <div className="flex items-center gap-2 p-3 bg-[var(--color-accent-subtle)] rounded-[var(--radius-md)]">
                  <Loader2 className="w-4 h-4 text-[var(--color-accent)] animate-spin" />
                  <span className="text-sm text-[var(--color-accent)]">
                    Uploading...
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default SourcesPanel;
