import { useState, useEffect, useCallback } from 'react';
import { Activity, Coins, Zap, Clock, RefreshCw } from 'lucide-react';
import { getAdminTokenMetrics } from '../../services/api';
import type { TokenMetricsResponse, ModelMetric, UserMetric, DayMetric } from '../../types/auth';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'purple' | 'orange';
}

function MetricCard({ title, value, subtitle, icon, color }: MetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-900/30 border-blue-700 text-blue-400',
    green: 'bg-green-900/30 border-green-700 text-green-400',
    purple: 'bg-purple-900/30 border-purple-700 text-purple-400',
    orange: 'bg-orange-900/30 border-orange-700 text-orange-400',
  };

  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-400">{title}</span>
        {icon}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {subtitle && <div className="text-xs text-gray-500 mt-1">{subtitle}</div>}
    </div>
  );
}

function formatNumber(num: number): string {
  if (num >= 1_000_000) {
    return (num / 1_000_000).toFixed(2) + 'M';
  }
  if (num >= 1_000) {
    return (num / 1_000).toFixed(1) + 'K';
  }
  return num.toLocaleString();
}

function formatCost(cost: number): string {
  if (cost === 0) return '$0.00';
  if (cost < 0.01) return '<$0.01';
  return `$${cost.toFixed(2)}`;
}

export function TokenMetrics() {
  const [metrics, setMetrics] = useState<TokenMetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);

  const fetchMetrics = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await getAdminTokenMetrics(days);
      setMetrics(data);
    } catch (err) {
      const error = err as { error?: string; message?: string };
      setError(error.error || error.message || 'Failed to fetch metrics');
    } finally {
      setIsLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-900/30 border border-red-700 rounded-lg">
        <h3 className="text-lg font-semibold text-red-400 mb-2">Error Loading Metrics</h3>
        <p className="text-gray-300">{error}</p>
        <button
          onClick={fetchMetrics}
          className="mt-4 px-4 py-2 bg-red-800 hover:bg-red-700 text-white rounded-lg transition-colors flex items-center"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry
        </button>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="text-center py-12 text-gray-400">
        <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>No metrics data available</p>
      </div>
    );
  }

  const summary = metrics.summary ?? { total_tokens: 0, total_cost: 0, total_queries: 0, avg_response_time: 0 };
  const by_model = metrics.by_model ?? [];
  const by_user = metrics.by_user ?? [];
  const by_day = metrics.by_day ?? [];
  const hasData = summary.total_queries > 0;

  return (
    <div className="space-y-6">
      {/* Header with Date Range Selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Token Usage Metrics</h2>
        <div className="flex items-center space-x-3">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
          <button
            onClick={fetchMetrics}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {!hasData ? (
        <div className="text-center py-12 bg-gray-800 rounded-lg">
          <Activity className="w-12 h-12 mx-auto mb-4 text-gray-600" />
          <p className="text-gray-400 text-lg">No usage data in the last {days} days</p>
          <p className="text-gray-500 text-sm mt-2">Usage data will appear here once queries are made</p>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Total Tokens"
              value={formatNumber(summary.total_tokens)}
              subtitle="Input + Output"
              icon={<Zap className="w-5 h-5" />}
              color="blue"
            />
            <MetricCard
              title="Total Cost"
              value={formatCost(summary.total_cost)}
              subtitle="Estimated"
              icon={<Coins className="w-5 h-5" />}
              color="green"
            />
            <MetricCard
              title="Total Queries"
              value={formatNumber(summary.total_queries)}
              subtitle={`Last ${days} days`}
              icon={<Activity className="w-5 h-5" />}
              color="purple"
            />
            <MetricCard
              title="Avg Response Time"
              value={`${Number(summary.avg_response_time || 0).toFixed(0)}ms`}
              subtitle="Per query"
              icon={<Clock className="w-5 h-5" />}
              color="orange"
            />
          </div>

          {/* Usage by Model */}
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-700">
              <h3 className="text-md font-semibold text-white">Usage by Model</h3>
            </div>
            {by_model.length === 0 ? (
              <div className="p-6 text-center text-gray-400">No model usage data</div>
            ) : (
              <table className="min-w-full divide-y divide-gray-700">
                <thead className="bg-gray-700/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Model</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Tokens</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Cost</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Queries</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {by_model.map((row: ModelMetric) => (
                    <tr key={row.model} className="hover:bg-gray-700/50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-white font-mono">{row.model}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300 text-right">{formatNumber(row.tokens)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300 text-right">{formatCost(row.cost)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300 text-right">{row.queries.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Usage by User */}
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-700">
              <h3 className="text-md font-semibold text-white">Usage by User</h3>
            </div>
            {by_user.length === 0 ? (
              <div className="p-6 text-center text-gray-400">No user usage data</div>
            ) : (
              <table className="min-w-full divide-y divide-gray-700">
                <thead className="bg-gray-700/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">User</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Tokens</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Cost</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Queries</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {by_user.map((row: UserMetric) => (
                    <tr key={row.user_id} className="hover:bg-gray-700/50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-white">{row.username}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300 text-right">{formatNumber(row.tokens)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300 text-right">{formatCost(row.cost)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300 text-right">{row.queries.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Daily Usage Chart (Simple Bar Chart) */}
          {by_day.length > 0 && (
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-700">
                <h3 className="text-md font-semibold text-white">Daily Usage Trend</h3>
              </div>
              <div className="p-6">
                <div className="flex items-end justify-between h-40 space-x-1">
                  {by_day.slice(-30).map((day: DayMetric, index: number) => {
                    const maxTokens = Math.max(...by_day.map(d => d.tokens));
                    const height = maxTokens > 0 ? (day.tokens / maxTokens) * 100 : 0;
                    const isLast = index === by_day.slice(-30).length - 1;

                    return (
                      <div
                        key={day.date}
                        className="flex-1 flex flex-col items-center group relative"
                      >
                        <div
                          className="w-full bg-blue-600 hover:bg-blue-500 rounded-t transition-colors cursor-pointer min-h-[2px]"
                          style={{ height: `${Math.max(height, 2)}%` }}
                        />
                        {/* Tooltip */}
                        <div className="absolute bottom-full mb-2 hidden group-hover:block z-10">
                          <div className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs whitespace-nowrap">
                            <div className="text-white font-semibold">{day.date}</div>
                            <div className="text-gray-400">{formatNumber(day.tokens)} tokens</div>
                            <div className="text-gray-400">{day.queries} queries</div>
                          </div>
                        </div>
                        {/* Show date label for first, last, and middle */}
                        {(index === 0 || isLast || index === Math.floor(by_day.slice(-30).length / 2)) && (
                          <div className="text-xs text-gray-500 mt-2 transform -rotate-45 origin-top-left whitespace-nowrap">
                            {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
