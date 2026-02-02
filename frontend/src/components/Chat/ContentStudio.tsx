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
  Upload,
  Palette,
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
  isFullScreen?: boolean;
}

const generatorIcons: Record<string, React.ReactNode> = {
  infographic: <ImageIcon className="w-4 h-4" />,
  mindmap: <Network className="w-4 h-4" />,
};

export function ContentStudio({ notebookId, notebookName, isFullScreen = false }: ContentStudioProps) {
  const [isExpanded, setIsExpanded] = useState(isFullScreen);
  const [generators, setGenerators] = useState<StudioGeneratorInfo[]>([]);
  const [gallery, setGallery] = useState<GeneratedContent[]>([]);
  const [selectedGenerator, setSelectedGenerator] = useState<string>('infographic');
  const [customPrompt, setCustomPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoadingGallery, setIsLoadingGallery] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState<GeneratedContent | null>(null);
  const [referenceImage, setReferenceImage] = useState<string | null>(null);
  const [referenceImageName, setReferenceImageName] = useState<string | null>(null);

  // Load generators on mount
  useEffect(() => {
    loadGenerators();
  }, []);

  // Load gallery when notebook changes or entering full screen mode
  useEffect(() => {
    if (notebookId && (isExpanded || isFullScreen)) {
      loadGallery();
    }
  }, [notebookId, isExpanded, isFullScreen]);

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

  // Convert file to base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        const result = reader.result as string;
        // Remove data URL prefix (e.g., "data:image/png;base64,")
        const base64 = result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = error => reject(error);
    });
  };

  // Handle reference image upload
  const handleReferenceImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please upload an image file (PNG, JPG, etc.)');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('Image file must be less than 5MB');
      return;
    }

    try {
      const base64 = await fileToBase64(file);
      setReferenceImage(base64);
      setReferenceImageName(file.name);
      setError(null);
    } catch {
      setError('Failed to process image');
    }
  };

  // Clear reference image
  const clearReferenceImage = () => {
    setReferenceImage(null);
    setReferenceImageName(null);
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
        reference_image: referenceImage || undefined,
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

  // Helper to render the preview modal
  const renderPreviewModal = () => {
    if (!previewContent) return null;

    return (
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
    );
  };

  if (!notebookId) {
    // Show helpful message in full-screen mode when no notebook selected
    if (isFullScreen) {
      return (
        <div className="flex flex-col items-center justify-center h-full bg-void text-center p-8">
          <Sparkles className="w-16 h-16 text-glow/30 mb-6" />
          <h2 className="text-xl font-semibold text-text mb-2 font-[family-name:var(--font-display)]">
            Content Studio
          </h2>
          <p className="text-text-muted max-w-md mb-4">
            Select a notebook with documents to generate infographics and mind maps from your content.
          </p>
          <p className="text-sm text-text-dim">
            Use the sidebar to select a notebook →
          </p>
        </div>
      );
    }
    return null;
  }

  // Full-screen studio mode
  if (isFullScreen) {
    return (
      <div className="flex flex-col h-full bg-void">
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Generator Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-glow" />
                <h2 className="text-lg font-semibold text-text font-[family-name:var(--font-display)]">
                  Content Studio
                </h2>
              </div>
              <p className="text-sm text-text-muted">
                Generate visual content from "{notebookName || 'your notebook'}"
              </p>
            </div>

            {/* Generator Selection */}
            <div className="bg-void-light rounded-xl p-6 border border-void-surface space-y-4">
              <label className="text-xs font-medium text-text-muted uppercase tracking-wider">
                Content Type
              </label>
              <div className="flex gap-3">
                {generators.map((gen) => (
                  <button
                    key={gen.content_type}
                    onClick={() => setSelectedGenerator(gen.content_type)}
                    className={`
                      flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all flex-1
                      ${selectedGenerator === gen.content_type
                        ? 'bg-glow text-void shadow-lg shadow-glow/20'
                        : 'bg-void-surface text-text-muted hover:text-text hover:bg-void-lighter'
                      }
                    `}
                  >
                    {generatorIcons[gen.content_type] || <ImageIcon className="w-5 h-5" />}
                    <span className="capitalize">{gen.name || gen.content_type}</span>
                  </button>
                ))}
              </div>

              {/* Custom prompt */}
              <div className="space-y-2">
                <label className="text-xs font-medium text-text-muted uppercase tracking-wider">
                  Custom Instructions (optional)
                </label>
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="Add specific instructions for generation..."
                  className="w-full px-4 py-3 rounded-lg bg-void-surface border border-void-lighter text-sm text-text placeholder:text-text-dim focus:outline-none focus:border-glow/50 resize-none transition-colors"
                  rows={3}
                  disabled={isGenerating}
                />
              </div>

              {/* Reference image */}
              <div className="space-y-2">
                <label className="text-xs font-medium text-text-muted uppercase tracking-wider flex items-center gap-1">
                  <Palette className="w-3 h-3" />
                  Brand Reference (optional)
                </label>
                {referenceImage ? (
                  <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-void-surface border border-glow/30">
                    <ImageIcon className="w-5 h-5 text-glow" />
                    <span className="text-sm text-text truncate flex-1">{referenceImageName}</span>
                    <button
                      onClick={clearReferenceImage}
                      className="p-1.5 rounded hover:bg-void-lighter text-text-dim hover:text-text transition-colors"
                      title="Remove reference image"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <label className="flex items-center gap-3 px-4 py-3 rounded-lg bg-void-surface border border-void-lighter border-dashed cursor-pointer hover:border-glow/50 hover:bg-void-lighter transition-colors">
                    <Upload className="w-5 h-5 text-text-dim" />
                    <span className="text-sm text-text-dim">Upload logo or brand image for color extraction</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleReferenceImageUpload}
                      className="hidden"
                      disabled={isGenerating}
                    />
                  </label>
                )}
              </div>

              {/* Generate button */}
              <button
                onClick={handleGenerate}
                disabled={isGenerating || generators.length === 0}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-lg bg-glow text-void font-medium text-base hover:bg-glow-bright disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Generating...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    <span>Generate {selectedGenerator}</span>
                  </>
                )}
              </button>

              {/* Error message */}
              {error && (
                <div className="px-4 py-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">
                  {error}
                </div>
              )}
            </div>

            {/* Gallery Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-text-muted uppercase tracking-wider">
                  Generated Content ({gallery.length})
                </h3>
                <button
                  onClick={loadGallery}
                  disabled={isLoadingGallery}
                  className="p-2 rounded-lg hover:bg-void-surface text-text-dim hover:text-text transition-colors"
                >
                  <RefreshCw className={`w-4 h-4 ${isLoadingGallery ? 'animate-spin' : ''}`} />
                </button>
              </div>

              {isLoadingGallery ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 text-glow animate-spin" />
                </div>
              ) : gallery.length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {gallery.map((item) => (
                    <div
                      key={item.content_id}
                      className="group relative aspect-square rounded-xl overflow-hidden bg-void-surface cursor-pointer hover:ring-2 hover:ring-glow/50 transition-all"
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
                          {generatorIcons[item.content_type] || <ImageIcon className="w-8 h-8 text-text-dim" />}
                        </div>
                      )}
                      <div className="absolute inset-0 bg-gradient-to-t from-void/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                        <div className="absolute bottom-2 left-2 right-2">
                          <p className="text-sm text-text font-medium truncate">{item.title}</p>
                          <p className="text-xs text-text-dim">{formatDate(item.created_at)}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-text-dim">
                  <ImageIcon className="w-12 h-12 mb-3 opacity-50" />
                  <p className="text-sm">No generated content yet</p>
                  <p className="text-xs mt-1">Generate an infographic or mind map to get started</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Preview Modal */}
        {previewContent && renderPreviewModal()}
      </div>
    );
  }

  // Compact expandable mode (original behavior)
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

            {/* Reference image for brand extraction */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-text-muted uppercase tracking-wider flex items-center gap-1">
                <Palette className="w-3 h-3" />
                Brand Reference (optional)
              </label>
              {referenceImage ? (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-void-surface border border-glow/30">
                  <ImageIcon className="w-4 h-4 text-glow" />
                  <span className="text-sm text-text truncate flex-1">{referenceImageName}</span>
                  <button
                    onClick={clearReferenceImage}
                    className="p-1 rounded hover:bg-void-lighter text-text-dim hover:text-text transition-colors"
                    title="Remove reference image"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <label className="flex items-center gap-2 px-3 py-2 rounded-lg bg-void-surface border border-void-lighter border-dashed cursor-pointer hover:border-glow/50 hover:bg-void-lighter transition-colors">
                  <Upload className="w-4 h-4 text-text-dim" />
                  <span className="text-sm text-text-dim">Upload logo/brand image for color extraction</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleReferenceImageUpload}
                    className="hidden"
                    disabled={isGenerating}
                  />
                </label>
              )}
              <p className="text-xs text-text-dim">
                Colors and style will be extracted from the image
              </p>
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
      {renderPreviewModal()}
    </>
  );
}

export default ContentStudio;
