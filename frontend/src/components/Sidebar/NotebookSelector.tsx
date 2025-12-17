import { useState } from 'react';
import { Book, Plus, Trash2, Edit2, Check, X } from 'lucide-react';
import type { Notebook } from '../../types';

interface NotebookSelectorProps {
  notebooks: Notebook[];
  selectedNotebook: Notebook | null;
  onSelect: (notebook: Notebook | null) => void;
  onCreate: (name: string, description?: string) => Promise<Notebook | null>;
  onDelete: (id: string) => Promise<boolean>;
  onUpdate: (id: string, data: Partial<Notebook>) => Promise<boolean>;
  isLoading?: boolean;
}

export function NotebookSelector({
  notebooks,
  selectedNotebook,
  onSelect,
  onCreate,
  onDelete,
  onUpdate,
  isLoading,
}: NotebookSelectorProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  const handleCreate = async () => {
    if (!newName.trim()) return;

    const notebook = await onCreate(newName.trim());
    if (notebook) {
      setNewName('');
      setIsCreating(false);
      onSelect(notebook);
    }
  };

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
      <div className="flex items-center justify-between px-1">
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider font-[family-name:var(--font-display)]">
          Notebooks
        </h3>
        <button
          onClick={() => setIsCreating(true)}
          className="p-1 rounded hover:bg-void-surface text-text-dim hover:text-glow transition-colors"
          title="Create notebook"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* General chat option */}
      <button
        onClick={() => onSelect(null)}
        className={`
          w-full flex items-center gap-3 px-3 py-2 rounded-lg
          transition-all duration-200
          ${
            !selectedNotebook
              ? 'bg-glow/10 border border-glow/30 text-glow'
              : 'hover:bg-void-surface text-text-muted hover:text-text'
          }
        `}
      >
        <Book className="w-4 h-4" />
        <span className="text-sm truncate">General Chat</span>
      </button>

      {/* Create new notebook form */}
      {isCreating && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-void-surface">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreate();
              if (e.key === 'Escape') {
                setIsCreating(false);
                setNewName('');
              }
            }}
            placeholder="Notebook name"
            autoFocus
            className="flex-1 bg-transparent text-sm text-text placeholder:text-text-dim focus:outline-none"
          />
          <button
            onClick={handleCreate}
            disabled={!newName.trim()}
            className="p-1 rounded text-success hover:bg-success/10 disabled:opacity-50"
          >
            <Check className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setIsCreating(false);
              setNewName('');
            }}
            className="p-1 rounded text-text-dim hover:bg-void-lighter"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Notebook list */}
      <div className="space-y-1 max-h-[200px] overflow-y-auto">
        {notebooks.map((notebook) => (
          <div
            key={notebook.id}
            onClick={() => onSelect(notebook)}
            className={`
              group flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer
              transition-all duration-200
              ${
                selectedNotebook?.id === notebook.id
                  ? 'bg-nebula/10 border border-nebula/30 text-nebula-bright'
                  : 'hover:bg-void-surface text-text-muted hover:text-text'
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
                <Book className="w-4 h-4 flex-shrink-0" />
                <span className="flex-1 text-sm truncate">{notebook.name}</span>
                <span className="text-xs text-text-dim">
                  {notebook.documentCount}
                </span>
                <div className="hidden group-hover:flex items-center gap-1">
                  <button
                    onClick={(e) => startEditing(notebook, e)}
                    className="p-1 rounded text-text-dim hover:text-text hover:bg-void-lighter"
                  >
                    <Edit2 className="w-3 h-3" />
                  </button>
                  <button
                    onClick={(e) => handleDelete(notebook.id, e)}
                    className="p-1 rounded text-text-dim hover:text-danger hover:bg-danger/10"
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
