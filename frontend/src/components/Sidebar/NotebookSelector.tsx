import { useState } from 'react';
import { Trash2, Edit2, Check, X, FileText, MessageSquare } from 'lucide-react';
import type { Notebook } from '../../types';

// Generate a consistent emoji icon based on notebook name
function getNotebookEmoji(name: string): string {
  const emojis = ['📚', '📖', '📓', '📕', '📗', '📘', '📙', '🗂️', '📋', '📝'];
  const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return emojis[hash % emojis.length];
}

interface NotebookSelectorProps {
  notebooks: Notebook[];
  selectedNotebook: Notebook | null;
  onSelect: (notebook: Notebook | null) => void;
  onDelete: (id: string) => Promise<boolean>;
  onUpdate: (id: string, data: Partial<Notebook>) => Promise<boolean>;
  isLoading?: boolean;
}

export function NotebookSelector({
  notebooks,
  selectedNotebook,
  onSelect,
  onDelete,
  onUpdate,
  isLoading,
}: NotebookSelectorProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  const handleUpdate = async (id: string) => {
    if (!editName.trim()) {
      setEditingId(null);
      return;
    }

    const success = await onUpdate(id, { name: editName.trim() });
    if (success) {
      setEditingId(null);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Delete this notebook and all its documents?')) {
      await onDelete(id);
    }
  };

  const startEditing = (notebook: Notebook, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(notebook.id);
    setEditName(notebook.name);
  };

  return (
    <div className="space-y-2">
      {/* General chat option */}
      <button
        onClick={() => onSelect(null)}
        className={`
          w-full flex items-center gap-3 px-3 py-2.5 rounded-lg
          transition-all duration-200 group/general
          ${
            !selectedNotebook
              ? 'bg-glow/10 border border-glow/30 text-glow shadow-sm shadow-glow/10'
              : 'hover:bg-void-surface text-text-muted hover:text-text border border-transparent'
          }
        `}
      >
        <div className={`
          w-7 h-7 rounded-md flex items-center justify-center text-sm
          ${!selectedNotebook ? 'bg-glow/20' : 'bg-void-surface group-hover/general:bg-void-lighter'}
        `}>
          <MessageSquare className="w-4 h-4" />
        </div>
        <div className="flex-1 text-left">
          <span className="text-sm font-medium">General Chat</span>
          <p className="text-xs text-text-dim">No document context</p>
        </div>
      </button>

      {/* Notebook list */}
      <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
        {notebooks.map((notebook) => (
          <div
            key={notebook.id}
            onClick={() => onSelect(notebook)}
            className={`
              group flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer
              transition-all duration-200
              ${
                selectedNotebook?.id === notebook.id
                  ? 'bg-nebula/10 border border-nebula/30 text-nebula-bright shadow-sm shadow-nebula/10'
                  : 'hover:bg-void-surface text-text-muted hover:text-text border border-transparent'
              }
            `}
          >
            {editingId === notebook.id ? (
              <div className="flex-1 flex items-center gap-2">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleUpdate(notebook.id);
                    if (e.key === 'Escape') setEditingId(null);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  autoFocus
                  className="flex-1 bg-transparent text-sm text-text focus:outline-none"
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleUpdate(notebook.id);
                  }}
                  className="p-1 rounded text-success hover:bg-success/10"
                >
                  <Check className="w-3 h-3" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingId(null);
                  }}
                  className="p-1 rounded text-text-dim hover:bg-void-lighter"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ) : (
              <>
                {/* Emoji icon */}
                <div className={`
                  w-7 h-7 rounded-md flex items-center justify-center text-sm flex-shrink-0
                  ${selectedNotebook?.id === notebook.id ? 'bg-nebula/20' : 'bg-void-surface group-hover:bg-void-lighter'}
                `}>
                  {getNotebookEmoji(notebook.name)}
                </div>

                {/* Name and document count */}
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium truncate block">{notebook.name}</span>
                  <div className="flex items-center gap-1 text-xs text-text-dim">
                    <FileText className="w-3 h-3" />
                    <span>{notebook.documentCount} {notebook.documentCount === 1 ? 'doc' : 'docs'}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="hidden group-hover:flex items-center gap-1">
                  <button
                    onClick={(e) => startEditing(notebook, e)}
                    className="p-1.5 rounded-md text-text-dim hover:text-text hover:bg-void-lighter transition-colors"
                    title="Rename notebook"
                  >
                    <Edit2 className="w-3 h-3" />
                  </button>
                  <button
                    onClick={(e) => handleDelete(notebook.id, e)}
                    className="p-1.5 rounded-md text-text-dim hover:text-danger hover:bg-danger/10 transition-colors"
                    title="Delete notebook"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-4">
          <div className="w-5 h-5 border-2 border-glow/30 border-t-glow rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}

export default NotebookSelector;
