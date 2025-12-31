/**
 * Requirements Modal Component
 *
 * Modal shown after file upload, before analysis.
 * Allows user to optionally provide initial requirements for dashboard generation.
 */

import { useState, useCallback } from 'react';
import { X, Sparkles, Lightbulb, ArrowRight, SkipForward } from 'lucide-react';

interface RequirementsModalProps {
  isOpen: boolean;
  fileName: string;
  onSubmit: (requirements: string) => void;
  onSkip: () => void;
  onClose: () => void;
}

// Example suggestions for common analytics scenarios
const EXAMPLE_SUGGESTIONS = [
  "Show me monthly trends and top performers",
  "I want to compare regions and identify outliers",
  "Focus on customer metrics and revenue analysis",
  "Display key financial KPIs with category breakdowns",
  "Analyze sales performance by product and time period",
];

export function RequirementsModal({
  isOpen,
  fileName,
  onSubmit,
  onSkip,
  onClose,
}: RequirementsModalProps) {
  const [requirements, setRequirements] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = useCallback(async () => {
    if (requirements.trim()) {
      setIsSubmitting(true);
      await onSubmit(requirements.trim());
      setIsSubmitting(false);
    }
  }, [requirements, onSubmit]);

  const handleSkip = useCallback(() => {
    setRequirements('');
    onSkip();
  }, [onSkip]);

  const handleSuggestionClick = useCallback((suggestion: string) => {
    setRequirements(suggestion);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.metaKey && requirements.trim()) {
      handleSubmit();
    }
  }, [requirements, handleSubmit]);

  if (!isOpen) return null;

  return (
    <div className="requirements-modal__overlay" onClick={onClose}>
      <div
        className="requirements-modal"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="requirements-modal__header">
          <div className="requirements-modal__title-section">
            <Sparkles size={20} className="requirements-modal__icon" />
            <h2 className="requirements-modal__title">
              Customize Your Dashboard
            </h2>
          </div>
          <button
            className="requirements-modal__close"
            onClick={onClose}
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="requirements-modal__content">
          <p className="requirements-modal__description">
            Tell us what you'd like to see in your dashboard for <strong>{fileName}</strong>.
            This helps the AI generate more relevant visualizations and insights.
          </p>

          {/* Requirements Input */}
          <div className="requirements-modal__input-section">
            <label className="requirements-modal__label">
              What would you like to analyze?
            </label>
            <textarea
              className="requirements-modal__textarea"
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g., Show me sales trends by region, highlight top customers, and display monthly revenue patterns..."
              rows={4}
              autoFocus
            />
            <span className="requirements-modal__hint">
              Tip: Be specific about the metrics, dimensions, and visualizations you need
            </span>
          </div>

          {/* Suggestions */}
          <div className="requirements-modal__suggestions">
            <div className="requirements-modal__suggestions-header">
              <Lightbulb size={14} />
              <span>Example requests:</span>
            </div>
            <div className="requirements-modal__suggestion-list">
              {EXAMPLE_SUGGESTIONS.map((suggestion, index) => (
                <button
                  key={index}
                  className="requirements-modal__suggestion"
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="requirements-modal__footer">
          <button
            className="requirements-modal__btn requirements-modal__btn--skip"
            onClick={handleSkip}
            disabled={isSubmitting}
          >
            <SkipForward size={16} />
            <span>Skip & Auto-Generate</span>
          </button>
          <button
            className="requirements-modal__btn requirements-modal__btn--submit"
            onClick={handleSubmit}
            disabled={!requirements.trim() || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="requirements-modal__spinner" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <span>Generate Dashboard</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default RequirementsModal;
