/**
 * Documents Landing Page
 *
 * Two-panel layout for document and notebook management:
 * - Left panel: Notebook list with search and create
 * - Right panel: Selected notebook's documents with full CRUD
 */

import { useState, useMemo } from 'react';
import {
  Search,
  Plus,
  FolderOpen,
  FileText,
  Trash2,
  Edit2,
  Check,
  X,
  Upload,
  Loader2,
  Globe,
  ChevronRight
} from 'lucide-react';
import { Header } from '../components/Header';
import { MainLayout } from '../components/Layout';
import { useNotebook } from '../contexts';
import { useNotebooks } from '../hooks/useNotebooks';
import { useToast } from '../hooks/useToast';
import { ToastContainer } from '../components/ui';
import { WebSearchPanel } from '../components/Sidebar/WebSearchPanel';
import type { Notebook, Document } from '../types';

export function DocumentsLandingPage() {
  const { notebooks } = useNotebook();
  const {
    createNotebook,
    updateNotebook,
    deleteNotebook,
    uploadDocument,
    deleteDocument,
    toggleDocumentActive,
    selectNotebook,
    selectedNotebook,
    documents,
    isLoading,
    isLoadingDocs
  } = useNotebooks();
  const { toasts, removeToast, success, error: showError } = useToast();

  // Local state
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreatingNotebook, setIsCreatingNotebook] = useState(false);
  const [newNotebookName, setNewNotebookName] = useState('');
  const [editingNotebookId, setEditingNotebookId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [showWebSearch, setShowWebSearch] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // Filter notebooks by search
  const filteredNotebooks = useMemo(() => {
    if (!searchQuery.trim()) return notebooks;
    const query = searchQuery.toLowerCase();
    return notebooks.filter(nb =>
      nb.name.toLowerCase().includes(query)
    );
  }, [notebooks, searchQuery]);

  // Notebook CRUD handlers
  const handleCreateNotebook = async () => {
    if (!newNotebookName.trim()) return;

    const notebook = await createNotebook(newNotebookName.trim());
    if (notebook) {
      success(`Created: ${notebook.name}`);
      setNewNotebookName('');
      setIsCreatingNotebook(false);
      selectNotebook(notebook);
    } else {
      showError('Failed to create notebook');
    }
  };

  const handleRenameNotebook = async (id: string) => {
    if (!editingName.trim()) {
      setEditingNotebookId(null);
      return;
    }

    const result = await updateNotebook(id, { name: editingName.trim() });
    if (result) {
      success('Notebook renamed');
      setEditingNotebookId(null);
    } else {
      showError('Failed to rename notebook');
    }
  };

  const handleDeleteNotebook = async (notebook: Notebook) => {
    if (!window.confirm(`Delete "${notebook.name}" and all its documents?`)) return;

    const result = await deleteNotebook(notebook.id);
    if (result) {
      success('Notebook deleted');
      if (selectedNotebook?.id === notebook.id) {
        selectNotebook(null);
      }
    } else {
      showError('Failed to delete notebook');
    }
  };

  // Document handlers
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    let successCount = 0;

    for (const file of Array.from(files)) {
      const result = await uploadDocument(file);
      if (result) successCount++;
    }

    if (successCount > 0) {
      success(`Uploaded ${successCount} file${successCount > 1 ? 's' : ''}`);
    }
    if (successCount < files.length) {
      showError(`Failed to upload ${files.length - successCount} file(s)`);
    }

    setIsUploading(false);
    e.target.value = '';
  };

  const handleDeleteDocument = async (doc: Document) => {
    if (!window.confirm(`Remove "${doc.filename}"?`)) return;

    const result = await deleteDocument(doc.source_id);
    if (result) {
      success('Document removed');
    } else {
      showError('Failed to remove document');
    }
  };

  const handleToggleDocument = async (doc: Document) => {
    const result = await toggleDocumentActive(doc.source_id, !(doc.active !== false));
    if (!result) {
      showError('Failed to update document');
    }
  };

  const handleWebSourcesAdded = () => {
    if (selectedNotebook) {
      selectNotebook(selectedNotebook);
    }
    success('Web content added');
    setShowWebSearch(false);
  };

  const startEditing = (notebook: Notebook) => {
    setEditingNotebookId(notebook.id);
    setEditingName(notebook.name);
  };

  return (
    <MainLayout header={<Header />}>
      <div className="flex h-[calc(100vh-3.5rem)]">
        {/* Left Panel - Notebook List */}
        <div className="w-80 border-r border-void-lighter flex flex-col bg-void-light shrink-0">
          {/* Search & Create Header */}
          <div className="p-4 border-b border-void-lighter space-y-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search notebooks..."
                className="w-full pl-10 pr-4 py-2 bg-void-surface border border-void-lighter rounded-lg text-sm text-text placeholder-text-dim focus:outline-none focus:border-glow"
              />
            </div>

            {/* Create Button */}
            {!isCreatingNotebook ? (
              <button
                onClick={() => setIsCreatingNotebook(true)}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-glow/10 text-glow rounded-lg hover:bg-glow/20 transition-colors text-sm font-medium"
              >
                <Plus className="w-4 h-4" />
                New Notebook
              </button>
            ) : (
              <div className="flex items-center gap-2">
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
                  placeholder="Notebook name..."
                  autoFocus
                  className="flex-1 px-3 py-2 bg-void-surface border border-void-lighter rounded-lg text-sm text-text placeholder-text-dim focus:outline-none focus:border-glow"
                />
                <button
                  onClick={handleCreateNotebook}
                  disabled={!newNotebookName.trim()}
                  className="p-2 text-glow hover:bg-glow/10 rounded-lg disabled:opacity-50"
                >
                  <Check className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    setIsCreatingNotebook(false);
                    setNewNotebookName('');
                  }}
                  className="p-2 text-text-dim hover:text-text rounded-lg"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {/* Notebook List */}
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-glow" />
              </div>
            ) : filteredNotebooks.length === 0 ? (
              <div className="p-4 text-center text-text-dim text-sm">
                {searchQuery ? 'No notebooks match your search' : 'No notebooks yet'}
              </div>
            ) : (
              <div className="p-2 space-y-1">
                {filteredNotebooks.map((notebook) => (
                  <div
                    key={notebook.id}
                    className={`
                      group flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer
                      transition-all duration-150
                      ${selectedNotebook?.id === notebook.id
                        ? 'bg-glow/10 border border-glow/30'
                        : 'hover:bg-void-surface border border-transparent'
                      }
                    `}
                    onClick={() => selectNotebook(notebook)}
                  >
                    {editingNotebookId === notebook.id ? (
                      // Editing mode
                      <div className="flex-1 flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="text"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleRenameNotebook(notebook.id);
                            if (e.key === 'Escape') setEditingNotebookId(null);
                          }}
                          autoFocus
                          className="flex-1 px-2 py-1 bg-void-surface border border-void-lighter rounded text-sm text-text focus:outline-none focus:border-glow"
                        />
                        <button
                          onClick={() => handleRenameNotebook(notebook.id)}
                          className="p-1 text-glow hover:bg-glow/10 rounded"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => setEditingNotebookId(null)}
                          className="p-1 text-text-dim hover:text-text rounded"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      // Display mode
                      <>
                        <div className={`
                          w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
                          ${selectedNotebook?.id === notebook.id ? 'bg-glow/20' : 'bg-void-surface'}
                        `}>
                          <FolderOpen className={`w-4 h-4 ${selectedNotebook?.id === notebook.id ? 'text-glow' : 'text-text-muted'}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className={`text-sm font-medium truncate ${selectedNotebook?.id === notebook.id ? 'text-glow' : 'text-text'}`}>
                            {notebook.name}
                          </div>
                          <div className="text-xs text-text-dim">
                            {notebook.documentCount || 0} doc{notebook.documentCount !== 1 ? 's' : ''}
                          </div>
                        </div>
                        {/* Actions - show on hover */}
                        <div className="hidden group-hover:flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => startEditing(notebook)}
                            className="p-1.5 text-text-dim hover:text-text hover:bg-void-lighter rounded"
                            title="Rename"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteNotebook(notebook)}
                            className="p-1.5 text-text-dim hover:text-danger hover:bg-danger/10 rounded"
                            title="Delete"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        {/* Chevron when not hovering */}
                        <ChevronRight className={`w-4 h-4 group-hover:hidden ${selectedNotebook?.id === notebook.id ? 'text-glow' : 'text-text-dim'}`} />
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Notebook count footer */}
          <div className="p-3 border-t border-void-lighter text-xs text-text-dim text-center">
            {notebooks.length} notebook{notebooks.length !== 1 ? 's' : ''}
          </div>
        </div>

        {/* Right Panel - Document Management */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {!selectedNotebook ? (
            // No notebook selected
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <FolderOpen className="w-16 h-16 text-text-dim mx-auto mb-4" />
                <h2 className="text-xl font-medium text-text mb-2">Select a Notebook</h2>
                <p className="text-text-muted mb-6">
                  Choose a notebook from the left to manage its documents
                </p>
                {notebooks.length === 0 && (
                  <button
                    onClick={() => setIsCreatingNotebook(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-glow/10 text-glow rounded-lg hover:bg-glow/20 transition-colors"
                  >
                    <Plus className="w-5 h-5" />
                    Create Your First Notebook
                  </button>
                )}
              </div>
            </div>
          ) : (
            // Notebook selected - show documents
            <>
              {/* Document Header */}
              <div className="p-6 border-b border-void-lighter">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-text">{selectedNotebook.name}</h2>
                    <p className="text-sm text-text-muted mt-1">
                      {documents.length} document{documents.length !== 1 ? 's' : ''} in this notebook
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {/* Web Search Button */}
                    <button
                      onClick={() => setShowWebSearch(!showWebSearch)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                        showWebSearch
                          ? 'bg-purple-500/20 text-purple-400'
                          : 'bg-void-surface text-text-muted hover:text-text'
                      }`}
                    >
                      <Globe className="w-4 h-4" />
                      Add from Web
                    </button>

                    {/* Upload Button */}
                    <label className="flex items-center gap-2 px-4 py-2 bg-glow text-void rounded-lg hover:bg-glow/90 transition-colors cursor-pointer">
                      {isUploading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Upload className="w-4 h-4" />
                      )}
                      Upload Files
                      <input
                        type="file"
                        multiple
                        onChange={handleFileUpload}
                        className="hidden"
                        accept=".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls"
                      />
                    </label>
                  </div>
                </div>

                {/* Web Search Panel */}
                {showWebSearch && (
                  <div className="mt-4 p-4 bg-void-surface rounded-lg border border-void-lighter">
                    <WebSearchPanel
                      notebookId={selectedNotebook.id}
                      onSourcesAdded={handleWebSourcesAdded}
                    />
                  </div>
                )}
              </div>

              {/* Document List */}
              <div className="flex-1 overflow-y-auto p-6">
                {isLoadingDocs ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-glow" />
                  </div>
                ) : documents.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <FileText className="w-16 h-16 text-text-dim mb-4" />
                    <h3 className="text-lg font-medium text-text mb-2">No documents yet</h3>
                    <p className="text-text-muted mb-6 max-w-md">
                      Upload files or add web content to this notebook for RAG queries
                    </p>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setShowWebSearch(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-void-surface text-text rounded-lg hover:bg-void-lighter transition-colors"
                      >
                        <Globe className="w-4 h-4" />
                        Add from Web
                      </button>
                      <label className="flex items-center gap-2 px-4 py-2 bg-glow text-void rounded-lg hover:bg-glow/90 transition-colors cursor-pointer">
                        <Upload className="w-4 h-4" />
                        Upload Files
                        <input
                          type="file"
                          multiple
                          onChange={handleFileUpload}
                          className="hidden"
                          accept=".pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls"
                        />
                      </label>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {documents.map((doc) => (
                      <div
                        key={doc.source_id}
                        className={`
                          flex items-center gap-4 p-4 rounded-lg border transition-all
                          ${doc.active !== false
                            ? 'bg-void-surface border-void-lighter'
                            : 'bg-void-light border-void-lighter opacity-60'
                          }
                        `}
                      >
                        {/* File icon */}
                        <div className={`
                          w-10 h-10 rounded-lg flex items-center justify-center
                          ${doc.active !== false ? 'bg-nebula/10' : 'bg-void-lighter'}
                        `}>
                          <FileText className={`w-5 h-5 ${doc.active !== false ? 'text-nebula' : 'text-text-dim'}`} />
                        </div>

                        {/* File info */}
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-text truncate">
                            {doc.filename}
                          </div>
                          <div className="text-xs text-text-dim">
                            {doc.file_type || 'Document'}
                            {doc.active === false && ' • Disabled'}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2">
                          {/* Toggle active */}
                          <button
                            onClick={() => handleToggleDocument(doc)}
                            className={`
                              px-3 py-1.5 text-xs rounded-lg transition-colors
                              ${doc.active !== false
                                ? 'bg-glow/10 text-glow hover:bg-glow/20'
                                : 'bg-void-lighter text-text-dim hover:text-text'
                              }
                            `}
                          >
                            {doc.active !== false ? 'Active' : 'Enable'}
                          </button>

                          {/* Delete */}
                          <button
                            onClick={() => handleDeleteDocument(doc)}
                            className="p-2 text-text-dim hover:text-danger hover:bg-danger/10 rounded-lg transition-colors"
                            title="Remove document"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </MainLayout>
  );
}

export default DocumentsLandingPage;
