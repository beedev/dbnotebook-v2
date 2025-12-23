import { useState, useEffect } from 'react';
import {
  Sparkles,
  Image as ImageIcon,
  Network,
  Loader2,
  Download,
  Trash2,
  ChevronDown,
  ChevronUp,
  X,
  ExternalLink,
  RefreshCw,
} from 'lucide-react';
import type { GeneratedContent, StudioGeneratorInfo } from '../../types';
import {
  getStudioGallery,
  getStudioGenerators,
  generateStudioContent,
  deleteStudioContent,
} from '../../services/api';

interface ContentStudioProps {
  notebookId: string | null;
  notebookName?: string;
}

const generatorIcons: Record<string, React.ReactNode> = {
  infographic: <ImageIcon className="w-4 h-4" />,
  mindmap: <Network className="w-4 h-4" />,
};

export function ContentStudio({ notebookId, notebookName }: ContentStudioProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [generators, setGenerators] = useState<StudioGeneratorInfo[]>([]);
  const [gallery, setGallery] = useState<GeneratedContent[]>([]);
  const [selectedGenerator, setSelectedGenerator] = useState<string>('infographic');
  const [customPrompt, setCustomPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoadingGallery, setIsLoadingGallery] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState<GeneratedContent | null>(null);

  // Load generators on mount
  useEffect(() => {
    loadGenerators();
  }, []);

  // Load gallery when notebook changes
  useEffect(() => {
    if (notebookId && isExpanded) {
      loadGallery();
    }
  }, [notebookId, isExpanded]);

  const loadGenerators = async () => {
    try {
      const response = await getStudioGenerators();
      setGenerators(response.generators.filter(g => g.available));
    } catch (err) {
      console.error('Failed to load generators:', err);
    }
  };

  const loadGallery = async () => {
    if (!notebookId) return;

    setIsLoadingGallery(true);
    try {
      const response = await getStudioGallery({ notebookId, limit: 10 });
      setGallery(response.items);
    } catch (err) {
      console.error('Failed to load gallery:', err);
    } finally {
      setIsLoadingGallery(false);
    }
  };

  const handleGenerate = async () => {
    if (!notebookId) return;

    setIsGenerating(true);
    setError(null);

    try {
      const response = await generateStudioContent({
        notebook_id: notebookId,
        type: selectedGenerator as 'infographic' | 'mindmap',
        prompt: customPrompt || undefined,
      });

      // Add to gallery at the beginning
      setGallery(prev => [response.content, ...prev]);
      setCustomPrompt('');
    } catch (err) {
      console.error('Generation error:', err);
      setError(err instanceof Error ? err.message : 'Generation failed. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDelete = async (contentId: string) => {
    if (!window.confirm('Delete this generated content?')) return;

    try {
      await deleteStudioContent(contentId);
      setGallery(prev => prev.filter(item => item.content_id !== contentId));
      if (previewContent?.content_id === contentId) {
        setPreviewContent(null);
      }
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!notebookId) {
    return null;
  }

  return (
    <>
      {/* Studio Panel */}
      <div className="border-b border-void-surface bg-void-light">
        {/* Header toggle */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-void-surface transition-colors"
        >
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-glow" />
            <span className="text-sm font-medium text-text">Content Studio</span>
            {gallery.length > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-glow/20 text-glow text-xs">
                {gallery.length}
              </span>
            )}
          </div>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-text-muted" />
          ) : (
            <ChevronDown className="w-4 h-4 text-text-muted" />
          )}
        </button>

        {isExpanded && (
          <div className="px-4 pb-4 space-y-4">
            {/* Generator selection */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-text-muted uppercase tracking-wider">
                Generate from "{notebookName || 'notebook'}"
              </label>
              <div className="flex gap-2">
                {generators.map((gen) => (
                  <button
                    key={gen.content_type}
                    onClick={() => setSelectedGenerator(gen.content_type)}
                    className={`
                      flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all
                      ${selectedGenerator === gen.content_type
                        ? 'bg-glow text-void'
                        : 'bg-void-surface text-text-muted hover:text-text hover:bg-void-lighter'
                      }
                    `}
                  >
                    {generatorIcons[gen.content_type] || <ImageIcon className="w-4 h-4" />}
                    <span className="capitalize">{gen.name || gen.content_type}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Custom prompt */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-text-muted uppercase tracking-wider">
                Custom instructions (optional)
              </label>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Add specific instructions for generation..."
                className="w-full px-3 py-2 rounded-lg bg-void-surface border border-void-lighter text-sm text-text placeholder:text-text-dim focus:outline-none focus:border-glow/50 resize-none transition-colors"
                rows={2}
                disabled={isGenerating}
              />
            </div>

            {/* Generate button */}
            <button
              onClick={handleGenerate}
              disabled={isGenerating || generators.length === 0}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-glow text-void font-medium text-sm hover:bg-glow-bright disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generate {selectedGenerator}</span>
                </>
              )}
            </button>

            {/* Error message */}
            {error && (
              <div className="px-3 py-2 rounded-lg bg-danger/10 border border-danger/30 text-danger text-xs">
                {error}
              </div>
            )}

            {/* Gallery */}
            {(gallery.length > 0 || isLoadingGallery) && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-text-muted uppercase tracking-wider">
                    Generated Content
                  </label>
                  <button
                    onClick={loadGallery}
                    disabled={isLoadingGallery}
                    className="p-1 rounded hover:bg-void-surface text-text-dim hover:text-text transition-colors"
                  >
                    <RefreshCw className={`w-3 h-3 ${isLoadingGallery ? 'animate-spin' : ''}`} />
                  </button>
                </div>

                {isLoadingGallery ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-5 h-5 text-glow animate-spin" />
                  </div>
                ) : (
                  <div className="grid grid-cols-4 gap-2">
                    {gallery.map((item) => (
                      <div
                        key={item.content_id}
                        className="group relative aspect-square rounded-lg overflow-hidden bg-void-surface cursor-pointer hover:ring-2 hover:ring-glow/50 transition-all"
                        onClick={() => setPreviewContent(item)}
                      >
                        {item.thumbnail_url ? (
                          <img
                            src={item.thumbnail_url}
                            alt={item.title}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            {generatorIcons[item.content_type] || <ImageIcon className="w-6 h-6 text-text-dim" />}
                          </div>
                        )}
                        <div className="absolute inset-0 bg-gradient-to-t from-void/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                          <div className="absolute bottom-1 left-1 right-1">
                            <p className="text-xs text-text truncate">{item.title}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {previewContent && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-void/80 backdrop-blur-sm"
          onClick={() => setPreviewContent(null)}
        >
          <div
            className="relative max-w-4xl max-h-[90vh] m-4 rounded-xl overflow-hidden bg-void-light border border-void-surface shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-void-surface">
              <div>
                <h3 className="font-medium text-text">{previewContent.title}</h3>
                <p className="text-xs text-text-dim">
                  {previewContent.content_type} - {formatDate(previewContent.created_at)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {previewContent.file_url && (
                  <a
                    href={previewContent.file_url}
                    download
                    className="p-2 rounded-lg hover:bg-void-surface text-text-muted hover:text-text transition-colors"
                    title="Download"
                  >
                    <Download className="w-4 h-4" />
                  </a>
                )}
                {previewContent.file_url && (
                  <a
                    href={previewContent.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg hover:bg-void-surface text-text-muted hover:text-text transition-colors"
                    title="Open in new tab"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
                <button
                  onClick={() => handleDelete(previewContent.content_id)}
                  className="p-2 rounded-lg hover:bg-danger/10 text-text-muted hover:text-danger transition-colors"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setPreviewContent(null)}
                  className="p-2 rounded-lg hover:bg-void-surface text-text-muted hover:text-text transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Modal content */}
            <div className="overflow-auto max-h-[calc(90vh-60px)]">
              {previewContent.file_url ? (
                <img
                  src={previewContent.file_url}
                  alt={previewContent.title}
                  className="w-full h-auto"
                />
              ) : (
                <div className="flex items-center justify-center py-20 text-text-dim">
                  <p>No preview available</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default ContentStudio;
