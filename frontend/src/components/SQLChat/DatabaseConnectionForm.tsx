/**
 * Database Connection Form Component
 *
 * Provides a form to configure database connections with:
 * - Structured form fields (host, port, database, credentials)
 * - Connection string toggle for power users
 * - Data masking policy configuration
 * - Connection testing before saving
 */

import { useState, useCallback } from 'react';
import {
  Database,
  Server,
  Key,
  User,
  Link,
  Eye,
  EyeOff,
  CheckCircle,
  XCircle,
  Loader2,
  Shield,
} from 'lucide-react';

import type {
  ConnectionFormData,
  DatabaseType,
  MaskingPolicy,
} from '../../types/sqlChat';

interface DatabaseConnectionFormProps {
  onSubmit: (data: ConnectionFormData) => Promise<void>;
  onTest: (data: ConnectionFormData) => Promise<boolean>;
  onCancel: () => void;
  isLoading?: boolean;
}

const DEFAULT_PORTS: Record<DatabaseType, number> = {
  postgresql: 5432,
  mysql: 3306,
  sqlite: 0,
};

const DB_TYPE_LABELS: Record<DatabaseType, string> = {
  postgresql: 'PostgreSQL',
  mysql: 'MySQL',
  sqlite: 'SQLite',
};

export function DatabaseConnectionForm({
  onSubmit,
  onTest,
  onCancel,
  isLoading = false,
}: DatabaseConnectionFormProps) {
  // Form state
  const [name, setName] = useState('');
  const [dbType, setDbType] = useState<DatabaseType>('postgresql');
  const [host, setHost] = useState('localhost');
  const [port, setPort] = useState(5432);
  const [databaseName, setDatabaseName] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Connection string mode
  const [useConnectionString, setUseConnectionString] = useState(false);
  const [connectionString, setConnectionString] = useState('');

  // Masking policy
  const [showMaskingConfig, setShowMaskingConfig] = useState(false);
  const [maskColumns, setMaskColumns] = useState('');
  const [redactColumns, setRedactColumns] = useState('');
  const [hashColumns, setHashColumns] = useState('');

  // Test connection state
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);
  const [testMessage, setTestMessage] = useState('');

  // Build form data
  const getFormData = useCallback((): ConnectionFormData => {
    const maskingPolicy: MaskingPolicy | undefined =
      maskColumns || redactColumns || hashColumns
        ? {
            maskColumns: maskColumns.split(',').map(s => s.trim()).filter(Boolean),
            redactColumns: redactColumns.split(',').map(s => s.trim()).filter(Boolean),
            hashColumns: hashColumns.split(',').map(s => s.trim()).filter(Boolean),
          }
        : undefined;

    return {
      name,
      dbType,
      host: dbType !== 'sqlite' ? host : undefined,
      port: dbType !== 'sqlite' ? port : undefined,
      databaseName,
      username: dbType !== 'sqlite' ? username : undefined,
      password: dbType !== 'sqlite' ? password : undefined,
      connectionString: useConnectionString ? connectionString : undefined,
      useConnectionString,
      maskingPolicy,
    };
  }, [name, dbType, host, port, databaseName, username, password, useConnectionString, connectionString, maskColumns, redactColumns, hashColumns]);

  // Handle DB type change
  const handleDbTypeChange = useCallback((newType: DatabaseType) => {
    setDbType(newType);
    setPort(DEFAULT_PORTS[newType]);
    setTestResult(null);
    setTestMessage('');
  }, []);

  // Test connection
  const handleTest = useCallback(async () => {
    setIsTesting(true);
    setTestResult(null);
    setTestMessage('');

    try {
      const success = await onTest(getFormData());
      setTestResult(success ? 'success' : 'error');
      setTestMessage(success ? 'Connection successful!' : 'Connection failed');
    } catch (err) {
      setTestResult('error');
      setTestMessage(err instanceof Error ? err.message : 'Connection failed');
    } finally {
      setIsTesting(false);
    }
  }, [getFormData, onTest]);

  // Submit form
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit(getFormData());
  }, [getFormData, onSubmit]);

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Connection Name */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Connection Name
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My Database"
          required
          className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                     text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
        />
      </div>

      {/* Database Type */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Database Type
        </label>
        <div className="flex gap-2">
          {(Object.keys(DB_TYPE_LABELS) as DatabaseType[]).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => handleDbTypeChange(type)}
              className={`flex-1 px-4 py-2 rounded-lg border transition-colors ${
                dbType === type
                  ? 'bg-cyan-600 border-cyan-500 text-white'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600'
              }`}
            >
              <Database className="w-4 h-4 inline-block mr-2" />
              {DB_TYPE_LABELS[type]}
            </button>
          ))}
        </div>
      </div>

      {/* Connection String Toggle */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="useConnectionString"
          checked={useConnectionString}
          onChange={(e) => setUseConnectionString(e.target.checked)}
          className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-cyan-500 focus:ring-cyan-500"
        />
        <label htmlFor="useConnectionString" className="text-sm text-slate-400">
          Use connection string instead
        </label>
      </div>

      {useConnectionString ? (
        /* Connection String Input */
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            <Link className="w-4 h-4 inline-block mr-2" />
            Connection String
          </label>
          <input
            type="text"
            value={connectionString}
            onChange={(e) => setConnectionString(e.target.value)}
            placeholder={`${dbType}://user:password@host:${DEFAULT_PORTS[dbType]}/database`}
            required
            className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                       text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none font-mono text-sm"
          />
          <p className="mt-1 text-xs text-slate-500">
            Example: {dbType === 'sqlite' ? 'sqlite:///path/to/file.db' : `${dbType}://user:pass@localhost:${DEFAULT_PORTS[dbType]}/mydb`}
          </p>
        </div>
      ) : (
        /* Structured Form Fields */
        <>
          {dbType !== 'sqlite' && (
            <>
              {/* Host & Port */}
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    <Server className="w-4 h-4 inline-block mr-2" />
                    Host
                  </label>
                  <input
                    type="text"
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                    placeholder="localhost"
                    required
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                               text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Port
                  </label>
                  <input
                    type="number"
                    value={port}
                    onChange={(e) => setPort(parseInt(e.target.value) || 0)}
                    required
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                               text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Username & Password */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    <User className="w-4 h-4 inline-block mr-2" />
                    Username
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="postgres"
                    required
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                               text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    <Key className="w-4 h-4 inline-block mr-2" />
                    Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="********"
                      required
                      className="w-full px-4 py-2 pr-10 bg-slate-800 border border-slate-700 rounded-lg
                                 text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Database Name */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              <Database className="w-4 h-4 inline-block mr-2" />
              {dbType === 'sqlite' ? 'Database Path' : 'Database Name'}
            </label>
            <input
              type="text"
              value={databaseName}
              onChange={(e) => setDatabaseName(e.target.value)}
              placeholder={dbType === 'sqlite' ? '/path/to/database.db' : 'mydb'}
              required
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                         text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
            />
          </div>
        </>
      )}

      {/* Data Masking Configuration */}
      <div className="border border-slate-700 rounded-lg overflow-hidden">
        <button
          type="button"
          onClick={() => setShowMaskingConfig(!showMaskingConfig)}
          className="w-full px-4 py-3 flex items-center justify-between bg-slate-800/50 hover:bg-slate-800 transition-colors"
        >
          <span className="flex items-center gap-2 text-sm text-slate-300">
            <Shield className="w-4 h-4" />
            Data Masking (Optional)
          </span>
          <span className="text-slate-500">{showMaskingConfig ? '-' : '+'}</span>
        </button>

        {showMaskingConfig && (
          <div className="p-4 space-y-4 bg-slate-800/30">
            <p className="text-xs text-slate-500">
              Configure which columns to mask, redact, or hash in query results.
            </p>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Mask Columns (show as ****)
              </label>
              <input
                type="text"
                value={maskColumns}
                onChange={(e) => setMaskColumns(e.target.value)}
                placeholder="email, phone, address"
                className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded
                           text-white text-sm placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Redact Columns (remove entirely)
              </label>
              <input
                type="text"
                value={redactColumns}
                onChange={(e) => setRedactColumns(e.target.value)}
                placeholder="ssn, password, token"
                className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded
                           text-white text-sm placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Hash Columns (for analytics)
              </label>
              <input
                type="text"
                value={hashColumns}
                onChange={(e) => setHashColumns(e.target.value)}
                placeholder="user_id, customer_id"
                className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded
                           text-white text-sm placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
              />
            </div>
          </div>
        )}
      </div>

      {/* Test Result */}
      {testResult && (
        <div
          className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
            testResult === 'success'
              ? 'bg-green-900/30 border border-green-800 text-green-400'
              : 'bg-red-900/30 border border-red-800 text-red-400'
          }`}
        >
          {testResult === 'success' ? (
            <CheckCircle className="w-4 h-4" />
          ) : (
            <XCircle className="w-4 h-4" />
          )}
          <span className="text-sm">{testMessage}</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3 pt-4 border-t border-slate-700">
        <button
          type="button"
          onClick={handleTest}
          disabled={isTesting || isLoading}
          className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg
                     transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isTesting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <CheckCircle className="w-4 h-4" />
          )}
          Test Connection
        </button>

        <div className="flex-1" />

        <button
          type="button"
          onClick={onCancel}
          disabled={isLoading}
          className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
        >
          Cancel
        </button>

        <button
          type="submit"
          disabled={isLoading || !name || !databaseName}
          className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg
                     transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
          Connect
        </button>
      </div>
    </form>
  );
}
