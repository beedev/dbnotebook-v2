import { Sparkles, Check, X } from 'lucide-react';

interface QueryRefinementProps {
  originalQuery: string;
  suggestions: string[];
  confidence: number;
  onSelectSuggestion: (query: string) => void;
  onKeepOriginal: () => void;
}

export function QueryRefinement({
  originalQuery,
  suggestions,
  confidence,
  onSelectSuggestion,
  onKeepOriginal
}: QueryRefinementProps) {
  // Confidence color mapping
  const getConfidenceColor = (conf: number): string => {
    if (conf >= 0.8) return 'text-success';
    if (conf >= 0.6) return 'text-warning';
    return 'text-text-muted';
  };

  const getConfidenceLabel = (conf: number): string => {
    if (conf >= 0.8) return 'High confidence';
    if (conf >= 0.6) return 'Medium confidence';
    return 'Low confidence';
  };

  return (
    <div className="rounded-lg border border-nebula/30 bg-nebula-subtle/50 backdrop-blur-sm p-4 animate-[slide-up_0.4s_ease-out]">
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-nebula/20 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-nebula" aria-hidden="true" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-text mb-1 font-[family-name:var(--font-display)]">
            Query Refinement Suggestions
          </h3>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-medium ${getConfidenceColor(confidence)}`}>
              {getConfidenceLabel(confidence)}
            </span>
            <span className="text-xs text-text-dim">
              {(confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Original query */}
      <div className="mb-3 pb-3 border-b border-void-surface">
        <p className="text-xs text-text-muted mb-1">Original query:</p>
        <p className="text-sm text-text-dim italic">"{originalQuery}"</p>
      </div>

      {/* Suggestion chips */}
      <div className="space-y-2 mb-4">
        <p className="text-xs text-text-muted">Suggested refinements:</p>
        <div className="flex flex-col gap-2">
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              onClick={() => onSelectSuggestion(suggestion)}
              className="group text-left px-3 py-2 rounded-lg bg-void-light border border-void-surface hover:border-nebula/50 hover:bg-void-surface transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-nebula focus-visible:ring-offset-2 focus-visible:ring-offset-void-light"
              aria-label={`Use refined query: ${suggestion}`}
            >
              <div className="flex items-start gap-2">
                <Check className="w-4 h-4 text-nebula flex-shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" aria-hidden="true" />
                <span className="text-sm text-text group-hover:text-nebula-bright transition-colors">
                  {suggestion}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 pt-2 border-t border-void-surface">
        <button
          onClick={onKeepOriginal}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-text-muted hover:text-text transition-colors rounded-md hover:bg-void-surface focus:outline-none focus-visible:ring-2 focus-visible:ring-glow"
          aria-label="Keep original query"
        >
          <X className="w-3.5 h-3.5" />
          Keep original
        </button>
      </div>
    </div>
  );
}

export default QueryRefinement;
