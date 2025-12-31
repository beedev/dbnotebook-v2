/**
 * Column Profile Table Component
 *
 * Displays a sortable, searchable table of all columns with their statistics.
 * Expandable rows show detailed statistics for each column.
 */

import { useState, useMemo } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Hash,
  Type,
  Calendar,
  ToggleLeft,
  List,
  Search,
  ArrowUpDown,
} from 'lucide-react';
import type { ColumnMetadata } from '../../types/analytics';
import { ColumnDetailPanel } from './ColumnDetailPanel';

interface ColumnProfileTableProps {
  columns: ColumnMetadata[];
  className?: string;
}

type SortField = 'name' | 'type' | 'nullPercent' | 'uniqueCount';
type SortOrder = 'asc' | 'desc';

const typeIcons: Record<string, React.ReactNode> = {
  numeric: <Hash size={14} className="column-type-icon column-type-icon--numeric" />,
  categorical: <List size={14} className="column-type-icon column-type-icon--categorical" />,
  datetime: <Calendar size={14} className="column-type-icon column-type-icon--datetime" />,
  boolean: <ToggleLeft size={14} className="column-type-icon column-type-icon--boolean" />,
  text: <Type size={14} className="column-type-icon column-type-icon--text" />,
};

const typeLabels: Record<string, string> = {
  numeric: 'Numeric',
  categorical: 'Categorical',
  datetime: 'Date/Time',
  boolean: 'Boolean',
  text: 'Text',
};

export function ColumnProfileTable({ columns, className = '' }: ColumnProfileTableProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('name');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  // Filter columns by search query
  const filteredColumns = useMemo(() => {
    if (!searchQuery.trim()) return columns;
    const query = searchQuery.toLowerCase();
    return columns.filter(
      col =>
        col.name.toLowerCase().includes(query) ||
        col.inferredType.toLowerCase().includes(query)
    );
  }, [columns, searchQuery]);

  // Sort columns
  const sortedColumns = useMemo(() => {
    return [...filteredColumns].sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'type':
          comparison = a.inferredType.localeCompare(b.inferredType);
          break;
        case 'nullPercent':
          comparison = (a.nullPercent || 0) - (b.nullPercent || 0);
          break;
        case 'uniqueCount':
          comparison = (a.uniqueCount || 0) - (b.uniqueCount || 0);
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });
  }, [filteredColumns, sortField, sortOrder]);

  const toggleRow = (columnName: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(columnName)) {
        next.delete(columnName);
      } else {
        next.add(columnName);
      }
      return next;
    });
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const getNullPercentColor = (percent: number): string => {
    if (percent === 0) return 'null-indicator--none';
    if (percent < 5) return 'null-indicator--low';
    if (percent < 20) return 'null-indicator--medium';
    return 'null-indicator--high';
  };

  return (
    <div className={`column-profile-table ${className}`}>
      {/* Search Bar */}
      <div className="column-profile-table__search">
        <Search size={16} className="column-profile-table__search-icon" />
        <input
          type="text"
          placeholder="Search columns..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="column-profile-table__search-input"
        />
        <span className="column-profile-table__count">
          {sortedColumns.length} of {columns.length} columns
        </span>
      </div>

      {/* Table */}
      <div className="column-profile-table__wrapper">
        <table className="column-profile-table__table">
          <thead>
            <tr>
              <th className="column-profile-table__th column-profile-table__th--expand"></th>
              <th
                className="column-profile-table__th column-profile-table__th--sortable"
                onClick={() => handleSort('name')}
              >
                <span>Column Name</span>
                <ArrowUpDown size={14} className={sortField === 'name' ? 'sort-active' : ''} />
              </th>
              <th
                className="column-profile-table__th column-profile-table__th--sortable"
                onClick={() => handleSort('type')}
              >
                <span>Type</span>
                <ArrowUpDown size={14} className={sortField === 'type' ? 'sort-active' : ''} />
              </th>
              <th
                className="column-profile-table__th column-profile-table__th--sortable column-profile-table__th--numeric"
                onClick={() => handleSort('nullPercent')}
              >
                <span>Missing %</span>
                <ArrowUpDown size={14} className={sortField === 'nullPercent' ? 'sort-active' : ''} />
              </th>
              <th
                className="column-profile-table__th column-profile-table__th--sortable column-profile-table__th--numeric"
                onClick={() => handleSort('uniqueCount')}
              >
                <span>Unique</span>
                <ArrowUpDown size={14} className={sortField === 'uniqueCount' ? 'sort-active' : ''} />
              </th>
              <th className="column-profile-table__th">Sample Values</th>
            </tr>
          </thead>
          <tbody>
            {sortedColumns.map(column => (
              <>
                <tr
                  key={column.name}
                  className={`column-profile-table__row ${expandedRows.has(column.name) ? 'column-profile-table__row--expanded' : ''}`}
                  onClick={() => toggleRow(column.name)}
                >
                  <td className="column-profile-table__td column-profile-table__td--expand">
                    {expandedRows.has(column.name) ? (
                      <ChevronDown size={16} />
                    ) : (
                      <ChevronRight size={16} />
                    )}
                  </td>
                  <td className="column-profile-table__td column-profile-table__td--name">
                    <code>{column.name}</code>
                  </td>
                  <td className="column-profile-table__td column-profile-table__td--type">
                    <span className={`type-badge type-badge--${column.inferredType}`}>
                      {typeIcons[column.inferredType] || typeIcons.text}
                      <span>{typeLabels[column.inferredType] || column.inferredType}</span>
                    </span>
                  </td>
                  <td className="column-profile-table__td column-profile-table__td--numeric">
                    <span className={`null-indicator ${getNullPercentColor(column.nullPercent || 0)}`}>
                      {(column.nullPercent || 0).toFixed(1)}%
                    </span>
                  </td>
                  <td className="column-profile-table__td column-profile-table__td--numeric">
                    {column.uniqueCount?.toLocaleString() || 0}
                  </td>
                  <td className="column-profile-table__td column-profile-table__td--samples">
                    <span className="sample-values">
                      {(column.sampleValues || []).slice(0, 3).map((val, i) => (
                        <span key={i} className="sample-value">
                          {String(val).slice(0, 20)}
                          {String(val).length > 20 ? '...' : ''}
                        </span>
                      ))}
                      {(column.sampleValues?.length || 0) > 3 && (
                        <span className="sample-more">+{column.sampleValues!.length - 3}</span>
                      )}
                    </span>
                  </td>
                </tr>
                {expandedRows.has(column.name) && (
                  <tr key={`${column.name}-detail`} className="column-profile-table__detail-row">
                    <td colSpan={6}>
                      <ColumnDetailPanel column={column} />
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>

      {sortedColumns.length === 0 && (
        <div className="column-profile-table__empty">
          {searchQuery ? (
            <p>No columns match "{searchQuery}"</p>
          ) : (
            <p>No column data available</p>
          )}
        </div>
      )}
    </div>
  );
}

export default ColumnProfileTable;
