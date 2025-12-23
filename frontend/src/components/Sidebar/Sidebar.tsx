import { useState } from 'react';
import { Menu, X, Settings, Github, Zap } from 'lucide-react';
import { NotebookSelector } from './NotebookSelector';
import { ModelSelector } from './ModelSelector';
import { DocumentsList } from './DocumentsList';
import { WebSearchPanel } from './WebSearchPanel';
import type { Notebook, ModelGroup, Document, ModelProvider } from '../../types';

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
  selectedProvider,
  onSelectModel,
  isLoadingModels,
  documents,
  onUploadDocument,
  onDeleteDocument,
  onToggleDocument,
  isLoadingDocs,
  onWebSourcesAdded,
}: SidebarProps) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile toggle button */}
      <button
        onClick={() => setIsMobileOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-40 p-2 rounded-lg bg-void-surface text-text hover:bg-void-lighter transition-colors"
        aria-label="Open sidebar"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-void/80 backdrop-blur-sm"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:relative inset-y-0 left-0 z-50
          w-72 flex flex-col
          bg-void-light border-r border-void-surface
          transition-transform duration-300 ease-out
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-void-surface">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-glow/20 flex items-center justify-center">
              <Zap className="w-5 h-5 text-glow" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-text font-[family-name:var(--font-display)]">
                <span className="gradient-text">DB</span>Notebook
              </h1>
            </div>
          </div>

          {/* Mobile close button */}
          <button
            onClick={() => setIsMobileOpen(false)}
            className="lg:hidden p-2 rounded-lg hover:bg-void-surface text-text-muted hover:text-text transition-colors"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Model selector */}
          <ModelSelector
            models={models}
            selectedModel={selectedModel}
            selectedProvider={selectedProvider}
            onSelect={onSelectModel}
            isLoading={isLoadingModels}
          />

          {/* Divider */}
          <div className="border-t border-void-surface" />

          {/* Notebook selector */}
          <NotebookSelector
            notebooks={notebooks}
            selectedNotebook={selectedNotebook}
            onSelect={onSelectNotebook}
            onCreate={onCreateNotebook}
            onDelete={onDeleteNotebook}
            onUpdate={onUpdateNotebook}
            isLoading={isLoadingNotebooks}
          />

          {/* Divider */}
          <div className="border-t border-void-surface" />

          {/* Documents list */}
          <DocumentsList
            documents={documents}
            onUpload={onUploadDocument}
            onDelete={onDeleteDocument}
            onToggleActive={onToggleDocument}
            isLoading={isLoadingDocs}
            notebookSelected={!!selectedNotebook}
          />

          {/* Divider */}
          <div className="border-t border-void-surface" />

          {/* Web Search */}
          <WebSearchPanel
            notebookId={selectedNotebook?.id || null}
            onSourcesAdded={onWebSourcesAdded}
          />
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-void-surface">
          <div className="flex items-center justify-between text-text-dim">
            <div className="flex items-center gap-2">
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-lg hover:bg-void-surface hover:text-text transition-colors"
                title="GitHub"
              >
                <Github className="w-4 h-4" />
              </a>
              <button
                className="p-2 rounded-lg hover:bg-void-surface hover:text-text transition-colors"
                title="Settings"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>
            <span className="text-xs">v1.0.0</span>
          </div>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;
