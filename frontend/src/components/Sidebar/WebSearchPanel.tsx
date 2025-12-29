import { useState } from 'react';
import {
  Search,
  Globe,
  Plus,
  ExternalLink,
  Loader2,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Eye,
} from 'lucide-react';
import { useWebSearch } from '../../hooks/useWebSearch';

interface WebSearchPanelProps {
  notebookId: string | null;
  onSourcesAdded?: () => void;
}

export function WebSearchPanel({ notebookId, onSourcesAdded }: WebSearchPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Use the web search hook
  const {
    results,
    isSearching,
    isAdding,
    error,
    successMessage,
    selectedUrls,
    previewUrl,
    previewContent,
    isLoadingPreview,
    search,
    toggleUrl,
    selectAll,
    selectNone,
    preview,
    importSelected,
  } = useWebSearch();

  const [localQuery, setLocalQuery] = useState('');

  const handleSearch = async () => {
    if (!localQuery.trim()) return;
    await search(localQuery.trim(), 5);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isSearching) {
      handleSearch();
    }
  };

  const handleAddSources = async () => {
    if (!notebookId || selectedUrls.size === 0) return;

    const result = await importSelected(notebookId);
    if (result.success) {
      onSourcesAdded?.();
    }
  };

  const handlePreview = async (url: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await preview(url, 500);
  };

  if (!notebookId) {
    return (
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider font-[family-name:var(--font-display)] px-1">
          Web Search
        </h3>
        <p className="text-sm text-text-dim px-1">
          Select a notebook to search the web
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Header with toggle */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-xs font-semibold text-text-muted uppercase tracking-wider font-[family-name:var(--font-display)] px-1 hover:text-text transition-colors"
      >
        <span className="flex items-center gap-2">
          <Globe className="w-3.5 h-3.5" />
          Web Search
        </span>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>

      {isExpanded && (
        <div className="space-y-3">
          {/* Search input */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim" />
              <input
                type="text"
                value={localQuery}
                onChange={(e) => setLocalQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Search the web..."
                className="w-full pl-9 pr-3 py-2 rounded-lg bg-void-surface border border-void-lighter text-sm text-text placeholder:text-text-dim focus:outline-none focus:border-glow/50 transition-colors"
                disabled={isSearching}
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={isSearching || !localQuery.trim()}
              className="px-3 py-2 rounded-lg bg-glow/20 text-glow hover:bg-glow/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSearching ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
            </button>
          </div>

          {/* Error message */}
          {error && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-danger/10 border border-danger/30 text-danger text-xs">
              <XCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Success message */}
          {successMessage && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-success/10 border border-success/30 text-success text-xs">
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Search results */}
          {results.length > 0 && (
            <div className="space-y-2">
              {/* Selection controls */}
              <div className="flex items-center justify-between text-xs text-text-dim px-1">
                <span>{selectedUrls.size} of {results.length} selected</span>
                <div className="flex gap-2">
                  <button
                    onClick={selectAll}
                    className="hover:text-text transition-colors"
                  >
                    Select all
                  </button>
                  <span>|</span>
                  <button
                    onClick={selectNone}
                    className="hover:text-text transition-colors"
                  >
                    Clear
                  </button>
                </div>
              </div>

              {/* Results list */}
              <div className="space-y-1 max-h-[300px] overflow-y-auto">
                {results.map((result) => (
                  <div
                    key={result.url}
                    className={`
                      rounded-lg transition-all duration-200
                      ${selectedUrls.has(result.url)
                        ? 'bg-glow/10 border border-glow/30'
                        : 'bg-void-surface hover:bg-void-lighter border border-transparent'
                      }
                    `}
                  >
                    <div
                      onClick={() => toggleUrl(result.url)}
                      className="p-2 cursor-pointer"
                    >
                      <div className="flex items-start gap-2">
                        <div className={`
                          mt-0.5 w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0
                          ${selectedUrls.has(result.url)
                            ? 'border-glow bg-glow'
                            : 'border-text-dim'
                          }
                        `}>
                          {selectedUrls.has(result.url) && (
                            <CheckCircle className="w-3 h-3 text-void" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-medium text-text truncate">
                            {result.title}
                          </h4>
                          <p className="text-xs text-text-dim line-clamp-2 mt-0.5">
                            {result.description}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <a
                              href={result.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="flex items-center gap-1 text-xs text-glow/70 hover:text-glow"
                            >
                              <ExternalLink className="w-3 h-3" />
                              <span className="truncate">{new URL(result.url).hostname}</span>
                            </a>
                            <button
                              onClick={(e) => handlePreview(result.url, e)}
                              className="flex items-center gap-1 text-xs text-text-dim hover:text-text transition-colors"
                              title="Preview content"
                            >
                              {isLoadingPreview && previewUrl === result.url ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                <Eye className="w-3 h-3" />
                              )}
                              <span>Preview</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                    {/* Preview panel */}
                    {previewUrl === result.url && previewContent && (
                      <div className="px-2 pb-2">
                        <div className="p-2 rounded bg-void border border-void-lighter text-xs">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-text">{previewContent.title}</span>
                            <span className="text-text-dim">{previewContent.word_count.toLocaleString()} words</span>
                          </div>
                          <p className="text-text-dim leading-relaxed">
                            {previewContent.content_preview}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Add button */}
              <button
                onClick={handleAddSources}
                disabled={selectedUrls.size === 0 || isAdding}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-glow text-void font-medium text-sm hover:bg-glow-bright disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isAdding ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Plus className="w-4 h-4" />
                )}
                <span>
                  {isAdding ? 'Adding...' : `Add ${selectedUrls.size} source${selectedUrls.size !== 1 ? 's' : ''} to notebook`}
                </span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default WebSearchPanel;
