/**
 * TimingBreakdown Component
 *
 * Reusable collapsible panel for displaying per-stage timing breakdown.
 * Shows progress bars, milliseconds, percentages, and bottleneck identification.
 *
 * Used by: QueryPage, RAG Chat, SQL Chat
 */

import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Timer,
  Database,
  Zap,
  Search,
  FileText,
  Brain,
  Layers,
  Shield,
  Code,
  CheckCircle,
  Clock,
  type LucideIcon
} from 'lucide-react';

export interface TimingStage {
  key: string;
  label: string;
  icon?: LucideIcon;
  color: string;
  isChild?: boolean;
}

interface TimingBreakdownProps {
  /** Total execution time in milliseconds */
  totalTimeMs: number;
  /** Timing values object with stage keys */
  timings: Record<string, number>;
  /** Stage configuration for display */
  stages: TimingStage[];
  /** Optional: Initially expanded state */
  defaultExpanded?: boolean;
  /** Optional: Custom title */
  title?: string;
  /** Optional: Model name used for this response */
  model?: string;
}

// Preset stage configurations for different endpoints
export const QUERY_API_STAGES: TimingStage[] = [
  { key: '1_notebook_lookup_ms', label: 'Notebook Lookup', icon: Database, color: 'bg-blue-500' },
  { key: '2_node_cache_ms', label: 'Node Cache', icon: Database, color: 'bg-blue-400' },
  { key: '3_create_retriever_ms', label: 'Create Retriever', icon: Zap, color: 'bg-yellow-500' },
  { key: '4_chunk_retrieval_ms', label: 'Chunk Retrieval', icon: Search, color: 'bg-green-500' },
  { key: '5_format_sources_ms', label: 'Format Sources', icon: FileText, color: 'bg-green-400' },
  { key: '6_raptor_total_ms', label: 'RAPTOR Total', icon: Layers, color: 'bg-purple-500' },
  { key: '6a_raptor_embedding_ms', label: '↳ Embedding', color: 'bg-purple-400', isChild: true },
  { key: '6b_raptor_lookup_ms', label: '↳ ANN Lookup', color: 'bg-purple-300', isChild: true },
  { key: '7_context_building_ms', label: 'Context Building', icon: FileText, color: 'bg-orange-500' },
  { key: '8_llm_completion_ms', label: 'LLM Completion', icon: Brain, color: 'bg-red-500' },
];

export const RAG_CHAT_STAGES: TimingStage[] = [
  { key: '1_routing_analysis_ms', label: 'Routing Analysis', icon: Layers, color: 'bg-purple-500' },
  { key: '2_notebook_switch_ms', label: 'Notebook Switch', icon: Database, color: 'bg-blue-500' },
  { key: '3_node_cache_ms', label: 'Node Cache', icon: Database, color: 'bg-blue-400' },
  { key: '4_retriever_creation_ms', label: 'Create Retriever', icon: Zap, color: 'bg-yellow-500' },
  { key: '5_chunk_retrieval_ms', label: 'Chunk Retrieval', icon: Search, color: 'bg-green-500' },
  { key: '6_source_formatting_ms', label: 'Format Sources', icon: FileText, color: 'bg-green-400' },
  { key: '6b_query_execution_ms', label: 'Query Execution', icon: Zap, color: 'bg-purple-400' },
  { key: '7_llm_completion_ms', label: 'LLM Completion', icon: Brain, color: 'bg-red-500' },
  { key: '8_response_streaming_ms', label: 'Response Streaming', icon: Clock, color: 'bg-orange-500' },
];

// V2 Chat API stages (stateless fast pattern with conversation memory)
export const V2_CHAT_STAGES: TimingStage[] = [
  { key: '1_notebook_lookup_ms', label: 'Notebook Lookup', icon: Database, color: 'bg-blue-500' },
  { key: '2_load_history_ms', label: 'Load History', icon: Clock, color: 'bg-purple-500' },
  { key: '3_node_cache_ms', label: 'Node Cache', icon: Database, color: 'bg-blue-400' },
  { key: '4_fast_retrieval_ms', label: 'Fast Retrieval', icon: Search, color: 'bg-green-500' },
  { key: '5_raptor_summaries_ms', label: 'RAPTOR Summaries', icon: Layers, color: 'bg-purple-400' },
  { key: '6_context_building_ms', label: 'Context Building', icon: FileText, color: 'bg-orange-500' },
  { key: '7_llm_completion_ms', label: 'LLM Completion', icon: Brain, color: 'bg-red-500' },
  { key: '8_save_history_ms', label: 'Save History', icon: Database, color: 'bg-blue-300' },
];

// V2 Chat streaming stages
export const V2_CHAT_STREAM_STAGES: TimingStage[] = [
  { key: '1_load_history_ms', label: 'Load History', icon: Clock, color: 'bg-purple-500' },
  { key: '2_node_cache_ms', label: 'Node Cache', icon: Database, color: 'bg-blue-400' },
  { key: '3_retrieval_ms', label: 'Retrieval', icon: Search, color: 'bg-green-500' },
  { key: '4_raptor_ms', label: 'RAPTOR', icon: Layers, color: 'bg-purple-400' },
  { key: '5_context_ms', label: 'Context Building', icon: FileText, color: 'bg-orange-500' },
  { key: '6_llm_stream_ms', label: 'LLM Streaming', icon: Brain, color: 'bg-red-500' },
  { key: '7_save_history_ms', label: 'Save History', icon: Database, color: 'bg-blue-300' },
];

export const SQL_CHAT_STAGES: TimingStage[] = [
  { key: '1_input_validation_ms', label: 'Input Validation', icon: Shield, color: 'bg-blue-500' },
  { key: '2_intent_classification_ms', label: 'Intent Classification', icon: Brain, color: 'bg-purple-500' },
  { key: '3_schema_check_ms', label: 'Schema Check', icon: Database, color: 'bg-blue-400' },
  { key: '4_schema_linking_ms', label: 'Schema Linking', icon: Layers, color: 'bg-purple-400' },
  { key: '5_dictionary_context_ms', label: 'Dictionary Context', icon: FileText, color: 'bg-green-500' },
  { key: '6_sql_generation_ms', label: 'SQL Generation', icon: Code, color: 'bg-yellow-500' },
  { key: '7_cost_estimation_ms', label: 'Cost Estimation', icon: Zap, color: 'bg-orange-400' },
  { key: '8_sql_execution_ms', label: 'SQL Execution', icon: Database, color: 'bg-green-400' },
  { key: '9_data_masking_ms', label: 'Data Masking', icon: Shield, color: 'bg-blue-300' },
  { key: '10_confidence_scoring_ms', label: 'Confidence Scoring', icon: CheckCircle, color: 'bg-purple-300' },
  { key: '11_response_generation_ms', label: 'Response Generation', icon: Brain, color: 'bg-red-500' },
];

export function TimingBreakdown({
  totalTimeMs,
  timings,
  stages,
  defaultExpanded = false,
  title = 'Performance Timings',
  model
}: TimingBreakdownProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Find the bottleneck (stage with highest time)
  const bottleneck = stages.reduce(
    (max, stage) => {
      const time = timings[stage.key] || 0;
      return time > max.time ? { key: stage.key, label: stage.label, time } : max;
    },
    { key: '', label: '', time: 0 }
  );

  const bottleneckPct = totalTimeMs > 0 ? (bottleneck.time / totalTimeMs) * 100 : 0;

  return (
    <div className="bg-void-surface rounded-lg border border-void-lighter overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-3 flex items-center justify-between hover:bg-void-lighter transition-colors"
      >
        <span className="font-semibold text-text flex items-center gap-2 text-sm">
          <Timer className="w-4 h-4 text-glow" />
          {title}
        </span>
        <div className="flex items-center gap-3">
          {model && (
            <span className="text-xs px-2 py-0.5 rounded bg-glow/20 text-glow font-medium">
              {model}
            </span>
          )}
          <span className="text-xs text-text-muted">
            {(totalTimeMs / 1000).toFixed(2)}s total
          </span>
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-text-muted" />
          ) : (
            <ChevronRight className="w-4 h-4 text-text-muted" />
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="p-4 border-t border-void-lighter">
          <div className="space-y-2">
            {stages.map(({ key, label, icon: Icon, color, isChild }) => {
              const ms = timings[key] || 0;
              const pct = totalTimeMs > 0 ? (ms / totalTimeMs) * 100 : 0;

              // Skip stages with 0 time unless they have children
              if (ms === 0 && !stages.some(s => s.isChild && s.key.startsWith(key.split('_')[0]))) {
                // Check if this is a parent with children that have values
                const hasChildWithValue = stages.some(
                  s => s.isChild && s.key.startsWith(key.replace('_ms', '').split('_')[0]) && timings[s.key] > 0
                );
                if (!hasChildWithValue && ms === 0) {
                  return null;
                }
              }

              return (
                <div key={key} className={isChild ? 'ml-4' : ''}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className={`flex items-center gap-1.5 ${isChild ? 'text-text-dim' : 'text-text-muted'}`}>
                      {Icon && <Icon className="w-3 h-3" />}
                      {label}
                    </span>
                    <span className="text-text font-mono">
                      {ms.toLocaleString()}ms
                      <span className="text-text-dim ml-1">
                        ({pct.toFixed(1)}%)
                      </span>
                    </span>
                  </div>
                  <div className="h-2 bg-void rounded-full overflow-hidden">
                    <div
                      className={`h-full ${color} transition-all duration-500`}
                      style={{ width: `${Math.max(pct, 0.5)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Summary */}
          <div className="mt-4 pt-3 border-t border-void-lighter space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-text-muted flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Bottleneck:
              </span>
              <span className="text-red-400 font-medium">
                {bottleneck.label} ({bottleneckPct.toFixed(1)}%)
              </span>
            </div>

            {/* Show RAPTOR ANN speed if available */}
            {timings['6b_raptor_lookup_ms'] !== undefined && timings['6b_raptor_lookup_ms'] > 0 && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-text-muted">RAPTOR ANN Speed:</span>
                <span className="text-green-400 font-medium">
                  {timings['6b_raptor_lookup_ms']}ms (O(log n))
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default TimingBreakdown;
