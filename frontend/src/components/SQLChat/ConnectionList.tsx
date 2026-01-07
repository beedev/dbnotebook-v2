/**
 * Connection List Component
 *
 * Displays and manages database connections with:
 * - Connection cards showing database info
 * - Active connection indicator
 * - Delete connection action
 * - Time since last used
 */

import { Database, Trash2, Clock, CheckCircle } from 'lucide-react';
import type { DatabaseConnection, DatabaseType } from '../../types/sqlChat';

interface ConnectionListProps {
  connections: DatabaseConnection[];
  activeConnectionId: string | null;
  onSelect: (connectionId: string) => void;
  onDelete: (connectionId: string) => void;
  isLoading?: boolean;
}

const DB_TYPE_COLORS: Record<DatabaseType, string> = {
  postgresql: 'text-blue-400 bg-blue-900/30 border-blue-800',
  mysql: 'text-orange-400 bg-orange-900/30 border-orange-800',
  sqlite: 'text-green-400 bg-green-900/30 border-green-800',
};

const DB_TYPE_LABELS: Record<DatabaseType, string> = {
  postgresql: 'PostgreSQL',
  mysql: 'MySQL',
  sqlite: 'SQLite',
};

function formatLastUsed(date: string | undefined): string {
  if (!date) return 'Never used';

  const now = new Date();
  const lastUsed = new Date(date);
  const diffMs = now.getTime() - lastUsed.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return lastUsed.toLocaleDateString();
}

export function ConnectionList({
  connections,
  activeConnectionId,
  onSelect,
  onDelete,
  isLoading = false,
}: ConnectionListProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse bg-slate-800 rounded-lg h-20" />
        ))}
      </div>
    );
  }

  if (connections.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        <Database className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>No database connections yet.</p>
        <p className="text-sm mt-1">Add a connection to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {connections.map((connection) => {
        const isActive = connection.id === activeConnectionId;
        const dbTypeClass = DB_TYPE_COLORS[connection.dbType];

        return (
          <div
            key={connection.id}
            onClick={() => onSelect(connection.id)}
            className={`
              relative p-4 rounded-lg border cursor-pointer transition-all
              ${isActive
                ? 'bg-cyan-900/20 border-cyan-700 shadow-lg shadow-cyan-900/20'
                : 'bg-slate-800/50 border-slate-700 hover:border-slate-600 hover:bg-slate-800'
              }
            `}
          >
            {/* Active indicator */}
            {isActive && (
              <div className="absolute top-3 right-3">
                <CheckCircle className="w-5 h-5 text-cyan-400" />
              </div>
            )}

            {/* Connection info */}
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-lg border ${dbTypeClass}`}>
                <Database className="w-5 h-5" />
              </div>

              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-white truncate pr-8">
                  {connection.name}
                </h3>

                <div className="flex items-center gap-2 mt-1 text-sm text-slate-400">
                  <span className={`px-2 py-0.5 rounded text-xs ${dbTypeClass}`}>
                    {DB_TYPE_LABELS[connection.dbType]}
                  </span>
                  {connection.host && (
                    <span className="truncate">
                      {connection.host}:{connection.port}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-1 mt-2 text-xs text-slate-500">
                  <Clock className="w-3 h-3" />
                  {formatLastUsed(connection.lastUsedAt)}
                </div>
              </div>
            </div>

            {/* Delete button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(connection.id);
              }}
              className="absolute bottom-3 right-3 p-1.5 text-slate-500 hover:text-red-400
                         hover:bg-red-900/20 rounded transition-colors"
              title="Delete connection"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
