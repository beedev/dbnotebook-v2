import { memo, useState } from 'react';
import {
  FileText,
  Image,
  Globe,
  Trash2,
  Eye,
  EyeOff,
  MoreHorizontal,
  FileType,
  Presentation,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Loader2,
} from 'lucide-react';
import type { Document } from '../../../types';

interface SourceCardProps {
  document: Document;
  onToggleActive: (sourceId: string, active: boolean) => Promise<boolean>;
  onDelete: (sourceId: string) => Promise<boolean>;
}

const getFileIcon = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';

  if (['pdf'].includes(ext)) return FileText;
  if (['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext)) return Image;
  if (['pptx', 'ppt'].includes(ext)) return Presentation;
  if (['docx', 'doc'].includes(ext)) return FileType;
  if (filename.startsWith('http')) return Globe;

  return FileText;
};

const getFileType = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';

  if (['pdf'].includes(ext)) return 'PDF';
  if (['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext)) return 'Image';
  if (['pptx', 'ppt'].includes(ext)) return 'Slides';
  if (['docx', 'doc'].includes(ext)) return 'Document';
  if (['epub'].includes(ext)) return 'eBook';
  if (['txt', 'md'].includes(ext)) return 'Text';
  if (filename.startsWith('http')) return 'Web';

  return 'File';
};

export const SourceCard = memo(function SourceCard({
  document,
  onToggleActive,
  onDelete,
}: SourceCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isToggling, setIsToggling] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const FileIcon = getFileIcon(document.filename);
  const fileType = getFileType(document.filename);
  const isActive = document.active !== false;
  const hasSummary = document.dense_summary && document.transformation_status === 'completed';
  const isProcessing = document.transformation_status === 'processing';

  const handleToggle = async () => {
    if (isToggling) return;
    setIsToggling(true);
    await onToggleActive(document.source_id, !isActive);
    setIsToggling(false);
  };

  const handleDelete = async () => {
    if (isDeleting) return;
    setIsDeleting(true);
    await onDelete(document.source_id);
    setIsDeleting(false);
    setShowMenu(false);
  };

  return (
    <div
      className={`
        group relative flex flex-col
        bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)]
        border border-[var(--color-border-subtle)]
        transition-all duration-[var(--transition-normal)]
        hover:border-[var(--color-border)]
        hover:shadow-[var(--shadow-sm)]
        ${!isActive ? 'opacity-60' : ''}
      `}
    >
      {/* Main card content */}
      <div className="flex items-start gap-3 p-3">
        {/* File Icon */}
        <div
          className={`
            flex-shrink-0 w-10 h-10 rounded-[var(--radius-md)]
            flex items-center justify-center
            ${isActive
              ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)]'
              : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]'
            }
            transition-colors duration-[var(--transition-fast)]
          `}
        >
          <FileIcon className="w-5 h-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h4
                className={`
                  text-sm font-medium
                  ${isExpanded ? 'whitespace-normal break-words' : 'truncate'}
                  ${isActive ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-tertiary)]'}
                `}
                title={document.filename}
              >
                {document.filename}
              </h4>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span className="badge badge-muted text-xs">
                  {fileType}
                </span>
                {document.chunk_count && (
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {document.chunk_count} chunks
                  </span>
                )}
                {/* Transformation status indicator */}
                {isProcessing && (
                  <span className="flex items-center gap-1 text-xs text-[var(--color-warning)]">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Analyzing...
                  </span>
                )}
                {hasSummary && (
                  <span className="flex items-center gap-1 text-xs text-[var(--color-success)]">
                    <Sparkles className="w-3 h-3" />
                    Summary
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              {/* Expand/Collapse - only show if has summary */}
              {hasSummary && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="p-1.5 rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] transition-colors"
                  title={isExpanded ? 'Collapse' : 'Show summary'}
                >
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>
              )}

              {/* Toggle active */}
              <button
                onClick={handleToggle}
                disabled={isToggling}
                className={`
                  p-1.5 rounded-[var(--radius-md)]
                  transition-colors duration-[var(--transition-fast)]
                  ${isActive
                    ? 'text-[var(--color-accent)] hover:bg-[var(--color-accent-subtle)]'
                    : 'text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)]'
                  }
                  disabled:opacity-50
                `}
                title={isActive ? 'Exclude from search' : 'Include in search'}
              >
                {isActive ? (
                  <Eye className="w-4 h-4" />
                ) : (
                  <EyeOff className="w-4 h-4" />
                )}
              </button>

              {/* Menu */}
              <div className="relative">
                <button
                  onClick={() => setShowMenu(!showMenu)}
                  className="p-1.5 rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] transition-colors"
                >
                  <MoreHorizontal className="w-4 h-4" />
                </button>

                {showMenu && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setShowMenu(false)}
                    />
                    <div
                      className="absolute right-0 top-full mt-1 z-20 w-36 py-1 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-[var(--radius-md)] shadow-[var(--shadow-lg)]"
                    >
                      <button
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--color-error)] hover:bg-[var(--color-error-subtle)] transition-colors disabled:opacity-50"
                      >
                        <Trash2 className="w-4 h-4" />
                        {isDeleting ? 'Removing...' : 'Remove'}
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* File type badge */}
          {document.file_type && (
            <p className="mt-1.5 text-xs text-[var(--color-text-tertiary)] truncate uppercase">
              {document.file_type}
            </p>
          )}
        </div>
      </div>

      {/* Expanded Summary Section */}
      {isExpanded && hasSummary && (
        <div className="px-3 pb-3 pt-0 border-t border-[var(--color-border-subtle)] mt-2">
          <div className="mt-3 space-y-3">
            {/* Summary */}
            <div>
              <h5 className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide mb-1.5">
                Summary
              </h5>
              <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
                {document.dense_summary}
              </p>
            </div>

            {/* Key Insights */}
            {document.key_insights && document.key_insights.length > 0 && (
              <div>
                <h5 className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wide mb-1.5">
                  Key Insights
                </h5>
                <ul className="space-y-1">
                  {document.key_insights.map((insight, index) => (
                    <li
                      key={index}
                      className="text-sm text-[var(--color-text-primary)] flex items-start gap-2"
                    >
                      <span className="text-[var(--color-accent)] mt-1">•</span>
                      <span>{insight}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Active indicator */}
      {isActive && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-8 bg-[var(--color-accent)] rounded-r-full" />
      )}
    </div>
  );
});

export default SourceCard;
