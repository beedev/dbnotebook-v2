import { useState } from 'react';
import {
  Menu,
  X,
  Settings,
  Github,
  Plus,
  ChevronDown,
  ChevronRight,
  Cpu,
  Loader2,
} from 'lucide-react';
import { NotebookCard } from './NotebookCard';
import { SourcesPanel } from '../SourcesPanel';
import type { Notebook, ModelGroup, Document, ModelProvider } from '../../../types';

interface SidebarProps {
  // Notebooks
  notebooks: Notebook[];
  selectedNotebook: Notebook | null;
  onSelectNotebook: (notebook: Notebook | null) => void;
  onCreateNotebook: (name: string, description?: string) => Promise<Notebook | null>;
  onDeleteNotebook: (id: string) => Promise<boolean>;
  onUpdateNotebook: (id: string, data: Partial<Notebook>) => Promise<boolean>;
  isLoadingNotebooks?: boolean;

  // Models
  models: ModelGroup[];
  selectedModel: string;
  selectedProvider: ModelProvider;
  onSelectModel: (model: string, provider: ModelProvider) => void;
  isLoadingModels?: boolean;

  // Documents
  documents: Document[];
  onUploadDocument: (file: File) => Promise<boolean>;
  onDeleteDocument: (sourceId: string) => Promise<boolean>;
  onToggleDocument: (sourceId: string, active: boolean) => Promise<boolean>;
  isLoadingDocs?: boolean;

  // Web Search
  onWebSourcesAdded?: () => void;
}

export function Sidebar({
  notebooks,
  selectedNotebook,
  onSelectNotebook,
  onCreateNotebook,
  onDeleteNotebook,
  onUpdateNotebook,
  isLoadingNotebooks,
  models,
  selectedModel,
  selectedProvider: _selectedProvider,
  onSelectModel,
  isLoadingModels,
  documents,
  onUploadDocument,
  onDeleteDocument,
  onToggleDocument,
  isLoadingDocs,
}: SidebarProps) {
  // selectedProvider is passed for future use
  void _selectedProvider;
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isNotebooksExpanded, setIsNotebooksExpanded] = useState(true);
  const [isCreatingNotebook, setIsCreatingNotebook] = useState(false);
  const [newNotebookName, setNewNotebookName] = useState('');
  const [showModelDropdown, setShowModelDropdown] = useState(false);

  const handleCreateNotebook = async () => {
    if (!newNotebookName.trim()) return;
    await onCreateNotebook(newNotebookName.trim());
    setNewNotebookName('');
    setIsCreatingNotebook(false);
  };

  const currentModel = models
    .flatMap((g) => g.models)
    .find((m) => m.name === selectedModel);

  return (
    <>
      {/* Mobile toggle button */}
      <button
        onClick={() => setIsMobileOpen(true)}
        className="
          lg:hidden fixed top-4 left-4 z-40
          p-2 rounded-[var(--radius-md)]
          bg-[var(--color-bg-elevated)]
          border border-[var(--color-border)]
          text-[var(--color-text-primary)]
          hover:bg-[var(--color-bg-hover)]
          shadow-[var(--shadow-sm)]
          transition-colors
        "
        aria-label="Open sidebar"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:relative inset-y-0 left-0 z-50
          w-72 flex flex-col
          bg-[var(--color-sidebar-bg)]
          border-r border-[var(--color-border-subtle)]
          transition-transform duration-300 ease-out
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-[var(--color-border-subtle)]">
          <div className="flex items-center gap-2.5">
            <div
              className="
                w-8 h-8 rounded-[var(--radius-md)]
                bg-[var(--color-accent)]
                flex items-center justify-center
              "
            >
              <span className="text-white font-bold text-sm font-[family-name:var(--font-display)]">
                DB
              </span>
            </div>
            <h1 className="text-base font-semibold text-[var(--color-text-primary)] font-[family-name:var(--font-display)]">
              DBNotebook
            </h1>
          </div>

          {/* Mobile close button */}
          <button
            onClick={() => setIsMobileOpen(false)}
            className="
              lg:hidden p-2 rounded-[var(--radius-md)]
              hover:bg-[var(--color-bg-hover)]
              text-[var(--color-text-muted)]
              transition-colors
            "
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Model selector */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wide px-1">
              Model
            </label>
            <div className="relative">
              <button
                onClick={() => setShowModelDropdown(!showModelDropdown)}
                disabled={isLoadingModels}
                className="
                  w-full flex items-center justify-between gap-2 px-3 py-2.5
                  bg-[var(--color-bg-primary)]
                  border border-[var(--color-border)]
                  rounded-[var(--radius-md)]
                  text-left
                  hover:border-[var(--color-border-strong)]
                  transition-colors
                  disabled:opacity-50
                "
              >
                <div className="flex items-center gap-2 min-w-0">
                  {isLoadingModels ? (
                    <Loader2 className="w-4 h-4 text-[var(--color-text-muted)] animate-spin" />
                  ) : (
                    <Cpu className="w-4 h-4 text-[var(--color-accent)]" />
                  )}
                  <span className="text-sm text-[var(--color-text-primary)] truncate">
                    {currentModel?.name || 'Select model'}
                  </span>
                </div>
                <ChevronDown className="w-4 h-4 text-[var(--color-text-muted)] flex-shrink-0" />
              </button>

              {showModelDropdown && !isLoadingModels && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setShowModelDropdown(false)}
                  />
                  <div
                    className="
                      absolute left-0 right-0 top-full mt-1 z-20
                      max-h-64 overflow-y-auto
                      bg-[var(--color-bg-elevated)]
                      border border-[var(--color-border)]
                      rounded-[var(--radius-md)]
                      shadow-[var(--shadow-lg)]
                    "
                  >
                    {models.map((group) => (
                      <div key={group.provider}>
                        <div className="px-3 py-2 text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wide bg-[var(--color-bg-secondary)]">
                          {group.provider}
                        </div>
                        {group.models.map((model) => (
                          <button
                            key={model.name}
                            onClick={() => {
                              onSelectModel(model.name, group.provider as ModelProvider);
                              setShowModelDropdown(false);
                            }}
                            className={`
                              w-full flex items-center gap-2 px-3 py-2
                              text-sm text-left
                              hover:bg-[var(--color-bg-hover)]
                              transition-colors
                              ${selectedModel === model.name
                                ? 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)]'
                                : 'text-[var(--color-text-primary)]'
                              }
                            `}
                          >
                            <span className="truncate">{model.name}</span>
                          </button>
                        ))}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Divider */}
          <div className="divider" />

          {/* Notebooks */}
          <div className="space-y-2">
            <button
              onClick={() => setIsNotebooksExpanded(!isNotebooksExpanded)}
              className="w-full flex items-center justify-between px-1 py-1 text-left group"
            >
              <div className="flex items-center gap-2">
                {isNotebooksExpanded ? (
                  <ChevronDown className="w-4 h-4 text-[var(--color-text-muted)]" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-[var(--color-text-muted)]" />
                )}
                <span className="text-sm font-semibold text-[var(--color-text-secondary)] font-[family-name:var(--font-display)]">
                  Notebooks
                </span>
                <span className="badge text-xs">{notebooks.length}</span>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setIsCreatingNotebook(true);
                  setIsNotebooksExpanded(true);
                }}
                className="
                  p-1.5 rounded-[var(--radius-md)]
                  text-[var(--color-accent)]
                  hover:bg-[var(--color-accent-subtle)]
                  opacity-0 group-hover:opacity-100
                  transition-all
                "
                title="Create notebook"
              >
                <Plus className="w-4 h-4" />
              </button>
            </button>

            {isNotebooksExpanded && (
              <div className="space-y-1">
                {/* Create notebook input */}
                {isCreatingNotebook && (
                  <div className="flex items-center gap-2 px-3 py-2">
                    <input
                      type="text"
                      value={newNotebookName}
                      onChange={(e) => setNewNotebookName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleCreateNotebook();
                        if (e.key === 'Escape') {
                          setIsCreatingNotebook(false);
                          setNewNotebookName('');
                        }
                      }}
                      placeholder="Notebook name"
                      autoFocus
                      className="
                        flex-1 px-2 py-1.5 text-sm
                        bg-[var(--color-bg-primary)]
                        border border-[var(--color-border)]
                        rounded-[var(--radius-sm)]
                        text-[var(--color-text-primary)]
                        placeholder:text-[var(--color-text-placeholder)]
                        focus:outline-none focus:border-[var(--color-accent)]
                      "
                    />
                    <button
                      onClick={handleCreateNotebook}
                      disabled={!newNotebookName.trim()}
                      className="
                        p-1.5 rounded-[var(--radius-sm)]
                        bg-[var(--color-accent)]
                        text-white
                        hover:bg-[var(--color-accent-hover)]
                        disabled:opacity-50 disabled:cursor-not-allowed
                        transition-colors
                      "
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                )}

                {/* Loading state */}
                {isLoadingNotebooks && (
                  <div className="space-y-2 px-1">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="skeleton h-12 rounded-[var(--radius-lg)]" />
                    ))}
                  </div>
                )}

                {/* Notebook list */}
                {!isLoadingNotebooks && notebooks.length === 0 && !isCreatingNotebook && (
                  <button
                    onClick={() => setIsCreatingNotebook(true)}
                    className="
                      w-full flex flex-col items-center justify-center py-6 px-4
                      border-2 border-dashed border-[var(--color-border)]
                      rounded-[var(--radius-lg)]
                      text-center
                      hover:border-[var(--color-accent)]
                      hover:bg-[var(--color-accent-subtle)]
                      transition-colors
                    "
                  >
                    <Plus className="w-6 h-6 text-[var(--color-text-muted)] mb-2" />
                    <span className="text-sm text-[var(--color-text-secondary)]">
                      Create your first notebook
                    </span>
                  </button>
                )}

                {!isLoadingNotebooks && notebooks.map((notebook) => (
                  <NotebookCard
                    key={notebook.id}
                    notebook={notebook}
                    isSelected={selectedNotebook?.id === notebook.id}
                    onSelect={() => onSelectNotebook(notebook)}
                    onDelete={onDeleteNotebook}
                    onUpdate={onUpdateNotebook}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="divider" />

          {/* Sources */}
          <SourcesPanel
            documents={documents}
            onUpload={onUploadDocument}
            onDelete={onDeleteDocument}
            onToggleActive={onToggleDocument}
            isLoading={isLoadingDocs}
            notebookSelected={!!selectedNotebook}
          />
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-[var(--color-border-subtle)]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1">
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="
                  p-2 rounded-[var(--radius-md)]
                  text-[var(--color-text-muted)]
                  hover:text-[var(--color-text-primary)]
                  hover:bg-[var(--color-bg-hover)]
                  transition-colors
                "
                title="GitHub"
              >
                <Github className="w-4 h-4" />
              </a>
              <button
                className="
                  p-2 rounded-[var(--radius-md)]
                  text-[var(--color-text-muted)]
                  hover:text-[var(--color-text-primary)]
                  hover:bg-[var(--color-bg-hover)]
                  transition-colors
                "
                title="Settings"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>
            <span className="text-xs text-[var(--color-text-muted)]">v2.0.0</span>
          </div>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;
