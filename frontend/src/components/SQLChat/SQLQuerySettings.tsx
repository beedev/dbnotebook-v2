/**
 * SQL Query Settings Component
 *
 * Settings panel for SQL Chat query configuration:
 * - Few-shot reranker: enable/disable and model selection
 * - Top-K: number of similar SQL examples to use
 * - Hybrid search: BM25 + vector combination
 */

import { useState, useCallback } from 'react';
import { ChevronDown, ChevronUp, Settings2, ToggleLeft, ToggleRight } from 'lucide-react';

export interface SQLQueryConfig {
  rerankerEnabled: boolean;
  rerankerModel: string;  // Supports local (xsmall, base, large) and groq:* models
  topK: number;
  hybridEnabled: boolean;
}

export const DEFAULT_SQL_QUERY_CONFIG: SQLQueryConfig = {
  rerankerEnabled: true,
  rerankerModel: 'base',
  topK: 5,
  hybridEnabled: true,
};

interface SQLQuerySettingsProps {
  config: SQLQueryConfig;
  onChange: (config: SQLQueryConfig) => void;
  disabled?: boolean;
}

export function SQLQuerySettings({
  config,
  onChange,
  disabled = false,
}: SQLQuerySettingsProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleRerankerToggle = useCallback(() => {
    onChange({ ...config, rerankerEnabled: !config.rerankerEnabled });
  }, [config, onChange]);

  const handleRerankerModelChange = useCallback(
    (model: SQLQueryConfig['rerankerModel']) => {
      onChange({ ...config, rerankerModel: model });
    },
    [config, onChange]
  );

  const handleTopKChange = useCallback(
    (value: number) => {
      onChange({ ...config, topK: Math.max(1, Math.min(20, value)) });
    },
    [config, onChange]
  );

  const handleHybridToggle = useCallback(() => {
    onChange({ ...config, hybridEnabled: !config.hybridEnabled });
  }, [config, onChange]);

  const hasCustomSettings =
    config.rerankerEnabled !== DEFAULT_SQL_QUERY_CONFIG.rerankerEnabled ||
    config.rerankerModel !== DEFAULT_SQL_QUERY_CONFIG.rerankerModel ||
    config.topK !== DEFAULT_SQL_QUERY_CONFIG.topK ||
    config.hybridEnabled !== DEFAULT_SQL_QUERY_CONFIG.hybridEnabled;

  return (
    <div className="px-4 pb-3">
      {/* Toggle Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        disabled={disabled}
        className={`
          flex items-center gap-2 text-xs font-medium transition-colors
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:text-cyan-400 cursor-pointer'}
          ${hasCustomSettings ? 'text-cyan-400' : 'text-slate-400'}
        `}
      >
        <Settings2 size={14} />
        <span>Query Settings</span>
        {hasCustomSettings && (
          <span className="px-1.5 py-0.5 bg-cyan-500/20 text-cyan-400 rounded text-[10px]">
            Custom
          </span>
        )}
        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {/* Expanded Panel */}
      {isExpanded && (
        <div
          className={`
            mt-3 p-4 rounded-lg border border-slate-700 bg-slate-800/50
            ${disabled ? 'opacity-50 pointer-events-none' : ''}
          `}
        >
          {/* Hybrid Search Toggle */}
          <div className="flex items-center justify-between mb-4">
            <div>
              <span className="text-xs font-medium text-white">Hybrid Search</span>
              <p className="text-[10px] text-slate-400 mt-0.5">
                Combine keyword + semantic search for SQL examples
              </p>
            </div>
            <button
              onClick={handleHybridToggle}
              disabled={disabled}
              className="text-slate-400 hover:text-white transition-colors"
            >
              {config.hybridEnabled ? (
                <ToggleRight size={24} className="text-cyan-400" />
              ) : (
                <ToggleLeft size={24} />
              )}
            </button>
          </div>

          {/* Reranker Toggle */}
          <div className="flex items-center justify-between mb-4">
            <div>
              <span className="text-xs font-medium text-white">Reranker</span>
              <p className="text-[10px] text-slate-400 mt-0.5">
                Re-rank similar SQL examples for better accuracy
              </p>
            </div>
            <button
              onClick={handleRerankerToggle}
              disabled={disabled}
              className="text-slate-400 hover:text-white transition-colors"
            >
              {config.rerankerEnabled ? (
                <ToggleRight size={24} className="text-cyan-400" />
              ) : (
                <ToggleLeft size={24} />
              )}
            </button>
          </div>

          {/* Reranker Model Selector (shown when reranker enabled) */}
          {config.rerankerEnabled && (
            <div className="mb-4 pl-4 border-l-2 border-slate-700">
              <label className="text-xs font-medium text-white block mb-2">
                Reranker Model
              </label>
              <div className="flex gap-1 p-1 bg-slate-900/50 rounded-lg">
                {(['xsmall', 'base', 'large'] as const).map((model) => (
                  <button
                    key={model}
                    onClick={() => handleRerankerModelChange(model)}
                    className={`
                      flex-1 py-1.5 px-2 text-[10px] font-medium rounded transition-all
                      ${
                        config.rerankerModel === model
                          ? 'bg-cyan-600 text-white'
                          : 'text-slate-400 hover:text-white hover:bg-slate-700'
                      }
                    `}
                  >
                    {model.charAt(0).toUpperCase() + model.slice(1)}
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-slate-500 mt-1">
                {config.rerankerModel === 'xsmall'
                  ? 'Fastest, good for simple queries'
                  : config.rerankerModel === 'base'
                    ? 'Balanced speed and accuracy'
                    : 'Most accurate, slower'}
              </p>
            </div>
          )}

          {/* Top-K Slider */}
          <div className="mb-4">
            <div className="flex justify-between items-center mb-2">
              <label className="text-xs font-medium text-white">
                Few-Shot Examples
              </label>
              <span className="text-xs text-cyan-400 font-mono">{config.topK}</span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              value={config.topK}
              onChange={(e) => handleTopKChange(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer
                [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3
                [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full
                [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:cursor-pointer
                [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-slate-900"
            />
            <div className="flex justify-between text-[10px] text-slate-500 mt-1">
              <span>1</span>
              <span>10</span>
            </div>
            <p className="text-[10px] text-slate-500 mt-1">
              Number of similar SQL examples to use for query generation
            </p>
          </div>

          {/* Reset Button */}
          {hasCustomSettings && (
            <button
              onClick={() => onChange(DEFAULT_SQL_QUERY_CONFIG)}
              className="w-full py-2 text-xs text-slate-400 hover:text-white
                border border-slate-700 hover:border-slate-500 rounded-md transition-colors"
            >
              Reset to Defaults
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default SQLQuerySettings;
