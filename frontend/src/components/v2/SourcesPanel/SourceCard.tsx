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

  const FileIcon = getFileIcon(document.filename);
  const fileType = getFileType(document.filename);
  const isActive = document.active !== false;

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
        group relative flex items-start gap-3 p-3
        bg-[var(--color-bg-elevated)] rounded-[var(--radius-lg)]
        border border-[var(--color-border-subtle)]
        transition-all duration-[var(--transition-normal)]
        hover:border-[var(--color-border)]
        hover:shadow-[var(--shadow-sm)]
        ${!isActive ? 'opacity-60' : ''}
      `}
    >
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
          <div className="min-w-0">
            <h4
              className={`
                text-sm font-medium truncate
                ${isActive ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-tertiary)]'}
              `}
              title={document.filename}
            >
              {document.filename}
            </h4>
            <div className="flex items-center gap-2 mt-1">
              <span className="badge badge-muted text-xs">
                {fileType}
              </span>
              {document.chunk_count && (
                <span className="text-xs text-[var(--color-text-muted)]">
                  {document.chunk_count} chunks
                </span>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
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

      {/* Active indicator */}
      {isActive && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-8 bg-[var(--color-accent)] rounded-r-full" />
      )}
    </div>
  );
});

export default SourceCard;
