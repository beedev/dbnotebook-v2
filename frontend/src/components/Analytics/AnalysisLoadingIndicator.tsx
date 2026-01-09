/**
 * Analysis Loading Indicator Component
 *
 * Shows progress when analysis is running (especially for auto-analysis
 * triggered from SQL Chat where ExcelUploader's progress UI won't show).
 */

import { FileSpreadsheet, BarChart3 } from 'lucide-react';
import type { AnalysisState } from '../../types/analytics';

interface AnalysisLoadingIndicatorProps {
  state: AnalysisState;
  progress: number;
  className?: string;
}

// Map analysis states to user-friendly status messages
const STATUS_MESSAGES: Record<AnalysisState, string> = {
  idle: 'Preparing...',
  uploading: 'Uploading file...',
  parsing: 'Parsing data...',
  profiling: 'Generating profile...',
  analyzing: 'Creating dashboard...',
  complete: 'Analysis complete!',
  error: 'Analysis failed',
};

export function AnalysisLoadingIndicator({
  state,
  progress,
  className = '',
}: AnalysisLoadingIndicatorProps) {
  const isError = state === 'error';
  const statusMessage = STATUS_MESSAGES[state] || 'Processing...';

  return (
    <div className={`analytics-loading-indicator ${className}`}>
      <div className="analytics-loading-indicator__container">
        {/* Animated icon */}
        <div className={`analytics-loading-indicator__icon ${isError ? 'analytics-loading-indicator__icon--error' : ''}`}>
          <FileSpreadsheet size={56} className="analytics-loading-indicator__file-icon" />
          <BarChart3 size={24} className="analytics-loading-indicator__chart-icon" />
        </div>

        {/* Status text */}
        <h2 className="analytics-loading-indicator__title">
          Analyzing Query Results
        </h2>
        <p className={`analytics-loading-indicator__status ${isError ? 'analytics-loading-indicator__status--error' : ''}`}>
          {statusMessage}
        </p>

        {/* Progress bar */}
        {!isError && (
          <div className="analytics-loading-indicator__progress">
            <div className="analytics-loading-indicator__progress-bar">
              <div
                className="analytics-loading-indicator__progress-fill"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="analytics-loading-indicator__progress-text">
              {progress}%
            </span>
          </div>
        )}

        {/* Hint text */}
        <p className="analytics-loading-indicator__hint">
          {isError
            ? 'Please try again or upload a different file'
            : 'This may take a moment for larger datasets'}
        </p>
      </div>
    </div>
  );
}

export default AnalysisLoadingIndicator;
