/**
 * Chart Grid Component
 *
 * Displays a grid of charts based on dashboard configuration.
 * Uses CSS-based charts for simplicity (no external charting library required).
 * Can be enhanced with Chart.js or D3 later.
 */

import { useMemo, useCallback } from 'react';
import { useCrossFilter, useAnalytics } from '../../contexts/AnalyticsContext';
import type { ChartConfig, AggregationType } from '../../types/analytics';

interface ChartGridProps {
  className?: string;
}

// Color palette for charts
const CHART_COLORS = [
  'hsl(210, 100%, 60%)',  // Blue
  'hsl(150, 70%, 50%)',   // Green
  'hsl(280, 70%, 60%)',   // Purple
  'hsl(30, 90%, 55%)',    // Orange
  'hsl(350, 80%, 60%)',   // Red
  'hsl(180, 60%, 50%)',   // Cyan
  'hsl(60, 80%, 50%)',    // Yellow
  'hsl(320, 70%, 55%)',   // Pink
];

export function ChartGrid({ className = '' }: ChartGridProps) {
  const { dashboardConfig, filteredData, parsedData } = useAnalytics();

  const chartConfigs = dashboardConfig?.charts || [];
  const data = filteredData || parsedData?.data || [];

  if (chartConfigs.length === 0 || data.length === 0) {
    return null;
  }

  return (
    <div className={`chart-grid ${className}`}>
      {chartConfigs.map((chart) => (
        <ChartCard key={chart.id} config={chart} data={data} />
      ))}
    </div>
  );
}

interface ChartCardProps {
  config: ChartConfig;
  data: Record<string, any>[];
}

function ChartCard({ config, data }: ChartCardProps) {
  const { applyCrossFilter, crossFilterEvent } = useCrossFilter();

  // Aggregate data for the chart (always top 10 + Others for high cardinality)
  const chartData = useMemo(() => {
    return aggregateChartData(data, config);
  }, [data, config]);

  const handleBarClick = useCallback((label: string) => {
    if (config.allowCrossFilter !== false) {
      applyCrossFilter(config.id, config.xAxis, label);
    }
  }, [config, applyCrossFilter]);

  const isFiltering = crossFilterEvent?.sourceChartId === config.id;

  return (
    <div className={`chart-card ${isFiltering ? 'chart-card--filtering' : ''}`}>
      <div className="chart-card__header">
        <h3 className="chart-card__title">{config.title}</h3>
        {config.allowCrossFilter !== false && (
          <span className="chart-card__hint">Click to filter</span>
        )}
      </div>
      <div className="chart-card__content">
        {config.type === 'bar' && (
          <BarChart
            data={chartData}
            onBarClick={handleBarClick}
            activeValue={crossFilterEvent?.filterValue}
          />
        )}
        {config.type === 'pie' && (
          <PieChart
            data={chartData}
            onSliceClick={handleBarClick}
            activeValue={crossFilterEvent?.filterValue}
          />
        )}
        {config.type === 'line' && (
          <LineChart data={chartData} />
        )}
        {(config.type === 'scatter' || config.type === 'area') && (
          <SimpleChart data={chartData} type={config.type} />
        )}
      </div>
    </div>
  );
}

interface ChartDataPoint {
  label: string;
  value: number;
  percent: number;
  color: string;
}

function aggregateChartData(
  data: Record<string, any>[],
  config: ChartConfig
): ChartDataPoint[] {
  const grouped: Record<string, number[]> = {};

  // Group data by x-axis
  data.forEach((row) => {
    const label = String(row[config.xAxis] ?? 'Unknown');
    if (!grouped[label]) {
      grouped[label] = [];
    }

    const value = config.yAxis === 'count' ? 1 : Number(row[config.yAxis]);
    if (!isNaN(value)) {
      grouped[label].push(value);
    }
  });

  // Apply aggregation
  const aggregated = Object.entries(grouped).map(([label, values], index) => ({
    label,
    value: computeAggregation(values, config.aggregation || 'sum'),
    percent: 0,
    color: CHART_COLORS[index % CHART_COLORS.length],
  }));

  // Sort by value descending by default for bar charts (shows top items first)
  aggregated.sort((a, b) => {
    if (config.sortBy === 'label') {
      return config.sortOrder === 'desc'
        ? b.label.localeCompare(a.label)
        : a.label.localeCompare(b.label);
    }
    // Default to descending (highest first) for value-based sorting
    if (config.sortOrder === 'asc') {
      return a.value - b.value; // Ascending: lowest first
    }
    return b.value - a.value; // Descending (default): highest first
  });

  // ALWAYS limit to top 10 + "Others" for bar charts with high cardinality
  // This provides a clean, readable visualization regardless of filter state
  const maxDisplayCategories = 10;
  const actualCardinality = aggregated.length;

  let result: ChartDataPoint[];

  if (actualCardinality <= maxDisplayCategories) {
    // Low cardinality: show all categories
    result = aggregated;
  } else {
    // High cardinality: show top 10 + "Others" with aggregated count
    const topItems = aggregated.slice(0, maxDisplayCategories);
    const restItems = aggregated.slice(maxDisplayCategories);

    // Aggregate the "Others" value
    const othersValue = restItems.reduce((sum, item) => sum + item.value, 0);

    if (othersValue > 0) {
      topItems.push({
        label: `Others (${restItems.length})`,
        value: othersValue,
        percent: 0,
        color: 'hsl(0, 0%, 60%)', // Gray for "Others"
      });
    }

    result = topItems;
  }

  // Calculate percentages based on the total of displayed items
  const total = result.reduce((sum, d) => sum + d.value, 0);
  result.forEach((d) => {
    d.percent = total > 0 ? (d.value / total) * 100 : 0;
  });

  return result;
}

function computeAggregation(values: number[], aggregation: AggregationType): number {
  if (values.length === 0) return 0;

  switch (aggregation) {
    case 'sum':
      return values.reduce((a, b) => a + b, 0);
    case 'avg':
      return values.reduce((a, b) => a + b, 0) / values.length;
    case 'count':
      return values.length;
    case 'min':
      return Math.min(...values);
    case 'max':
      return Math.max(...values);
    case 'median':
      const sorted = [...values].sort((a, b) => a - b);
      const mid = Math.floor(sorted.length / 2);
      return sorted.length % 2 !== 0
        ? sorted[mid]
        : (sorted[mid - 1] + sorted[mid]) / 2;
    default:
      return values.reduce((a, b) => a + b, 0);
  }
}

// Simple Bar Chart (CSS-based)
interface BarChartProps {
  data: ChartDataPoint[];
  onBarClick?: (label: string) => void;
  activeValue?: any;
}

function BarChart({ data, onBarClick, activeValue }: BarChartProps) {
  const maxValue = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="bar-chart">
      {data.map((d) => (
        <div
          key={d.label}
          className={`bar-chart__item ${activeValue === d.label ? 'bar-chart__item--active' : ''}`}
          onClick={() => onBarClick?.(d.label)}
        >
          <div className="bar-chart__label" title={d.label}>
            {d.label.length > 15 ? `${d.label.slice(0, 15)}...` : d.label}
          </div>
          <div className="bar-chart__bar-container">
            <div
              className="bar-chart__bar"
              style={{
                width: `${(d.value / maxValue) * 100}%`,
                backgroundColor: d.color,
              }}
            />
          </div>
          <div className="bar-chart__value">{formatNumber(d.value)}</div>
        </div>
      ))}
    </div>
  );
}

// Simple Pie Chart (CSS-based) with cross-filter support
interface PieChartProps {
  data: ChartDataPoint[];
  onSliceClick?: (label: string) => void;
  activeValue?: any;
}

function PieChart({ data, onSliceClick, activeValue }: PieChartProps) {
  // Create conic gradient for pie chart
  let currentAngle = 0;
  const gradientStops = data.map((d) => {
    const startAngle = currentAngle;
    currentAngle += d.percent * 3.6; // Convert percent to degrees
    return `${d.color} ${startAngle}deg ${currentAngle}deg`;
  }).join(', ');

  return (
    <div className="pie-chart">
      <div
        className="pie-chart__circle"
        style={{ background: `conic-gradient(${gradientStops})` }}
        title="Click legend items to filter"
      />
      <div className="pie-chart__legend">
        {data.slice(0, 6).map((d) => (
          <div
            key={d.label}
            className={`pie-chart__legend-item ${activeValue === d.label ? 'pie-chart__legend-item--active' : ''}`}
            onClick={() => onSliceClick?.(d.label)}
            style={{ cursor: onSliceClick ? 'pointer' : 'default' }}
          >
            <span
              className="pie-chart__legend-color"
              style={{ backgroundColor: d.color }}
            />
            <span className="pie-chart__legend-label" title={d.label}>
              {d.label.length > 12 ? `${d.label.slice(0, 12)}...` : d.label}
            </span>
            <span className="pie-chart__legend-value">{d.percent.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Simple Line Chart (CSS-based)
function LineChart({ data }: { data: ChartDataPoint[] }) {
  const maxValue = Math.max(...data.map((d) => d.value), 1);
  const minValue = Math.min(...data.map((d) => d.value), 0);
  const range = maxValue - minValue || 1;

  // Create SVG path for the line
  const width = 300;
  const height = 150;
  const padding = 20;

  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1 || 1)) * (width - 2 * padding);
    const y = height - padding - ((d.value - minValue) / range) * (height - 2 * padding);
    return `${x},${y}`;
  });

  const pathD = points.length > 0 ? `M ${points.join(' L ')}` : '';

  return (
    <div className="line-chart">
      <svg viewBox={`0 0 ${width} ${height}`} className="line-chart__svg">
        {/* Grid lines */}
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className="line-chart__axis" />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} className="line-chart__axis" />

        {/* Line */}
        <path d={pathD} className="line-chart__line" fill="none" stroke="hsl(210, 100%, 60%)" strokeWidth="2" />

        {/* Points */}
        {data.map((d, i) => {
          const x = padding + (i / (data.length - 1 || 1)) * (width - 2 * padding);
          const y = height - padding - ((d.value - minValue) / range) * (height - 2 * padding);
          return (
            <circle key={i} cx={x} cy={y} r="4" className="line-chart__point" fill="hsl(210, 100%, 60%)" />
          );
        })}
      </svg>
      <div className="line-chart__labels">
        {data.length > 0 && <span>{data[0].label}</span>}
        {data.length > 1 && <span>{data[data.length - 1].label}</span>}
      </div>
    </div>
  );
}

// Fallback for other chart types
function SimpleChart({ data, type }: { data: ChartDataPoint[]; type: string }) {
  return (
    <div className="simple-chart">
      <p className="simple-chart__placeholder">
        {type.charAt(0).toUpperCase() + type.slice(1)} chart
      </p>
      <div className="simple-chart__data">
        {data.slice(0, 5).map((d) => (
          <div key={d.label} className="simple-chart__item">
            <span>{d.label}:</span>
            <strong>{formatNumber(d.value)}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatNumber(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  } else if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toFixed(0);
}

export default ChartGrid;
