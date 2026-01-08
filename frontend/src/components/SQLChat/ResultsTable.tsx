/**
 * Results Table Component
 *
 * Displays query results in a scrollable table with:
 * - Sortable columns
 * - Row count and execution time
 * - CSV download
 * - Empty state handling
 */

import { useState, useMemo } from 'react';
import {
  ChevronUp,
  ChevronDown,
  Download,
  Clock,
  Table as TableIcon,
  AlertCircle,
  BarChart3,
} from 'lucide-react';
import type { QueryResult, ColumnInfo } from '../../types/sqlChat';

interface ResultsTableProps {
  result: QueryResult | null;
  maxRows?: number;
  onAnalyzeInDashboard?: (file: File) => void;
}

type SortDirection = 'asc' | 'desc' | null;

function formatValue(value: any): string {
  if (value === null || value === undefined) {
    return 'NULL';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }
  return String(value);
}

function dataToCSV(data: Record<string, any>[], columns: ColumnInfo[]): string {
  const headers = columns.map((c) => c.name);
  const rows = data.map((row) =>
    columns.map((c) => {
      const val = row[c.name];
      // Escape quotes and wrap in quotes if contains comma
      const str = formatValue(val);
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    }).join(',')
  );

  return [headers.join(','), ...rows].join('\n');
}

function downloadCSV(data: Record<string, any>[], columns: ColumnInfo[], filename: string) {
  const csv = dataToCSV(data, columns);
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function ResultsTable({
  result,
  maxRows = 1000,
  onAnalyzeInDashboard,
}: ResultsTableProps) {
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  // Handle analyze in dashboard
  const handleAnalyzeInDashboard = () => {
    if (!result || !onAnalyzeInDashboard) return;

    const csv = dataToCSV(result.data, result.columns);
    const blob = new Blob([csv], { type: 'text/csv' });
    const file = new File([blob], 'query_results.csv', { type: 'text/csv' });
    onAnalyzeInDashboard(file);
  };

  // Sort data
  const sortedData = useMemo(() => {
    if (!result?.data || !sortColumn || !sortDirection) {
      return result?.data || [];
    }

    return [...result.data].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      // Handle nulls
      if (aVal === null || aVal === undefined) return sortDirection === 'asc' ? 1 : -1;
      if (bVal === null || bVal === undefined) return sortDirection === 'asc' ? -1 : 1;

      // Compare
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal).toLowerCase();
      const bStr = String(bVal).toLowerCase();
      return sortDirection === 'asc'
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr);
    });
  }, [result?.data, sortColumn, sortDirection]);

  // Handle column header click
  const handleSort = (columnName: string) => {
    if (sortColumn === columnName) {
      // Cycle: asc -> desc -> null
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortColumn(null);
        setSortDirection(null);
      }
    } else {
      setSortColumn(columnName);
      setSortDirection('asc');
    }
  };

  // Error state
  if (result && !result.success) {
    return (
      <div className="border border-red-800 rounded-lg bg-red-900/20 p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-red-400 font-medium">Query Error</p>
            <p className="text-sm text-red-300 mt-1">{result.errorMessage}</p>
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (!result || result.data.length === 0) {
    return (
      <div className="border border-slate-700 rounded-lg bg-slate-800/50 p-8 text-center">
        <TableIcon className="w-12 h-12 mx-auto mb-3 text-slate-600" />
        <p className="text-slate-400">
          {result ? 'Query returned no results.' : 'No query results to display.'}
        </p>
      </div>
    );
  }

  const displayData = sortedData.slice(0, maxRows);
  const hasMore = sortedData.length > maxRows;

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800/50 border-b border-slate-700">
        <div className="flex items-center gap-4 text-sm text-slate-400">
          <span>
            <span className="text-white font-medium">{result.rowCount.toLocaleString()}</span>
            {' '}row{result.rowCount !== 1 ? 's' : ''}
          </span>
          {result.executionTimeMs !== undefined && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {result.executionTimeMs}ms
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {onAnalyzeInDashboard && (
            <button
              onClick={handleAnalyzeInDashboard}
              className="flex items-center gap-1.5 px-3 py-1 text-sm text-nebula-bright hover:text-white
                         hover:bg-nebula/20 rounded transition-colors"
              title="Analyze this data in the Analytics Dashboard"
            >
              <BarChart3 className="w-4 h-4" />
              <span className="hidden sm:inline">Analyze</span>
            </button>
          )}
          <button
            onClick={() => downloadCSV(result.data, result.columns, 'query_results.csv')}
            className="flex items-center gap-1.5 px-3 py-1 text-sm text-slate-400 hover:text-white
                       hover:bg-slate-700 rounded transition-colors"
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">CSV</span>
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-800 sticky top-0">
            <tr>
              {result.columns.map((column) => (
                <th
                  key={column.name}
                  onClick={() => handleSort(column.name)}
                  className="text-left px-4 py-2 font-medium text-slate-300 border-b border-slate-700
                             cursor-pointer hover:bg-slate-700/50 transition-colors whitespace-nowrap"
                >
                  <div className="flex items-center gap-1">
                    <span>{column.name}</span>
                    {sortColumn === column.name && (
                      sortDirection === 'asc' ? (
                        <ChevronUp className="w-4 h-4 text-cyan-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-cyan-400" />
                      )
                    )}
                  </div>
                  <span className="text-xs text-slate-500 font-normal">
                    {column.dataType}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayData.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className="border-b border-slate-700/50 hover:bg-slate-800/30"
              >
                {result.columns.map((column) => {
                  const value = row[column.name];
                  const isNull = value === null || value === undefined;

                  return (
                    <td
                      key={column.name}
                      className={`px-4 py-2 ${
                        isNull ? 'text-slate-600 italic' : 'text-slate-300'
                      }`}
                    >
                      <div className="max-w-xs truncate" title={formatValue(value)}>
                        {formatValue(value)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* More rows indicator */}
      {hasMore && (
        <div className="px-4 py-2 bg-slate-800/30 border-t border-slate-700 text-center text-sm text-slate-500">
          Showing {maxRows.toLocaleString()} of {result.rowCount.toLocaleString()} rows.
          Download CSV for full data.
        </div>
      )}
    </div>
  );
}
