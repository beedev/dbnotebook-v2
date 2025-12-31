/**
 * Filter Bar Component
 *
 * Renders dynamic filter controls based on dashboard configuration.
 * Supports categorical, range, and date filters.
 */

import { useCallback } from 'react';
import { Filter, X, RefreshCw } from 'lucide-react';
import { useAnalytics, useCrossFilter } from '../../contexts/AnalyticsContext';
import type { FilterConfig } from '../../types/analytics';

interface FilterBarProps {
  className?: string;
}

export function FilterBar({ className = '' }: FilterBarProps) {
  const { dashboardConfig, filters, updateFilter, clearFilters, parsedData } = useAnalytics();
  const { crossFilterEvent, clearCrossFilter, isFiltering: hasCrossFilter } = useCrossFilter();

  const filterConfigs = dashboardConfig?.filters || [];

  // Get unique values for categorical filters from data
  const getUniqueValues = useCallback((column: string): string[] => {
    if (!parsedData?.data) return [];

    const values = new Set<string>();
    parsedData.data.forEach((row) => {
      if (row[column] !== null && row[column] !== undefined) {
        values.add(String(row[column]));
      }
    });

    return Array.from(values).sort();
  }, [parsedData]);

  // Get min/max for range filters
  const getRange = useCallback((column: string): [number, number] => {
    if (!parsedData?.data) return [0, 100];

    let min = Infinity;
    let max = -Infinity;

    parsedData.data.forEach((row) => {
      const val = Number(row[column]);
      if (!isNaN(val)) {
        if (val < min) min = val;
        if (val > max) max = val;
      }
    });

    return [min === Infinity ? 0 : min, max === -Infinity ? 100 : max];
  }, [parsedData]);

  const hasActiveFilters = Object.keys(filters).length > 0 || hasCrossFilter;

  const handleClearAll = useCallback(() => {
    clearFilters();
    clearCrossFilter();
  }, [clearFilters, clearCrossFilter]);

  if (filterConfigs.length === 0) {
    return null;
  }

  return (
    <div className={`filter-bar ${className}`}>
      <div className="filter-bar__header">
        <div className="filter-bar__title">
          <Filter size={16} />
          <span>Filters</span>
        </div>
        {hasActiveFilters && (
          <button
            onClick={handleClearAll}
            className="filter-bar__clear-btn"
            title="Clear all filters"
          >
            <RefreshCw size={14} />
            <span>Reset</span>
          </button>
        )}
      </div>

      <div className="filter-bar__controls">
        {filterConfigs.map((config) => (
          <FilterControl
            key={config.id}
            config={config}
            value={filters[config.id]?.value}
            onChange={(value) => updateFilter(config.id, { type: config.type, value })}
            getUniqueValues={getUniqueValues}
            getRange={getRange}
          />
        ))}
      </div>

      {hasCrossFilter && crossFilterEvent && (
        <div className="filter-bar__cross-filter">
          <span className="filter-bar__cross-filter-label">
            Filtered by: <strong>{crossFilterEvent.filterColumn}</strong> = {String(crossFilterEvent.filterValue)}
          </span>
          <button
            onClick={clearCrossFilter}
            className="filter-bar__cross-filter-clear"
            title="Clear cross-filter"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}

interface FilterControlProps {
  config: FilterConfig;
  value: any;
  onChange: (value: any) => void;
  getUniqueValues: (column: string) => string[];
  getRange: (column: string) => [number, number];
}

function FilterControl({
  config,
  value,
  onChange,
  getUniqueValues,
  getRange,
}: FilterControlProps) {
  switch (config.type) {
    case 'categorical':
      return (
        <CategoricalFilter
          config={config}
          value={value}
          onChange={onChange}
          options={config.options || getUniqueValues(config.column)}
        />
      );
    case 'range':
      return (
        <RangeFilter
          config={config}
          value={value}
          onChange={onChange}
          range={getRange(config.column)}
        />
      );
    case 'date':
      return (
        <DateFilter
          config={config}
          value={value}
          onChange={onChange}
        />
      );
    default:
      return null;
  }
}

interface CategoricalFilterProps {
  config: FilterConfig;
  value: string[] | undefined;
  onChange: (value: string[]) => void;
  options: string[];
}

function CategoricalFilter({ config, value, onChange, options }: CategoricalFilterProps) {
  const selectedValues = value || [];

  const handleToggle = useCallback((option: string) => {
    if (selectedValues.includes(option)) {
      onChange(selectedValues.filter((v) => v !== option));
    } else {
      onChange([...selectedValues, option]);
    }
  }, [selectedValues, onChange]);

  const handleSelectAll = useCallback(() => {
    onChange(options);
  }, [options, onChange]);

  const handleClear = useCallback(() => {
    onChange([]);
  }, [onChange]);

  return (
    <div className="filter-control filter-control--categorical">
      <label className="filter-control__label">{config.label}</label>
      <div className="filter-control__actions">
        <button onClick={handleSelectAll} className="filter-control__action-btn">All</button>
        <button onClick={handleClear} className="filter-control__action-btn">None</button>
      </div>
      <div className="filter-control__options">
        {options.slice(0, 10).map((option) => (
          <label key={option} className="filter-control__option">
            <input
              type="checkbox"
              checked={selectedValues.includes(option)}
              onChange={() => handleToggle(option)}
            />
            <span className="filter-control__option-text">{option}</span>
          </label>
        ))}
        {options.length > 10 && (
          <span className="filter-control__more">+{options.length - 10} more</span>
        )}
      </div>
    </div>
  );
}

interface RangeFilterProps {
  config: FilterConfig;
  value: [number, number] | undefined;
  onChange: (value: [number, number]) => void;
  range: [number, number];
}

function RangeFilter({ config, value, onChange, range }: RangeFilterProps) {
  const [min, max] = range;
  const currentMin = value?.[0] ?? min;
  const currentMax = value?.[1] ?? max;

  return (
    <div className="filter-control filter-control--range">
      <label className="filter-control__label">{config.label}</label>
      <div className="filter-control__range-inputs">
        <input
          type="number"
          value={currentMin}
          min={min}
          max={max}
          onChange={(e) => onChange([Number(e.target.value), currentMax])}
          className="filter-control__range-input"
          placeholder="Min"
        />
        <span className="filter-control__range-separator">to</span>
        <input
          type="number"
          value={currentMax}
          min={min}
          max={max}
          onChange={(e) => onChange([currentMin, Number(e.target.value)])}
          className="filter-control__range-input"
          placeholder="Max"
        />
      </div>
    </div>
  );
}

interface DateFilterProps {
  config: FilterConfig;
  value: [string, string] | undefined;
  onChange: (value: [string, string]) => void;
}

function DateFilter({ config, value, onChange }: DateFilterProps) {
  const startDate = value?.[0] ?? '';
  const endDate = value?.[1] ?? '';

  return (
    <div className="filter-control filter-control--date">
      <label className="filter-control__label">{config.label}</label>
      <div className="filter-control__date-inputs">
        <input
          type="date"
          value={startDate}
          onChange={(e) => onChange([e.target.value, endDate])}
          className="filter-control__date-input"
        />
        <span className="filter-control__range-separator">to</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => onChange([startDate, e.target.value])}
          className="filter-control__date-input"
        />
      </div>
    </div>
  );
}

export default FilterBar;
