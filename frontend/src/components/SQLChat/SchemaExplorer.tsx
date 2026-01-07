/**
 * Schema Explorer Component
 *
 * Displays database schema in a collapsible tree view with:
 * - Table list with row counts
 * - Column details (type, constraints)
 * - Sample values preview
 * - Search/filter functionality
 */

import { useState, useMemo } from 'react';
import {
  Table,
  ChevronRight,
  ChevronDown,
  Key,
  Link,
  Hash,
  Search,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import type { SchemaInfo, TableInfo, ColumnInfo } from '../../types/sqlChat';

interface SchemaExplorerProps {
  schema: SchemaInfo | null;
  isLoading?: boolean;
  onRefresh?: () => void;
}

function ColumnTypeIcon({ column }: { column: ColumnInfo }) {
  if (column.isPrimaryKey) {
    return (
      <span title="Primary Key">
        <Key className="w-3 h-3 text-yellow-400" />
      </span>
    );
  }
  if (column.isForeignKey) {
    return (
      <span title="Foreign Key">
        <Link className="w-3 h-3 text-blue-400" />
      </span>
    );
  }
  return <Hash className="w-3 h-3 text-slate-500" />;
}

function formatDataType(type: string): string {
  // Simplify common PostgreSQL types
  return type
    .replace('character varying', 'varchar')
    .replace('timestamp without time zone', 'timestamp')
    .replace('timestamp with time zone', 'timestamptz')
    .replace('double precision', 'float8');
}

function TableNode({ table }: { table: TableInfo }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      {/* Table header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-slate-800/50 hover:bg-slate-800 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-slate-500" />
        ) : (
          <ChevronRight className="w-4 h-4 text-slate-500" />
        )}
        <Table className="w-4 h-4 text-cyan-400" />
        <span className="font-medium text-white">{table.name}</span>
        {table.rowCount !== undefined && (
          <span className="ml-auto text-xs text-slate-500">
            {table.rowCount.toLocaleString()} rows
          </span>
        )}
      </button>

      {/* Columns */}
      {isExpanded && (
        <div className="border-t border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-800/30 text-slate-400 text-xs">
                <th className="text-left px-3 py-1.5 font-medium">Column</th>
                <th className="text-left px-3 py-1.5 font-medium">Type</th>
                <th className="text-left px-3 py-1.5 font-medium">Nullable</th>
              </tr>
            </thead>
            <tbody>
              {table.columns.map((column) => (
                <tr
                  key={column.name}
                  className="border-t border-slate-700/50 hover:bg-slate-800/30"
                >
                  <td className="px-3 py-1.5 flex items-center gap-2">
                    <ColumnTypeIcon column={column} />
                    <span className="text-white font-mono">{column.name}</span>
                  </td>
                  <td className="px-3 py-1.5 text-slate-400 font-mono text-xs">
                    {formatDataType(column.dataType)}
                  </td>
                  <td className="px-3 py-1.5">
                    {column.nullable ? (
                      <span className="text-slate-500">null</span>
                    ) : (
                      <span className="text-orange-400">not null</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Sample values */}
          {Object.keys(table.sampleValues).length > 0 && (
            <div className="px-3 py-2 bg-slate-800/20 border-t border-slate-700">
              <p className="text-xs text-slate-500 mb-1">Sample values:</p>
              <div className="text-xs text-slate-400 space-y-0.5">
                {Object.entries(table.sampleValues).slice(0, 3).map(([col, values]) => (
                  <div key={col} className="flex gap-2">
                    <span className="text-slate-500">{col}:</span>
                    <span className="truncate">
                      {(values as any[]).slice(0, 3).map(v => String(v)).join(', ')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function SchemaExplorer({
  schema,
  isLoading = false,
  onRefresh,
}: SchemaExplorerProps) {
  const [searchQuery, setSearchQuery] = useState('');

  // Filter tables by search query
  const filteredTables = useMemo(() => {
    if (!schema?.tables) return [];
    if (!searchQuery) return schema.tables;

    const query = searchQuery.toLowerCase();
    return schema.tables.filter(
      (table) =>
        table.name.toLowerCase().includes(query) ||
        table.columns.some((col) => col.name.toLowerCase().includes(query))
    );
  }, [schema?.tables, searchQuery]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="text-center py-8 text-slate-500">
        <Table className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>Select a connection to view schema.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with search and refresh */}
      <div className="flex items-center gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tables or columns..."
            className="w-full pl-9 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                       text-white text-sm placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
          />
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
            title="Refresh schema"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Table count */}
      <div className="text-sm text-slate-400">
        {filteredTables.length} table{filteredTables.length !== 1 ? 's' : ''}
        {searchQuery && ` matching "${searchQuery}"`}
      </div>

      {/* Table list */}
      <div className="space-y-2">
        {filteredTables.map((table) => (
          <TableNode key={table.name} table={table} />
        ))}
      </div>

      {filteredTables.length === 0 && searchQuery && (
        <div className="text-center py-4 text-slate-500">
          No tables or columns match "{searchQuery}"
        </div>
      )}
    </div>
  );
}
