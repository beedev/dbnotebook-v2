import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu, X, Settings, Github, ChevronDown, ChevronRight, FileText, ExternalLink } from 'lucide-react';
import { NotebookSelector } from './NotebookSelector';
import { ThemeToggle } from '../ui';
import { useNotebook, useDocument } from '../../contexts';
import type { Notebook } from '../../types';

interface SidebarProps {
  // Notebook operations (needed for API calls in parent)
  onSelectNotebook: (notebook: Notebook | null) => void;
  onDeleteNotebook: (id: string) => Promise<boolean>;
  onUpdateNotebook: (id: string, data: Partial<Notebook>) => Promise<boolean>;
}

export function Sidebar({
  onSelectNotebook,
  onDeleteNotebook,
  onUpdateNotebook,
}: SidebarProps) {
  const navigate = useNavigate();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    notebooks: true,
    sources: true,
  });

  // Use contexts for notebooks and documents (read-only state)
  const {
    notebooks,
    selectedNotebook,
    isLoading: isLoadingNotebooks,
  } = useNotebook();

  const { documents } = useDocument();

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
        {/* Mobile close button (header) */}
        <div className="lg:hidden flex items-center justify-end p-2 border-b border-void-surface">
          <button
            onClick={() => setIsMobileOpen(false)}
            className="p-2 rounded-lg hover:bg-void-surface text-text-muted hover:text-text transition-colors"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
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
                {!selectedNotebook ? (
                  <p className="text-sm text-text-dim">
                    Select a notebook to view sources
                  </p>
                ) : documents.length === 0 ? (
                  <div className="space-y-3">
                    <p className="text-sm text-text-dim">No documents yet</p>
                    <button
                      onClick={() => navigate('/documents')}
                      className="flex items-center gap-2 text-sm text-glow hover:underline"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Add Documents
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {/* Read-only document list */}
                    <div className="space-y-1 max-h-[300px] overflow-y-auto">
                      {documents.slice(0, 10).map((doc) => (
                        <div
                          key={doc.source_id}
                          className={`flex items-center gap-2 px-2 py-1.5 rounded-md ${
                            doc.active !== false ? 'bg-void-surface' : 'bg-void-light opacity-50'
                          }`}
                        >
                          <FileText className="w-4 h-4 text-text-muted flex-shrink-0" />
                          <span className="text-sm text-text truncate" title={doc.filename}>
                            {doc.filename}
                          </span>
                        </div>
                      ))}
                      {documents.length > 10 && (
                        <p className="text-xs text-text-dim px-2">
                          +{documents.length - 10} more documents
                        </p>
                      )}
                    </div>
                    {/* Manage link */}
                    <button
                      onClick={() => navigate('/documents')}
                      className="flex items-center gap-2 text-sm text-glow hover:underline"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Manage Documents
                    </button>
                  </div>
                )}
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
