import { memo, useState } from 'react';
import { Book, MoreHorizontal, Trash2, Edit2, Check, X } from 'lucide-react';
import type { Notebook } from '../../../types';

interface NotebookCardProps {
  notebook: Notebook;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: (id: string) => Promise<boolean>;
  onUpdate: (id: string, data: Partial<Notebook>) => Promise<boolean>;
}

export const NotebookCard = memo(function NotebookCard({
  notebook,
  isSelected,
  onSelect,
  onDelete,
  onUpdate,
}: NotebookCardProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(notebook.name);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleSaveEdit = async () => {
    if (editName.trim() && editName !== notebook.name) {
      await onUpdate(notebook.id, { name: editName.trim() });
    }
    setIsEditing(false);
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    await onDelete(notebook.id);
    setIsDeleting(false);
    setShowMenu(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      setEditName(notebook.name);
      setIsEditing(false);
    }
  };

  return (
    <div
      className={`
        group relative flex items-center gap-3 px-3 py-2.5
        rounded-[var(--radius-lg)]
        cursor-pointer
        transition-all duration-[var(--transition-fast)]
        ${isSelected
          ? 'bg-[var(--color-accent-subtle)] border border-[var(--color-accent)]'
          : 'hover:bg-[var(--color-sidebar-hover)] border border-transparent'
        }
      `}
      onClick={() => !isEditing && onSelect()}
    >
      {/* Icon */}
      <div
        className={`
          flex-shrink-0 w-8 h-8 rounded-[var(--radius-md)]
          flex items-center justify-center
          ${isSelected
            ? 'bg-[var(--color-accent)] text-white'
            : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'
          }
          transition-colors
        `}
      >
        <Book className="w-4 h-4" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {isEditing ? (
          <div className="flex items-center gap-1">
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
              className="
                flex-1 px-2 py-1 text-sm
                bg-[var(--color-bg-primary)]
                border border-[var(--color-border)]
                rounded-[var(--radius-sm)]
                text-[var(--color-text-primary)]
                focus:outline-none focus:border-[var(--color-accent)]
              "
              onClick={(e) => e.stopPropagation()}
            />
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleSaveEdit();
              }}
              className="p-1 text-[var(--color-success)] hover:bg-[var(--color-success-subtle)] rounded"
            >
              <Check className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setEditName(notebook.name);
                setIsEditing(false);
              }}
              className="p-1 text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <>
            <h4
              className={`
                text-sm font-medium truncate
                ${isSelected
                  ? 'text-[var(--color-accent)]'
                  : 'text-[var(--color-text-primary)]'
                }
              `}
            >
              {notebook.name}
            </h4>
            {notebook.documentCount !== undefined && (
              <p className="text-xs text-[var(--color-text-muted)]">
                {notebook.documentCount} {notebook.documentCount === 1 ? 'source' : 'sources'}
              </p>
            )}
          </>
        )}
      </div>

      {/* Actions */}
      {!isEditing && (
        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            className={`
              p-1.5 rounded-[var(--radius-md)]
              text-[var(--color-text-muted)]
              hover:text-[var(--color-text-primary)]
              hover:bg-[var(--color-bg-hover)]
              transition-all
              ${showMenu ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}
            `}
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(false);
                }}
              />
              <div
                className="
                  absolute right-0 top-full mt-1 z-20
                  w-36 py-1
                  bg-[var(--color-bg-elevated)]
                  border border-[var(--color-border)]
                  rounded-[var(--radius-md)]
                  shadow-[var(--shadow-lg)]
                "
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  onClick={() => {
                    setIsEditing(true);
                    setShowMenu(false);
                  }}
                  className="
                    w-full flex items-center gap-2 px-3 py-2
                    text-sm text-[var(--color-text-secondary)]
                    hover:bg-[var(--color-bg-hover)]
                    transition-colors
                  "
                >
                  <Edit2 className="w-4 h-4" />
                  Rename
                </button>
                <button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="
                    w-full flex items-center gap-2 px-3 py-2
                    text-sm text-[var(--color-error)]
                    hover:bg-[var(--color-error-subtle)]
                    transition-colors
                    disabled:opacity-50
                  "
                >
                  <Trash2 className="w-4 h-4" />
                  {isDeleting ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
});

export default NotebookCard;
