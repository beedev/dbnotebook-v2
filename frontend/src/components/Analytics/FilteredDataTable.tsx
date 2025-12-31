/**
 * Filtered Data Table Component
 *
 * Displays raw data rows that match current filters.
 * Includes CSV download functionality.
 */

import { useState, useMemo, useCallback } from 'react';
import { Download, ChevronDown, ChevronUp, Table2 } from 'lucide-react';
import { useAnalytics, useCrossFilter } from '../../contexts/AnalyticsContext';

interface FilteredDataTableProps {
  className?: string;
  maxRows?: number;
}

export function FilteredDataTable({ className = '', maxRows = 100 }: FilteredDataTableProps) {
  const { filteredData, parsedData, filters } = useAnalytics();
  const { crossFilterEvent } = useCrossFilter();

  const [isExpanded, setIsExpanded] = useState(false);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Get the data to display
  const data = filteredData || parsedData?.data || [];
  const columns = parsedData?.columns || [];
  const columnNames = columns.map((c: { name: string }) => c.name);

  // Check if any filter is active
  const hasActiveFilter = crossFilterEvent !== null ||
    Object.values(filters || {}).some((f: { value: any }) => {
      if (Array.isArray(f.value)) return f.value.length > 0;
      return f.value !== null && f.value !== undefined;
    });

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortColumn) return data;

    return [...data].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal).toLowerCase();
      const bStr = String(bVal).toLowerCase();
      return sortDirection === 'asc'
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr);
    });
  }, [data, sortColumn, sortDirection]);

  // Limit displayed rows
  const displayData = sortedData.slice(0, maxRows);

  // Handle column sort
  const handleSort = useCallback((column: string) => {
    if (sortColumn === column) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  }, [sortColumn]);

  // Export to CSV
  const handleExportCSV = useCallback(() => {
    if (sortedData.length === 0) return;

    // Build CSV content
    const headers = columnNames.join(',');
    const rows = sortedData.map(row =>
      columnNames.map(col => {
        const val = row[col];
        if (val === null || val === undefined) return '';
        const str = String(val);
        // Escape quotes and wrap in quotes if contains comma or newline
        if (str.includes(',') || str.includes('\n') || str.includes('"')) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      }).join(',')
    ).join('\n');

    const csv = `${headers}\n${rows}`;

    // Create download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `filtered_data_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [sortedData, columnNames]);

  // Don't show if no data
  if (data.length === 0) {
    return null;
  }

  return (
    <div className={`filtered-data-table ${className}`}>
      <div
        className="filtered-data-table__header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="filtered-data-table__title">
          <Table2 size={18} />
          <span>
            Filtered Data
            <span className="filtered-data-table__count">
              ({data.length.toLocaleString()} {data.length === 1 ? 'row' : 'rows'})
            </span>
          </span>
          {hasActiveFilter && (
            <span className="filtered-data-table__filter-badge">Filtered</span>
          )}
        </div>
        <div className="filtered-data-table__actions">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleExportCSV();
            }}
            className="filtered-data-table__export-btn"
            title="Download as CSV"
          >
            <Download size={16} />
            <span>Download CSV</span>
          </button>
          <button className="filtered-data-table__toggle">
            {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="filtered-data-table__content">
          <div className="filtered-data-table__scroll">
            <table className="filtered-data-table__table">
              <thead>
                <tr>
                  {columnNames.slice(0, 10).map(col => (
                    <th
                      key={col}
                      onClick={() => handleSort(col)}
                      className={sortColumn === col ? 'sorted' : ''}
                    >
                      <span>{col}</span>
                      {sortColumn === col && (
                        <span className="sort-indicator">
                          {sortDirection === 'asc' ? '▲' : '▼'}
                        </span>
                      )}
                    </th>
                  ))}
                  {columnNames.length > 10 && (
                    <th className="more-cols">+{columnNames.length - 10} more</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {displayData.map((row, i) => (
                  <tr key={i}>
                    {columnNames.slice(0, 10).map(col => (
                      <td key={col} title={String(row[col] ?? '')}>
                        {formatCellValue(row[col])}
                      </td>
                    ))}
                    {columnNames.length > 10 && <td className="more-cols">...</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {sortedData.length > maxRows && (
            <div className="filtered-data-table__footer">
              Showing {maxRows} of {sortedData.length.toLocaleString()} rows.
              Download CSV for full data.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatCellValue(value: any): string {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return value.toLocaleString();
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  const str = String(value);
  return str.length > 30 ? str.slice(0, 30) + '...' : str;
}

export default FilteredDataTable;
