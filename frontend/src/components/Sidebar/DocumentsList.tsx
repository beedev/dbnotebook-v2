import { useState, useRef } from 'react';
import {
  FileText,
  Upload,
  Trash2,
  Eye,
  EyeOff,
  File,
  Image,
  FileSpreadsheet,
  Presentation,
} from 'lucide-react';
import type { Document } from '../../types';

interface DocumentsListProps {
  documents: Document[];
  onUpload: (file: File) => Promise<boolean>;
  onDelete: (sourceId: string) => Promise<boolean>;
  onToggleActive: (sourceId: string, active: boolean) => Promise<boolean>;
  isLoading?: boolean;
  notebookSelected: boolean;
}

const fileIcons: Record<string, React.ReactNode> = {
  pdf: <FileText className="w-4 h-4 text-red-400" />,
  txt: <File className="w-4 h-4 text-text-muted" />,
  md: <FileText className="w-4 h-4 text-cyan-400" />,
  docx: <FileText className="w-4 h-4 text-blue-400" />,
  doc: <FileText className="w-4 h-4 text-blue-400" />,
  epub: <FileText className="w-4 h-4 text-purple-400" />,
  pptx: <Presentation className="w-4 h-4 text-orange-400" />,
  ppt: <Presentation className="w-4 h-4 text-orange-400" />,
  xlsx: <FileSpreadsheet className="w-4 h-4 text-green-400" />,
  xls: <FileSpreadsheet className="w-4 h-4 text-green-400" />,
  csv: <FileSpreadsheet className="w-4 h-4 text-green-400" />,
  png: <Image className="w-4 h-4 text-pink-400" />,
  jpg: <Image className="w-4 h-4 text-pink-400" />,
  jpeg: <Image className="w-4 h-4 text-pink-400" />,
  webp: <Image className="w-4 h-4 text-pink-400" />,
};

function getFileIcon(fileType?: string) {
  if (!fileType) return <File className="w-4 h-4 text-text-muted" />;
  return fileIcons[fileType.toLowerCase()] || <File className="w-4 h-4 text-text-muted" />;
}

export function DocumentsList({
  documents,
  onUpload,
  onDelete,
  onToggleActive,
  isLoading,
  notebookSelected,
}: DocumentsListProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      await handleUpload(file);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await handleUpload(file);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      await onUpload(file);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (sourceId: string) => {
    if (window.confirm('Remove this document from the notebook?')) {
      await onDelete(sourceId);
    }
  };

  if (!notebookSelected) {
    return (
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider font-[family-name:var(--font-display)] px-1">
          Documents
        </h3>
        <p className="text-sm text-text-dim px-1">
          Select a notebook to manage documents
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider font-[family-name:var(--font-display)] px-1">
        Documents ({documents.length})
      </h3>

      {/* Upload area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          relative p-4 rounded-lg border-2 border-dashed
          cursor-pointer transition-all duration-200
          ${
            isDragging
              ? 'border-glow bg-glow/5'
              : 'border-void-surface hover:border-text-dim'
          }
          ${isUploading ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md,.docx,.doc,.epub,.pptx,.ppt,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.webp"
          className="hidden"
          onChange={handleFileSelect}
        />

        <div className="flex flex-col items-center gap-2 text-center">
          <div className={`p-2 rounded-lg ${isDragging ? 'bg-glow/20' : 'bg-void-surface'}`}>
            <Upload className={`w-5 h-5 ${isDragging ? 'text-glow' : 'text-text-muted'}`} />
          </div>
          <p className="text-sm text-text-muted">
            {isUploading ? 'Uploading...' : 'Drop files or click to upload'}
          </p>
          <p className="text-xs text-text-dim">
            PDF, DOCX, TXT, MD, EPUB, PPTX, XLSX, Images
          </p>
        </div>
      </div>

      {/* Document list */}
      {documents.length > 0 && (
        <div className="space-y-1 max-h-[250px] overflow-y-auto">
          {documents.map((doc) => (
            <div
              key={doc.source_id}
              className={`
                group flex items-center gap-2 px-3 py-2 rounded-lg
                transition-all duration-200
                ${doc.active !== false ? 'bg-void-surface' : 'bg-void-light opacity-60'}
              `}
            >
              {/* File icon */}
              {getFileIcon(doc.file_type)}

              {/* File name */}
              <span className="flex-1 text-sm text-text truncate" title={doc.filename}>
                {doc.filename}
              </span>

              {/* Chunk count */}
              {doc.chunk_count !== undefined && (
                <span className="text-xs text-text-dim">
                  {doc.chunk_count} chunks
                </span>
              )}

              {/* Actions */}
              <div className="hidden group-hover:flex items-center gap-1">
                <button
                  onClick={() => onToggleActive(doc.source_id, doc.active === false)}
                  className={`
                    p-1 rounded transition-colors
                    ${doc.active !== false ? 'text-text-dim hover:text-warning' : 'text-warning hover:text-text'}
                  `}
                  title={doc.active !== false ? 'Deactivate' : 'Activate'}
                >
                  {doc.active !== false ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                </button>
                <button
                  onClick={() => handleDelete(doc.source_id)}
                  className="p-1 rounded text-text-dim hover:text-danger hover:bg-danger/10 transition-colors"
                  title="Remove"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-4">
          <div className="w-5 h-5 border-2 border-glow/30 border-t-glow rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}

export default DocumentsList;
