import { Lightbulb, X, ChevronRight } from 'lucide-react';
import type { ReactNode } from 'react';

export interface Suggestion {
  id: string;
  type: 'document' | 'query' | 'action';
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface SuggestionCardProps {
  suggestion: Suggestion;
  onDismiss?: (id: string) => void;
  variant?: 'inline' | 'floating';
}

export function SuggestionCard({
  suggestion,
  onDismiss,
  variant = 'inline'
}: SuggestionCardProps) {
  const baseClasses = "group relative rounded-lg border transition-all duration-200";

  const variantClasses = {
    inline: "bg-void-light border-void-surface hover:border-glow/30 hover:bg-void-surface p-4",
    floating: "bg-void-surface/90 backdrop-blur-sm border-glow/20 shadow-glow p-4 animate-[slide-in-right_0.3s_ease-out]"
  };

  const typeConfig: Record<Suggestion['type'], { icon: ReactNode; color: string }> = {
    document: {
      icon: <Lightbulb className="w-5 h-5" />,
      color: 'text-nebula'
    },
    query: {
      icon: <Lightbulb className="w-5 h-5" />,
      color: 'text-glow'
    },
    action: {
      icon: <Lightbulb className="w-5 h-5" />,
      color: 'text-glow-bright'
    }
  };

  const config = typeConfig[suggestion.type];

  return (
    <div className={`${baseClasses} ${variantClasses[variant]}`}>
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div
          className={`flex-shrink-0 w-10 h-10 rounded-lg bg-void-lighter flex items-center justify-center ${config.color} group-hover:scale-105 transition-transform`}
          aria-hidden="true"
        >
          {config.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-text mb-1 font-[family-name:var(--font-display)]">
            {suggestion.title}
          </h4>
          <p className="text-xs text-text-muted leading-relaxed">
            {suggestion.description}
          </p>

          {/* Action button */}
          {suggestion.action && (
            <button
              onClick={suggestion.action.onClick}
              className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-glow hover:text-glow-bright transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-glow focus-visible:ring-offset-2 focus-visible:ring-offset-void-light rounded"
              aria-label={suggestion.action.label}
            >
              {suggestion.action.label}
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Dismiss button */}
        {onDismiss && (
          <button
            onClick={() => onDismiss(suggestion.id)}
            className="flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center text-text-dim hover:text-text hover:bg-void-surface transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-glow"
            aria-label="Dismiss suggestion"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

export default SuggestionCard;
