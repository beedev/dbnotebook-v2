/**
 * KPI Card Grid Component
 *
 * Displays key performance indicator cards with
 * computed values from filtered data.
 */

import { useMemo } from 'react';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Users,
  BarChart3,
  Activity,
  Target,
  Percent,
} from 'lucide-react';
import { useAnalytics } from '../../contexts/AnalyticsContext';
import type { KPIConfig, AggregationType } from '../../types/analytics';

interface KPICardGridProps {
  className?: string;
}

// Icon mapping
const ICON_MAP: Record<string, React.FC<{ size?: number; className?: string }>> = {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Users,
  BarChart: BarChart3,
  BarChart3,
  Activity,
  Target,
  Percent,
};

// Color mapping for Tailwind classes
const COLOR_MAP: Record<string, string> = {
  blue: 'kpi-card--blue',
  green: 'kpi-card--green',
  red: 'kpi-card--red',
  purple: 'kpi-card--purple',
  orange: 'kpi-card--orange',
};

export function KPICardGrid({ className = '' }: KPICardGridProps) {
  const { dashboardConfig, filteredData, parsedData } = useAnalytics();

  const kpiConfigs = dashboardConfig?.kpis || [];
  const data = filteredData || parsedData?.data || [];

  // Compute KPI values
  const kpiValues = useMemo(() => {
    if (!data || data.length === 0) return {};

    const values: Record<string, number> = {};

    kpiConfigs.forEach((kpi) => {
      values[kpi.id] = computeAggregation(data, kpi.metric, kpi.aggregation);
    });

    return values;
  }, [data, kpiConfigs]);

  if (kpiConfigs.length === 0) {
    return null;
  }

  return (
    <div className={`kpi-grid ${className}`}>
      {kpiConfigs.map((kpi) => (
        <KPICard
          key={kpi.id}
          config={kpi}
          value={kpiValues[kpi.id] ?? 0}
        />
      ))}
    </div>
  );
}

interface KPICardProps {
  config: KPIConfig;
  value: number;
}

function KPICard({ config, value }: KPICardProps) {
  const Icon = ICON_MAP[config.icon || 'BarChart'] || BarChart3;
  const colorClass = COLOR_MAP[config.color || 'blue'] || COLOR_MAP.blue;

  const formattedValue = formatValue(value, config.format, config.decimalPlaces, config.prefix, config.suffix);

  return (
    <div className={`kpi-card ${colorClass}`}>
      <div className="kpi-card__header">
        <span className="kpi-card__title">{config.title}</span>
        <div className="kpi-card__icon">
          <Icon size={20} />
        </div>
      </div>
      <div className="kpi-card__value">{formattedValue}</div>
      <div className="kpi-card__metric">
        {config.aggregation} of {config.metric}
      </div>
    </div>
  );
}

// Compute aggregation value
function computeAggregation(
  data: Record<string, any>[],
  column: string,
  aggregation: AggregationType
): number {
  const values = data
    .map((row) => Number(row[column]))
    .filter((v) => !isNaN(v));

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
      return 0;
  }
}

// Format value for display
function formatValue(
  value: number,
  format: 'number' | 'currency' | 'percentage',
  decimalPlaces = 0,
  prefix = '',
  suffix = ''
): string {
  let formatted: string;

  switch (format) {
    case 'currency':
      formatted = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: decimalPlaces,
        maximumFractionDigits: decimalPlaces,
      }).format(value);
      break;
    case 'percentage':
      formatted = `${value.toFixed(decimalPlaces)}%`;
      break;
    default:
      if (value >= 1000000) {
        formatted = `${(value / 1000000).toFixed(1)}M`;
      } else if (value >= 1000) {
        formatted = `${(value / 1000).toFixed(1)}K`;
      } else {
        formatted = value.toFixed(decimalPlaces);
      }
  }

  return `${prefix}${formatted}${suffix}`;
}

export default KPICardGrid;
