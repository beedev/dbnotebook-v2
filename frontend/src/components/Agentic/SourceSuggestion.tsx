import { FileSearch, Globe, Upload, SkipForward } from 'lucide-react';

interface SourceSuggestionProps {
  reason: string;
  suggestedQuery: string;
  onSearchWeb: (query: string) => void;
  onUpload: () => void;
  onSkip: () => void;
}

export function SourceSuggestion({
  reason,
  suggestedQuery,
  onSearchWeb,
  onUpload,
  onSkip
}: SourceSuggestionProps) {
  return (
    <div className="rounded-lg border border-warning/30 bg-warning/5 backdrop-blur-sm p-4 animate-[slide-up_0.4s_ease-out]">
      {/* Header */}
      <div className="flex items-start gap-3 mb-4">
        <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-warning/10 flex items-center justify-center">
          <FileSearch className="w-5 h-5 text-warning" aria-hidden="true" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-text mb-1 font-[family-name:var(--font-display)]">
            Missing Knowledge Source
          </h3>
          <p className="text-sm text-text-muted leading-relaxed">
            {reason}
          </p>
        </div>
      </div>

      {/* Suggested query */}
      <div className="mb-4 p-3 rounded-lg bg-void-light border border-void-surface">
        <p className="text-xs text-text-muted mb-1">Suggested search:</p>
        <p className="text-sm text-text font-medium font-[family-name:var(--font-code)]">
          "{suggestedQuery}"
        </p>
      </div>

      {/* Action buttons */}
      <div className="space-y-2">
        <p className="text-xs text-text-muted mb-2">What would you like to do?</p>

        {/* Search Web */}
        <button
          onClick={() => onSearchWeb(suggestedQuery)}
          className="w-full group flex items-center gap-3 px-4 py-3 rounded-lg bg-glow/5 hover:bg-glow/10 border border-glow/20 hover:border-glow/40 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-glow focus-visible:ring-offset-2 focus-visible:ring-offset-void-light"
          aria-label="Search web for suggested content"
        >
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-glow/10 group-hover:bg-glow/20 flex items-center justify-center transition-colors">
            <Globe className="w-4 h-4 text-glow" aria-hidden="true" />
          </div>
          <div className="flex-1 text-left">
            <p className="text-sm font-medium text-text group-hover:text-glow transition-colors">
              Search Web
            </p>
            <p className="text-xs text-text-dim">
              Find and import relevant content
            </p>
          </div>
        </button>

        {/* Upload Document */}
        <button
          onClick={onUpload}
          className="w-full group flex items-center gap-3 px-4 py-3 rounded-lg bg-nebula/5 hover:bg-nebula/10 border border-nebula/20 hover:border-nebula/40 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-nebula focus-visible:ring-offset-2 focus-visible:ring-offset-void-light"
          aria-label="Upload a document"
        >
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-nebula/10 group-hover:bg-nebula/20 flex items-center justify-center transition-colors">
            <Upload className="w-4 h-4 text-nebula" aria-hidden="true" />
          </div>
          <div className="flex-1 text-left">
            <p className="text-sm font-medium text-text group-hover:text-nebula transition-colors">
              Upload Document
            </p>
            <p className="text-xs text-text-dim">
              Add files from your computer
            </p>
          </div>
        </button>

        {/* Skip */}
        <button
          onClick={onSkip}
          className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-medium text-text-muted hover:text-text rounded-lg hover:bg-void-surface transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-glow"
          aria-label="Skip this suggestion"
        >
          <SkipForward className="w-3.5 h-3.5" aria-hidden="true" />
          Skip for now
        </button>
      </div>
    </div>
  );
}

export default SourceSuggestion;
