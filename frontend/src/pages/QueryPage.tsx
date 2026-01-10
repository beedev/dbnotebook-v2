/**
 * Query API Page
 *
 * Simple interface to test the programmatic RAG API:
 * 1. Select a notebook from the list
 * 2. Enter a query
 * 3. View the response and sources
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Search,
  Send,
  Book,
  FileText,
  Clock,
  Loader2,
  CheckCircle,
  AlertCircle,
  Copy,
  Check
} from 'lucide-react';

interface Notebook {
  id: string;
  name: string;
  document_count: number;
  created_at: string | null;
}

interface Source {
  document: string;
  excerpt: string;
  score: number;
}

interface QueryResponse {
  success: boolean;
  response?: string;
  sources?: Source[];
  metadata?: {
    execution_time_ms: number;
    model: string;
    retrieval_strategy: string;
    node_count: number;
  };
  error?: string;
}

export function QueryPage() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [selectedNotebook, setSelectedNotebook] = useState<Notebook | null>(null);
  const [query, setQuery] = useState('');
  const [isLoadingNotebooks, setIsLoadingNotebooks] = useState(true);
  const [isQuerying, setIsQuerying] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Load notebooks on mount
  useEffect(() => {
    loadNotebooks();
  }, []);

  const loadNotebooks = async () => {
    setIsLoadingNotebooks(true);
    setError(null);
    try {
      const res = await fetch('/api/query/notebooks');
      const data = await res.json();
      if (data.success) {
        setNotebooks(data.notebooks || []);
      } else {
        setError(data.error || 'Failed to load notebooks');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load notebooks');
    } finally {
      setIsLoadingNotebooks(false);
    }
  };

  const handleQuery = useCallback(async () => {
    if (!selectedNotebook || !query.trim()) return;

    setIsQuerying(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          notebook_id: selectedNotebook.id,
          query: query.trim(),
          include_sources: true,
          max_sources: 6,
        }),
      });

      const data: QueryResponse = await res.json();
      setResponse(data);

      if (!data.success) {
        setError(data.error || 'Query failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed');
    } finally {
      setIsQuerying(false);
    }
  }, [selectedNotebook, query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleQuery();
    }
  };

  const copyResponse = () => {
    if (response?.response) {
      navigator.clipboard.writeText(response.response);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Unknown';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="query-page h-full flex flex-col bg-void">
      {/* Header */}
      <div className="p-6 border-b border-void-surface">
        <h1 className="text-2xl font-bold text-text mb-2">
          <span className="gradient-text">Query</span> API
        </h1>
        <p className="text-text-muted text-sm">
          Test the programmatic RAG API - select a notebook and ask questions
        </p>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Notebook Selection */}
        <div className="w-80 border-r border-void-surface flex flex-col">
          <div className="p-4 border-b border-void-surface">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2">
              <Book className="w-4 h-4 text-glow" />
              Select Notebook
            </h2>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {isLoadingNotebooks ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-glow animate-spin" />
              </div>
            ) : notebooks.length === 0 ? (
              <div className="text-center py-8 text-text-muted">
                <Book className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No notebooks found</p>
              </div>
            ) : (
              <div className="space-y-1">
                {notebooks.map((nb) => (
                  <button
                    key={nb.id}
                    onClick={() => setSelectedNotebook(nb)}
                    className={`
                      w-full text-left p-3 rounded-lg transition-all
                      ${selectedNotebook?.id === nb.id
                        ? 'bg-glow/20 border border-glow/50'
                        : 'bg-void-surface hover:bg-void-lighter border border-transparent'
                      }
                    `}
                  >
                    <div className="flex items-start justify-between">
                      <span className={`font-medium text-sm ${
                        selectedNotebook?.id === nb.id ? 'text-glow' : 'text-text'
                      }`}>
                        {nb.name}
                      </span>
                      {selectedNotebook?.id === nb.id && (
                        <CheckCircle className="w-4 h-4 text-glow shrink-0" />
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-text-muted">
                      <span className="flex items-center gap-1">
                        <FileText className="w-3 h-3" />
                        {nb.document_count} docs
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDate(nb.created_at)}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Query and Response */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Query Input */}
          <div className="p-4 border-b border-void-surface">
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-dim" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={selectedNotebook
                    ? `Ask about ${selectedNotebook.name}...`
                    : 'Select a notebook first...'
                  }
                  disabled={!selectedNotebook || isQuerying}
                  className="
                    w-full pl-10 pr-4 py-3
                    bg-void-surface text-text
                    rounded-lg border border-void-lighter
                    placeholder:text-text-dim
                    focus:outline-none focus:border-glow focus:ring-1 focus:ring-glow/30
                    disabled:opacity-50 disabled:cursor-not-allowed
                    transition-all
                  "
                />
              </div>
              <button
                onClick={handleQuery}
                disabled={!selectedNotebook || !query.trim() || isQuerying}
                className="
                  px-6 py-3 rounded-lg
                  bg-glow text-void font-medium
                  hover:bg-glow-bright
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transition-all flex items-center gap-2
                "
              >
                {isQuerying ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Querying...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Send
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Response Area */}
          <div className="flex-1 overflow-y-auto p-4">
            {error && (
              <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-red-400">Error</p>
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              </div>
            )}

            {response?.success && (
              <div className="space-y-4">
                {/* Response */}
                <div className="bg-void-surface rounded-lg border border-void-lighter overflow-hidden">
                  <div className="p-3 border-b border-void-lighter flex items-center justify-between">
                    <h3 className="font-semibold text-text flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-green-400" />
                      Response
                    </h3>
                    <button
                      onClick={copyResponse}
                      className="p-1.5 rounded hover:bg-void-lighter transition-colors"
                      title="Copy response"
                    >
                      {copied ? (
                        <Check className="w-4 h-4 text-green-400" />
                      ) : (
                        <Copy className="w-4 h-4 text-text-muted" />
                      )}
                    </button>
                  </div>
                  <div className="p-4">
                    <p className="text-text whitespace-pre-wrap leading-relaxed">
                      {response.response}
                    </p>
                  </div>
                </div>

                {/* Metadata */}
                {response.metadata && (
                  <div className="flex flex-wrap gap-3 text-xs">
                    <span className="px-2 py-1 bg-void-surface rounded text-text-muted">
                      <Clock className="w-3 h-3 inline mr-1" />
                      {(response.metadata.execution_time_ms / 1000).toFixed(2)}s
                    </span>
                    <span className="px-2 py-1 bg-void-surface rounded text-text-muted">
                      Model: {response.metadata.model}
                    </span>
                    <span className="px-2 py-1 bg-void-surface rounded text-text-muted">
                      Strategy: {response.metadata.retrieval_strategy}
                    </span>
                    <span className="px-2 py-1 bg-void-surface rounded text-text-muted">
                      {response.metadata.node_count} nodes
                    </span>
                  </div>
                )}

                {/* Sources */}
                {response.sources && response.sources.length > 0 && (
                  <div className="bg-void-surface rounded-lg border border-void-lighter overflow-hidden">
                    <div className="p-3 border-b border-void-lighter">
                      <h3 className="font-semibold text-text flex items-center gap-2">
                        <FileText className="w-4 h-4 text-nebula-bright" />
                        Sources ({response.sources.length})
                      </h3>
                    </div>
                    <div className="divide-y divide-void-lighter">
                      {response.sources.map((source, idx) => (
                        <div key={idx} className="p-3">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium text-text">
                              {source.document}
                            </span>
                            <span className="text-xs px-2 py-0.5 bg-nebula/20 text-nebula-bright rounded">
                              {(source.score * 100).toFixed(1)}% match
                            </span>
                          </div>
                          <p className="text-sm text-text-muted line-clamp-2">
                            {source.excerpt}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Empty State */}
            {!response && !error && !isQuerying && (
              <div className="h-full flex items-center justify-center">
                <div className="text-center max-w-md">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-glow/10 flex items-center justify-center">
                    <Search className="w-8 h-8 text-glow" />
                  </div>
                  <h3 className="text-lg font-semibold text-text mb-2">
                    Ready to Query
                  </h3>
                  <p className="text-text-muted text-sm">
                    {selectedNotebook
                      ? `Selected: ${selectedNotebook.name}. Enter your question above.`
                      : 'Select a notebook from the left panel, then enter your question.'
                    }
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default QueryPage;
