import { useState } from 'react';
import { ChevronDown, ChevronUp, BarChart3, AlertTriangle, Lightbulb, ExternalLink, X } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface Insight {
  type: 'stat' | 'warning' | 'tip';
  icon?: string;
  content: string;
}

interface InsightPanelProps {
  documentName: string;
  insights: Insight[];
  onExplore?: () => void;
  onDismiss?: () => void;
}

export function InsightPanel({
  documentName,
  insights,
  onExplore,
  onDismiss
}: InsightPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Icon and styling configuration per insight type
  const getInsightConfig = (type: Insight['type']): {
    icon: LucideIcon;
    bgColor: string;
    iconColor: string;
    textColor: string;
  } => {
    switch (type) {
      case 'stat':
        return {
          icon: BarChart3,
          bgColor: 'bg-glow/10',
          iconColor: 'text-glow',
          textColor: 'text-text'
        };
      case 'warning':
        return {
          icon: AlertTriangle,
          bgColor: 'bg-warning/10',
          iconColor: 'text-warning',
          textColor: 'text-text'
        };
      case 'tip':
        return {
          icon: Lightbulb,
          bgColor: 'bg-nebula/10',
          iconColor: 'text-nebula',
          textColor: 'text-text'
        };
    }
  };

  return (
    <div className="rounded-lg border border-glow/20 bg-void-surface/80 backdrop-blur-sm shadow-glow animate-[slide-up_0.4s_ease-out]">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-void-lighter">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-glow/10 flex items-center justify-center">
            <BarChart3 className="w-5 h-5 text-glow" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-text font-[family-name:var(--font-display)] truncate">
              Document Insights
            </h3>
            <p className="text-xs text-text-muted truncate">
              {documentName}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-7 h-7 rounded-md flex items-center justify-center text-text-muted hover:text-text hover:bg-void-lighter transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-glow"
            aria-label={isExpanded ? 'Collapse insights' : 'Expand insights'}
            aria-expanded={isExpanded}
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="w-7 h-7 rounded-md flex items-center justify-center text-text-dim hover:text-text hover:bg-void-lighter transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-glow"
              aria-label="Dismiss insights panel"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-4 space-y-3">
          {insights.length === 0 ? (
            <p className="text-sm text-text-muted text-center py-2">
              No insights available
            </p>
          ) : (
            insights.map((insight, index) => {
              const config = getInsightConfig(insight.type);
              const Icon = config.icon;

              return (
                <div
                  key={index}
                  className={`flex items-start gap-3 p-3 rounded-lg ${config.bgColor} transition-colors`}
                >
                  <div className="flex-shrink-0">
                    <Icon className={`w-4 h-4 ${config.iconColor}`} aria-hidden="true" />
                  </div>
                  <p className={`text-sm ${config.textColor} leading-relaxed`}>
                    {insight.content}
                  </p>
                </div>
              );
            })
          )}

          {/* Action button */}
          {onExplore && insights.length > 0 && (
            <div className="pt-2 border-t border-void-lighter">
              <button
                onClick={onExplore}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-glow hover:text-glow-bright bg-glow/5 hover:bg-glow/10 border border-glow/20 hover:border-glow/40 rounded-lg transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-glow focus-visible:ring-offset-2 focus-visible:ring-offset-void-surface"
                aria-label="Explore document insights"
              >
                Explore document
                <ExternalLink className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default InsightPanel;
