/**
 * Column Detail Panel Component
 *
 * Expandable panel showing detailed statistics for a column:
 * - Numeric: Mean, Median, Std, Min-Max, Quartiles, Skewness/Kurtosis
 * - Categorical: Top values with bar chart, entropy score
 * - Common: Sample values, null info
 */

import type { ColumnMetadata } from '../../types/analytics';

interface ColumnDetailPanelProps {
  column: ColumnMetadata;
  className?: string;
}

export function ColumnDetailPanel({ column, className = '' }: ColumnDetailPanelProps) {
  const { statistics, categorical, inferredType, nullCount, nullPercent, sampleValues } = column;

  const formatNumber = (num: number | undefined, decimals = 2): string => {
    if (num === undefined || num === null) return 'N/A';
    if (Math.abs(num) >= 1e6) return num.toExponential(2);
    if (Math.abs(num) < 0.01 && num !== 0) return num.toExponential(2);
    return num.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: decimals
    });
  };

  const getDistributionLabel = (skewness: number | undefined): { label: string; color: string } => {
    if (skewness === undefined) return { label: 'Unknown', color: 'gray' };
    if (Math.abs(skewness) < 0.5) return { label: 'Symmetric', color: 'green' };
    if (skewness > 0.5) return { label: 'Right-skewed', color: 'orange' };
    return { label: 'Left-skewed', color: 'blue' };
  };

  const getKurtosisLabel = (kurtosis: number | undefined): { label: string; color: string } => {
    if (kurtosis === undefined) return { label: 'Unknown', color: 'gray' };
    if (Math.abs(kurtosis - 3) < 0.5) return { label: 'Normal', color: 'green' };
    if (kurtosis > 3.5) return { label: 'Heavy-tailed', color: 'red' };
    return { label: 'Light-tailed', color: 'blue' };
  };

  return (
    <div className={`column-detail-panel ${className}`}>
      <div className="column-detail-panel__grid">
        {/* Numeric Statistics */}
        {(inferredType === 'numeric' && statistics) && (
          <div className="column-detail-panel__section">
            <h4 className="column-detail-panel__section-title">Distribution Statistics</h4>

            <div className="stat-grid">
              {/* Central Tendency */}
              <div className="stat-group">
                <h5 className="stat-group__title">Central Tendency</h5>
                <div className="stat-row">
                  <span className="stat-label">Mean</span>
                  <span className="stat-value">{formatNumber(statistics.mean)}</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">Median</span>
                  <span className="stat-value">{formatNumber(statistics.median)}</span>
                </div>
              </div>

              {/* Spread */}
              <div className="stat-group">
                <h5 className="stat-group__title">Spread</h5>
                <div className="stat-row">
                  <span className="stat-label">Std Dev</span>
                  <span className="stat-value">{formatNumber(statistics.std)}</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">IQR</span>
                  <span className="stat-value">{formatNumber(statistics.iqr)}</span>
                </div>
              </div>

              {/* Range */}
              <div className="stat-group">
                <h5 className="stat-group__title">Range</h5>
                <div className="stat-row">
                  <span className="stat-label">Min</span>
                  <span className="stat-value">{formatNumber(statistics.min)}</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">Max</span>
                  <span className="stat-value">{formatNumber(statistics.max)}</span>
                </div>
              </div>

              {/* Quartiles */}
              <div className="stat-group">
                <h5 className="stat-group__title">Quartiles</h5>
                <div className="stat-row">
                  <span className="stat-label">Q1 (25%)</span>
                  <span className="stat-value">
                    {formatNumber(statistics.quartiles?.[0])}
                  </span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">Q2 (50%)</span>
                  <span className="stat-value">
                    {formatNumber(statistics.quartiles?.[1])}
                  </span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">Q3 (75%)</span>
                  <span className="stat-value">
                    {formatNumber(statistics.quartiles?.[2])}
                  </span>
                </div>
              </div>
            </div>

            {/* Distribution Shape */}
            <div className="distribution-shape">
              <h5 className="stat-group__title">Distribution Shape</h5>
              <div className="shape-indicators">
                <div className="shape-indicator">
                  <span className="shape-indicator__label">Skewness</span>
                  <span className="shape-indicator__value">{formatNumber(statistics.skewness, 3)}</span>
                  <span
                    className={`shape-indicator__badge shape-indicator__badge--${getDistributionLabel(statistics.skewness).color}`}
                  >
                    {getDistributionLabel(statistics.skewness).label}
                  </span>
                </div>
                <div className="shape-indicator">
                  <span className="shape-indicator__label">Kurtosis</span>
                  <span className="shape-indicator__value">{formatNumber(statistics.kurtosis, 3)}</span>
                  <span
                    className={`shape-indicator__badge shape-indicator__badge--${getKurtosisLabel(statistics.kurtosis).color}`}
                  >
                    {getKurtosisLabel(statistics.kurtosis).label}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Categorical Statistics */}
        {(inferredType === 'categorical' && categorical) && (
          <div className="column-detail-panel__section">
            <h4 className="column-detail-panel__section-title">Value Distribution</h4>

            <div className="categorical-stats">
              <div className="categorical-stats__header">
                <span className="categorical-stats__unique">
                  {categorical.uniqueCount?.toLocaleString() || 0} unique values
                </span>
                {categorical.entropy !== undefined && (
                  <span className="categorical-stats__entropy" title="Entropy: measure of randomness/uniformity (higher = more uniform)">
                    Entropy: {categorical.entropy.toFixed(3)}
                  </span>
                )}
              </div>

              {categorical.topValues && categorical.topValues.length > 0 && (
                <div className="top-values">
                  <h5 className="top-values__title">Top Values</h5>
                  <div className="top-values__list">
                    {categorical.topValues.slice(0, 10).map((item, index) => (
                      <div key={index} className="top-value-row">
                        <span className="top-value-row__rank">#{index + 1}</span>
                        <span className="top-value-row__value" title={item.value}>
                          {item.value.length > 25 ? `${item.value.slice(0, 25)}...` : item.value}
                        </span>
                        <div className="top-value-row__bar-container">
                          <div
                            className="top-value-row__bar"
                            style={{ width: `${Math.min(item.percent, 100)}%` }}
                          />
                        </div>
                        <span className="top-value-row__count">
                          {item.count.toLocaleString()}
                        </span>
                        <span className="top-value-row__percent">
                          {item.percent.toFixed(1)}%
                        </span>
                      </div>
                    ))}
                  </div>
                  {(categorical.topValues.length > 10) && (
                    <span className="top-values__more">
                      +{categorical.topValues.length - 10} more values
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Missing Data */}
        <div className="column-detail-panel__section column-detail-panel__section--compact">
          <h4 className="column-detail-panel__section-title">Data Quality</h4>
          <div className="quality-stats">
            <div className="quality-stat">
              <span className="quality-stat__label">Missing Values</span>
              <span className="quality-stat__value">
                {nullCount?.toLocaleString() || 0}
              </span>
            </div>
            <div className="quality-stat">
              <span className="quality-stat__label">Missing %</span>
              <span className={`quality-stat__value ${(nullPercent || 0) > 10 ? 'quality-stat__value--warning' : ''}`}>
                {(nullPercent || 0).toFixed(2)}%
              </span>
            </div>
            <div className="quality-stat">
              <span className="quality-stat__label">Completeness</span>
              <span className="quality-stat__value">
                {(100 - (nullPercent || 0)).toFixed(2)}%
              </span>
            </div>
          </div>
        </div>

        {/* Sample Values */}
        {sampleValues && sampleValues.length > 0 && (
          <div className="column-detail-panel__section column-detail-panel__section--compact">
            <h4 className="column-detail-panel__section-title">Sample Values</h4>
            <div className="sample-values-grid">
              {sampleValues.slice(0, 5).map((val, index) => (
                <span key={index} className="sample-value-chip">
                  {String(val).slice(0, 50)}
                  {String(val).length > 50 ? '...' : ''}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ColumnDetailPanel;
