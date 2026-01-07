/**
 * SQL Preview Component
 *
 * Displays generated SQL with:
 * - Syntax highlighting
 * - Copy to clipboard
 * - Collapsible view
 * - Confidence indicator
 */

import { useState, type ReactNode } from 'react';
import {
  Code,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import type { ConfidenceScore, IntentClassification } from '../../types/sqlChat';

interface SQLPreviewProps {
  sql: string;
  intent?: IntentClassification;
  confidence?: ConfidenceScore;
  isExpanded?: boolean;
  onToggle?: () => void;
}

const INTENT_LABELS: Record<string, string> = {
  lookup: 'Data Lookup',
  aggregation: 'Aggregation',
  comparison: 'Comparison',
  trend: 'Trend Analysis',
  top_k: 'Top/Bottom N',
  unknown: 'General Query',
};

const CONFIDENCE_COLORS = {
  high: 'text-green-400 bg-green-900/30 border-green-800',
  medium: 'text-yellow-400 bg-yellow-900/30 border-yellow-800',
  low: 'text-red-400 bg-red-900/30 border-red-800',
};

// Basic SQL keyword highlighting
function highlightSQL(sql: string): ReactNode {
  const keywords = [
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
    'ON', 'AND', 'OR', 'NOT', 'IN', 'IS', 'NULL', 'LIKE', 'BETWEEN',
    'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET', 'AS', 'DISTINCT',
    'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
    'ASC', 'DESC', 'UNION', 'ALL', 'EXISTS', 'ANY', 'SOME',
  ];

  // Create regex pattern for keywords (case insensitive, whole words)
  const pattern = new RegExp(
    `\\b(${keywords.join('|')})\\b`,
    'gi'
  );

  // Split by keywords while keeping them
  const parts = sql.split(pattern);

  return (
    <>
      {parts.map((part, i) => {
        const isKeyword = keywords.some(
          (kw) => kw.toLowerCase() === part.toLowerCase()
        );

        if (isKeyword) {
          return (
            <span key={i} className="text-cyan-400 font-medium">
              {part.toUpperCase()}
            </span>
          );
        }

        // Highlight strings
        if (part.match(/^'[^']*'$/)) {
          return (
            <span key={i} className="text-green-400">
              {part}
            </span>
          );
        }

        // Highlight numbers
        if (part.match(/^\d+$/)) {
          return (
            <span key={i} className="text-orange-400">
              {part}
            </span>
          );
        }

        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

export function SQLPreview({
  sql,
  intent,
  confidence,
  isExpanded: controlledExpanded,
  onToggle,
}: SQLPreviewProps) {
  const [internalExpanded, setInternalExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  const isExpanded = controlledExpanded ?? internalExpanded;
  const handleToggle = onToggle ?? (() => setInternalExpanded(!internalExpanded));

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-800/50">
        <button
          onClick={handleToggle}
          className="flex items-center gap-2 text-slate-300 hover:text-white transition-colors"
        >
          <Code className="w-4 h-4" />
          <span className="text-sm font-medium">Generated SQL</span>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>

        <div className="flex items-center gap-2">
          {/* Intent badge */}
          {intent && (
            <span className="px-2 py-0.5 text-xs rounded bg-slate-700 text-slate-300">
              {INTENT_LABELS[intent.intent] || intent.intent}
            </span>
          )}

          {/* Confidence badge */}
          {confidence && (
            <span
              className={`flex items-center gap-1 px-2 py-0.5 text-xs rounded border ${
                CONFIDENCE_COLORS[confidence.level]
              }`}
            >
              {confidence.level === 'high' ? (
                <CheckCircle className="w-3 h-3" />
              ) : confidence.level === 'low' ? (
                <AlertCircle className="w-3 h-3" />
              ) : null}
              {Math.round(confidence.score * 100)}% confidence
            </span>
          )}

          {/* Copy button */}
          <button
            onClick={handleCopy}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
            title="Copy SQL"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-400" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* SQL Content */}
      {isExpanded && (
        <div className="p-3 bg-slate-900/50 overflow-x-auto">
          <pre className="text-sm font-mono text-slate-300 whitespace-pre-wrap">
            {highlightSQL(sql)}
          </pre>
        </div>
      )}

      {/* Confidence factors (collapsed by default) */}
      {isExpanded && confidence && confidence.factors && (
        <div className="px-3 py-2 bg-slate-800/30 border-t border-slate-700 text-xs text-slate-500">
          <details>
            <summary className="cursor-pointer hover:text-slate-400">
              Confidence factors
            </summary>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <div>Table relevance: {Math.round(confidence.factors.tableRelevance * 100)}%</div>
              <div>Few-shot match: {Math.round(confidence.factors.fewShotSimilarity * 100)}%</div>
              <div>Retry penalty: {confidence.factors.retryPenalty}x</div>
              <div>Column overlap: {Math.round(confidence.factors.columnOverlap * 100)}%</div>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
