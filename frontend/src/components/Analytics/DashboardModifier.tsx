/**
 * Dashboard Modifier Component
 *
 * NLP-driven dashboard modification interface.
 * Allows users to modify the dashboard via natural language instructions.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  Wand2,
  Undo2,
  Redo2,
  Send,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Check,
} from 'lucide-react';

interface DashboardModifierProps {
  onModify: (instruction: string) => Promise<boolean>;
  onUndo: () => Promise<boolean>;
  onRedo: () => Promise<boolean>;
  canUndo: boolean;
  canRedo: boolean;
  isLoading: boolean;
  lastChanges: string[];
  className?: string;
}

// Example modification prompts
const EXAMPLE_PROMPTS = [
  { label: 'Add chart', prompt: 'Add a pie chart showing distribution by category' },
  { label: 'Add KPI', prompt: 'Add a KPI card for average value' },
  { label: 'Remove filter', prompt: 'Remove all filters' },
  { label: 'Change chart type', prompt: 'Change the bar chart to a line chart' },
  { label: 'Add filter', prompt: 'Add a date range filter' },
  { label: 'Customize colors', prompt: 'Use blue color theme for all charts' },
];

export function DashboardModifier({
  onModify,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  isLoading,
  lastChanges,
  className = '',
}: DashboardModifierProps) {
  const [instruction, setInstruction] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);
  const [showExamples, setShowExamples] = useState(false);
  const [recentSuccess, setRecentSuccess] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [instruction]);

  // Show success indicator briefly after changes
  useEffect(() => {
    if (lastChanges.length > 0 && !lastChanges.includes('Undid last modification') && !lastChanges.includes('Redid modification')) {
      setRecentSuccess(true);
      const timer = setTimeout(() => setRecentSuccess(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [lastChanges]);

  const handleSubmit = useCallback(async () => {
    if (!instruction.trim() || isLoading) return;

    try {
      await onModify(instruction.trim());
      setInstruction('');
      setShowExamples(false);
    } catch (error) {
      console.error('Modification failed:', error);
    }
  }, [instruction, isLoading, onModify]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  const handleExampleClick = useCallback((prompt: string) => {
    setInstruction(prompt);
    setShowExamples(false);
    textareaRef.current?.focus();
  }, []);

  return (
    <div className={`dashboard-modifier ${className}`}>
      {/* Header */}
      <div
        className="dashboard-modifier__header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="dashboard-modifier__title">
          <Wand2 size={16} />
          <span>AI Dashboard Assistant</span>
          {recentSuccess && (
            <span className="dashboard-modifier__success-badge">
              <Check size={12} />
              <span>Updated</span>
            </span>
          )}
        </div>
        <div className="dashboard-modifier__header-actions">
          {/* Undo/Redo buttons in header */}
          <button
            className="dashboard-modifier__history-btn"
            onClick={(e) => {
              e.stopPropagation();
              onUndo();
            }}
            disabled={!canUndo || isLoading}
            title="Undo last change"
          >
            <Undo2 size={14} />
          </button>
          <button
            className="dashboard-modifier__history-btn"
            onClick={(e) => {
              e.stopPropagation();
              onRedo();
            }}
            disabled={!canRedo || isLoading}
            title="Redo"
          >
            <Redo2 size={14} />
          </button>
          <button className="dashboard-modifier__expand-btn">
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {/* Expandable content */}
      {isExpanded && (
        <div className="dashboard-modifier__content">
          {/* Last changes indicator */}
          {lastChanges.length > 0 && (
            <div className="dashboard-modifier__changes">
              <span className="dashboard-modifier__changes-label">Last changes:</span>
              <ul className="dashboard-modifier__changes-list">
                {lastChanges.slice(0, 3).map((change, i) => (
                  <li key={i}>{change}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Input section */}
          <div className="dashboard-modifier__input-section">
            <div className="dashboard-modifier__input-wrapper">
              <textarea
                ref={textareaRef}
                className="dashboard-modifier__textarea"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Tell me how to modify the dashboard..."
                rows={1}
                disabled={isLoading}
              />
              <button
                className="dashboard-modifier__submit-btn"
                onClick={handleSubmit}
                disabled={!instruction.trim() || isLoading}
                title="Apply changes (Cmd+Enter)"
              >
                {isLoading ? (
                  <span className="dashboard-modifier__spinner" />
                ) : (
                  <Send size={16} />
                )}
              </button>
            </div>

            {/* Examples toggle */}
            <button
              className="dashboard-modifier__examples-toggle"
              onClick={() => setShowExamples(!showExamples)}
            >
              <Sparkles size={12} />
              <span>{showExamples ? 'Hide examples' : 'Show examples'}</span>
            </button>
          </div>

          {/* Example prompts */}
          {showExamples && (
            <div className="dashboard-modifier__examples">
              {EXAMPLE_PROMPTS.map((example, i) => (
                <button
                  key={i}
                  className="dashboard-modifier__example"
                  onClick={() => handleExampleClick(example.prompt)}
                >
                  <span className="dashboard-modifier__example-label">
                    {example.label}
                  </span>
                  <span className="dashboard-modifier__example-prompt">
                    {example.prompt}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Loading overlay */}
          {isLoading && (
            <div className="dashboard-modifier__loading">
              <div className="dashboard-modifier__loading-content">
                <span className="dashboard-modifier__loading-spinner" />
                <span>Analyzing and modifying dashboard...</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DashboardModifier;
