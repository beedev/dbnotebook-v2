import { useState, useCallback } from 'react';
import { ChevronDown, ChevronUp, Settings2 } from 'lucide-react';
import {
  RetrievalSettings,
  DEFAULT_RETRIEVAL_CONFIG,
  type RetrievalConfig,
} from '../shared';

export interface QuerySettings {
  searchStyle: number; // 0-100: 0 = keyword, 100 = semantic
  resultDepth: 'focused' | 'balanced' | 'comprehensive';
  temperature: number; // 0-100: maps to 0-2.0
  retrieval: RetrievalConfig;
}

export const DEFAULT_QUERY_SETTINGS: QuerySettings = {
  searchStyle: 50,
  resultDepth: 'balanced',
  temperature: 5, // 5 = 0.1 (low = deterministic, high = creative)
  retrieval: DEFAULT_RETRIEVAL_CONFIG,
};

interface QuerySettingsPanelProps {
  settings: QuerySettings;
  onChange: (settings: QuerySettings) => void;
  disabled?: boolean;
}

export function QuerySettingsPanel({
  settings,
  onChange,
  disabled = false,
}: QuerySettingsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleSearchStyleChange = useCallback(
    (value: number) => {
      onChange({ ...settings, searchStyle: value });
    },
    [settings, onChange]
  );

  const handleResultDepthChange = useCallback(
    (depth: QuerySettings['resultDepth']) => {
      onChange({ ...settings, resultDepth: depth });
    },
    [settings, onChange]
  );

  const handleTemperatureChange = useCallback(
    (value: number) => {
      onChange({ ...settings, temperature: value });
    },
    [settings, onChange]
  );

  const handleRetrievalChange = useCallback(
    (retrieval: RetrievalConfig) => {
      onChange({ ...settings, retrieval });
    },
    [settings, onChange]
  );

  // Determine if any settings are non-default
  const hasCustomQuerySettings =
    settings.searchStyle !== DEFAULT_QUERY_SETTINGS.searchStyle ||
    settings.resultDepth !== DEFAULT_QUERY_SETTINGS.resultDepth ||
    settings.temperature !== DEFAULT_QUERY_SETTINGS.temperature;

  const hasCustomRetrievalSettings =
    settings.retrieval.rerankerEnabled !== DEFAULT_RETRIEVAL_CONFIG.rerankerEnabled ||
    settings.retrieval.rerankerModel !== DEFAULT_RETRIEVAL_CONFIG.rerankerModel ||
    settings.retrieval.raptorEnabled !== DEFAULT_RETRIEVAL_CONFIG.raptorEnabled ||
    settings.retrieval.topK !== DEFAULT_RETRIEVAL_CONFIG.topK;

  const hasCustomSettings = hasCustomQuerySettings || hasCustomRetrievalSettings;

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-3">
      {/* Toggle Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        disabled={disabled}
        className={`
          flex items-center gap-2 text-xs font-medium transition-colors
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:text-glow cursor-pointer'}
          ${hasCustomSettings ? 'text-glow' : 'text-text-muted'}
        `}
      >
        <Settings2 size={14} />
        <span>Query Settings</span>
        {hasCustomSettings && (
          <span className="px-1.5 py-0.5 bg-glow/20 text-glow rounded text-[10px]">
            Custom
          </span>
        )}
        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {/* Expanded Panel */}
      {isExpanded && (
        <div
          className={`
            mt-3 p-4 rounded-lg border border-void-surface bg-void-light
            ${disabled ? 'opacity-50 pointer-events-none' : ''}
          `}
        >
          {/* Search Style Slider */}
          <div className="mb-5">
            <div className="flex justify-between items-center mb-2">
              <label className="text-xs font-medium text-text">
                Search Style
              </label>
              <span className="text-xs text-text-muted">
                {settings.searchStyle < 30
                  ? 'Keyword'
                  : settings.searchStyle > 70
                    ? 'Semantic'
                    : 'Hybrid'}
              </span>
            </div>
            <div className="relative">
              <input
                type="range"
                min="0"
                max="100"
                value={settings.searchStyle}
                onChange={(e) => handleSearchStyleChange(Number(e.target.value))}
                className="query-slider w-full"
              />
              <div className="flex justify-between text-[10px] text-text-dim mt-1">
                <span>Keyword</span>
                <span>Semantic</span>
              </div>
            </div>
          </div>

          {/* Result Depth Toggle */}
          <div className="mb-5">
            <label className="text-xs font-medium text-text block mb-2">
              Result Depth
            </label>
            <div className="flex gap-1 p-1 bg-void-surface/50 rounded-lg">
              {(['focused', 'balanced', 'comprehensive'] as const).map((depth) => (
                <button
                  key={depth}
                  onClick={() => handleResultDepthChange(depth)}
                  className={`
                    flex-1 py-2 px-3 text-xs font-medium rounded-md transition-all
                    ${
                      settings.resultDepth === depth
                        ? 'bg-glow text-void shadow-sm'
                        : 'text-text-muted hover:text-text hover:bg-void-lighter'
                    }
                  `}
                >
                  {depth.charAt(0).toUpperCase() + depth.slice(1)}
                </button>
              ))}
            </div>
            <div className="text-[10px] text-text-dim mt-1.5 text-center">
              {settings.resultDepth === 'focused'
                ? 'Top 10 most relevant results'
                : settings.resultDepth === 'balanced'
                  ? 'Top 20 balanced results'
                  : 'Top 40 comprehensive results'}
            </div>
          </div>

          {/* Temperature Slider */}
          <div className="mb-5">
            <div className="flex justify-between items-center mb-2">
              <label className="text-xs font-medium text-text">
                Response Tone
              </label>
              <span className="text-xs text-text-muted">
                {settings.temperature < 30
                  ? 'Precise'
                  : settings.temperature > 70
                    ? 'Creative'
                    : 'Balanced'}
              </span>
            </div>
            <div className="relative">
              <input
                type="range"
                min="0"
                max="100"
                value={settings.temperature}
                onChange={(e) => handleTemperatureChange(Number(e.target.value))}
                className="query-slider w-full"
              />
              <div className="flex justify-between text-[10px] text-text-dim mt-1">
                <span>Precise</span>
                <span>Creative</span>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-void-surface my-4" />

          {/* Retrieval Settings */}
          <RetrievalSettings
            config={settings.retrieval}
            onChange={handleRetrievalChange}
            disabled={disabled}
            compact
          />

          {/* Reset Button */}
          {hasCustomSettings && (
            <button
              onClick={() => onChange(DEFAULT_QUERY_SETTINGS)}
              className="mt-4 w-full py-2 text-xs text-text-muted hover:text-text
                border border-void-surface hover:border-text-dim rounded-md transition-colors"
            >
              Reset All to Defaults
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default QuerySettingsPanel;
