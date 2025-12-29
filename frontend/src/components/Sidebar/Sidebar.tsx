import { useState } from 'react';
import { Menu, X, Settings, Github, Zap, ChevronDown, ChevronRight } from 'lucide-react';
import { NotebookSelector } from './NotebookSelector';
import { ModelSelector } from './ModelSelector';
import { DocumentsList } from './DocumentsList';
import { WebSearchPanel } from './WebSearchPanel';
import { ThemeToggle } from '../ui';
import { useNotebook, useDocument } from '../../contexts';
import type { ModelGroup, Notebook, ModelProvider } from '../../types';

interface SidebarProps {
  // Models (not in context yet)
  models: ModelGroup[];
  selectedModel: string;
  selectedProvider: ModelProvider;
  onSelectModel: (model: string, provider: ModelProvider) => void;
  isLoadingModels?: boolean;

  // Document operations (needed for toast notifications in parent)
  onUploadDocument: (file: File) => Promise<boolean>;
  onDeleteDocument: (sourceId: string) => Promise<boolean>;
  onToggleDocument: (sourceId: string, active: boolean) => Promise<boolean>;

  // Notebook operations (needed for API calls in parent)
  onSelectNotebook: (notebook: Notebook | null) => void;
  onCreateNotebook: (name: string, description?: string) => Promise<Notebook | null>;
  onDeleteNotebook: (id: string) => Promise<boolean>;
  onUpdateNotebook: (id: string, data: Partial<Notebook>) => Promise<boolean>;

  // Web Search callback
  onWebSourcesAdded?: () => void;
}

export function Sidebar({
  models,
  selectedModel,
  selectedProvider,
  onSelectModel,
  isLoadingModels,
  onUploadDocument,
  onDeleteDocument,
  onToggleDocument,
  onSelectNotebook,
  onCreateNotebook,
  onDeleteNotebook,
  onUpdateNotebook,
  onWebSourcesAdded,
}: SidebarProps) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    notebooks: true,
    sources: true,
    webSearch: false,
  });

  // Use contexts for notebooks and documents (read-only state)
  const {
    notebooks,
    selectedNotebook,
    isLoading: isLoadingNotebooks,
  } = useNotebook();

  const {
    documents,
    isLoading: isLoadingDocs,
  } = useDocument();

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

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
        <div className="flex-1 overflow-y-auto">
          {/* Model selector - always visible */}
          <div className="p-4 border-b border-void-surface/50">
            <ModelSelector
              models={models}
              selectedModel={selectedModel}
              selectedProvider={selectedProvider}
              onSelect={onSelectModel}
              isLoading={isLoadingModels}
            />
          </div>

          {/* Notebooks Section */}
          <div className="border-b border-void-surface/50">
            <button
              onClick={() => toggleSection('notebooks')}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-void-surface/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                  Notebooks
                </span>
                {notebooks.length > 0 && (
                  <span className="px-1.5 py-0.5 rounded-full bg-glow/10 text-glow text-[10px] font-medium">
                    {notebooks.length}
                  </span>
                )}
              </div>
              {expandedSections.notebooks ? (
                <ChevronDown className="w-4 h-4 text-text-dim" />
              ) : (
                <ChevronRight className="w-4 h-4 text-text-dim" />
              )}
            </button>
            {expandedSections.notebooks && (
              <div className="px-4 pb-4">
                <NotebookSelector
                  notebooks={notebooks}
                  selectedNotebook={selectedNotebook}
                  onSelect={onSelectNotebook}
                  onCreate={onCreateNotebook}
                  onDelete={onDeleteNotebook}
                  onUpdate={onUpdateNotebook}
                  isLoading={isLoadingNotebooks}
                />
              </div>
            )}
          </div>

          {/* Sources Section */}
          <div className="border-b border-void-surface/50">
            <button
              onClick={() => toggleSection('sources')}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-void-surface/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                  Sources
                </span>
                {documents.length > 0 && (
                  <span className="px-1.5 py-0.5 rounded-full bg-nebula/10 text-nebula text-[10px] font-medium">
                    {documents.filter(d => d.active !== false).length}/{documents.length}
                  </span>
                )}
              </div>
              {expandedSections.sources ? (
                <ChevronDown className="w-4 h-4 text-text-dim" />
              ) : (
                <ChevronRight className="w-4 h-4 text-text-dim" />
              )}
            </button>
            {expandedSections.sources && (
              <div className="px-4 pb-4">
                <DocumentsList
                  documents={documents}
                  onUpload={onUploadDocument}
                  onDelete={onDeleteDocument}
                  onToggleActive={onToggleDocument}
                  isLoading={isLoadingDocs}
                  notebookSelected={!!selectedNotebook}
                />
              </div>
            )}
          </div>

          {/* Web Search Section */}
          <div className="border-b border-void-surface/50">
            <button
              onClick={() => toggleSection('webSearch')}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-void-surface/50 transition-colors"
            >
              <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                Web Search
              </span>
              {expandedSections.webSearch ? (
                <ChevronDown className="w-4 h-4 text-text-dim" />
              ) : (
                <ChevronRight className="w-4 h-4 text-text-dim" />
              )}
            </button>
            {expandedSections.webSearch && (
              <div className="px-4 pb-4">
                <WebSearchPanel
                  notebookId={selectedNotebook?.id || null}
                  onSourcesAdded={onWebSourcesAdded}
                />
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-void-surface">
          <div className="flex items-center justify-between text-text-dim">
            <div className="flex items-center gap-2">
              <ThemeToggle />
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
            <span className="text-xs">v1.2.0</span>
          </div>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;
