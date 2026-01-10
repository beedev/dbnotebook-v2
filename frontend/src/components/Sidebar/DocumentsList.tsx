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
  ChevronDown,
  ChevronUp,
  Sparkles,
  Loader2,
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
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set());
  const fileInputRef = useRef<HTMLInputElement>(null);

  const toggleExpanded = (sourceId: string) => {
    setExpandedDocs(prev => {
      const next = new Set(prev);
      if (next.has(sourceId)) {
        next.delete(sourceId);
      } else {
        next.add(sourceId);
      }
      return next;
    });
  };

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

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      for (const file of files) {
        await handleUpload(file);
      }
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      for (const file of files) {
        await handleUpload(file);
      }
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
          multiple
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
        <div className="space-y-1 max-h-[400px] overflow-y-auto">
          {documents.map((doc) => {
            const hasSummary = doc.dense_summary && doc.transformation_status === 'completed';
            const isProcessing = doc.transformation_status === 'processing';
            const isExpanded = expandedDocs.has(doc.source_id);

            return (
              <div
                key={doc.source_id}
                className={`
                  group rounded-lg transition-all duration-200
                  ${doc.active !== false ? 'bg-void-surface' : 'bg-void-light opacity-60'}
                `}
              >
                {/* Main row */}
                <div className="flex items-center gap-2 px-3 py-2">
                  {/* File icon */}
                  {getFileIcon(doc.file_type)}

                  {/* File name and status */}
                  <div className="flex-1 min-w-0">
                    <span
                      className={`text-sm text-text block ${isExpanded ? '' : 'truncate'}`}
                      title={doc.filename}
                    >
                      {doc.filename}
                    </span>
                    {/* Status indicators */}
                    <div className="flex items-center gap-2 mt-0.5">
                      {doc.chunk_count !== undefined && (
                        <span className="text-xs text-text-dim">
                          {doc.chunk_count} chunks
                        </span>
                      )}
                      {isProcessing && (
                        <span className="flex items-center gap-1 text-xs text-yellow-400">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Analyzing
                        </span>
                      )}
                      {hasSummary && (
                        <span className="flex items-center gap-1 text-xs text-green-400">
                          <Sparkles className="w-3 h-3" />
                          Summary
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1">
                    {/* Expand button - only if has summary */}
                    {hasSummary && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleExpanded(doc.source_id);
                        }}
                        className="p-1.5 rounded-md text-text-dim hover:text-glow hover:bg-glow/10 transition-all duration-200"
                        title={isExpanded ? 'Hide summary' : 'Show summary'}
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleActive(doc.source_id, doc.active === false);
                      }}
                      className={`
                        p-1.5 rounded-md transition-all duration-200
                        ${doc.active !== false
                          ? 'text-glow hover:bg-glow/10'
                          : 'text-text-dim opacity-50 hover:opacity-100 hover:bg-void-lighter'}
                      `}
                      title={doc.active !== false ? 'Disable from RAG (click to deactivate)' : 'Enable for RAG (click to activate)'}
                    >
                      {doc.active !== false ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(doc.source_id);
                      }}
                      className="p-1.5 rounded-md text-text-dim opacity-0 group-hover:opacity-100 hover:text-danger hover:bg-danger/10 transition-all duration-200"
                      title="Remove document"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Expanded summary section */}
                {isExpanded && hasSummary && (
                  <div className="px-3 pb-3 pt-1 border-t border-void-lighter mt-1">
                    <div className="space-y-2">
                      {/* Summary */}
                      <div>
                        <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1">
                          Summary
                        </h5>
                        <p className="text-xs text-text-muted leading-relaxed whitespace-pre-wrap">
                          {doc.dense_summary}
                        </p>
                      </div>

                      {/* Key Insights */}
                      {doc.key_insights && doc.key_insights.length > 0 && (
                        <div>
                          <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1">
                            Key Insights
                          </h5>
                          <ul className="space-y-1">
                            {doc.key_insights.slice(0, 5).map((insight, index) => (
                              <li
                                key={index}
                                className="text-xs text-text-muted flex items-start gap-1.5"
                              >
                                <span className="text-glow mt-0.5">•</span>
                                <span>{insight}</span>
                              </li>
                            ))}
                            {doc.key_insights.length > 5 && (
                              <li className="text-xs text-text-dim italic">
                                +{doc.key_insights.length - 5} more insights
                              </li>
                            )}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
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
