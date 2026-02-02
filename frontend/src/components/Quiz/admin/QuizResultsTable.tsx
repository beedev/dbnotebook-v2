import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Loader2, Users, BarChart3, TrendingUp, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import { getQuizResults } from '../../../services/api';
import type { QuizResultsResponse, QuizAttempt } from '../../../types/quiz';

export function QuizResultsTable() {
  const { quizId } = useParams<{ quizId: string }>();
  const navigate = useNavigate();
  const [results, setResults] = useState<QuizResultsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadResults() {
      if (!quizId) return;
      try {
        const data = await getQuizResults(quizId);
        setResults(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load results';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    }
    loadResults();
  }, [quizId]);

  const exportToCsv = () => {
    if (!results) return;

    const headers = ['Name', 'Score', 'Total', 'Percentage', 'Passed', 'Completed'];
    const rows = results.attempts.map((a) => [
      a.takerName,
      a.score,
      a.total,
      `${a.percentage}%`,
      a.passed ? 'Yes' : 'No',
      a.completedAt ? new Date(a.completedAt).toLocaleString() : 'In Progress',
    ]);

    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${results.quiz.title.replace(/[^a-z0-9]/gi, '_')}_results.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !results) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <button
          onClick={() => navigate('/quizzes')}
          className="flex items-center gap-2 text-text-muted hover:text-text mb-6"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Quizzes
        </button>
        <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 flex items-center gap-3">
          <AlertCircle className="w-6 h-6 flex-shrink-0" />
          <div>
            <h2 className="font-medium">Error loading results</h2>
            <p className="text-sm">{error || 'Unknown error'}</p>
          </div>
        </div>
      </div>
    );
  }

  const { quiz, statistics, attempts } = results;

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/quizzes')}
            className="p-2 hover:bg-void-surface rounded-lg text-text-muted hover:text-text transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-semibold text-text">{quiz.title}</h1>
            <p className="text-sm text-text-muted">Results</p>
          </div>
        </div>
        <button
          onClick={exportToCsv}
          disabled={attempts.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-void-surface border border-void-lighter rounded-lg text-text hover:bg-void-lighter transition-colors disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={<Users className="w-5 h-5" />}
          label="Total Attempts"
          value={statistics.totalAttempts}
          color="text-blue-400"
        />
        <StatCard
          icon={<BarChart3 className="w-5 h-5" />}
          label="Average Score"
          value={`${statistics.avgPercentage}%`}
          color="text-purple-400"
        />
        <StatCard
          icon={<TrendingUp className="w-5 h-5" />}
          label="Pass Rate"
          value={`${statistics.passRate}%`}
          color="text-green-400"
        />
        <StatCard
          icon={<CheckCircle className="w-5 h-5" />}
          label="Completed"
          value={statistics.completedAttempts}
          color="text-teal-400"
        />
      </div>

      {/* Results Table */}
      {attempts.length === 0 ? (
        <div className="text-center py-12 bg-void-surface rounded-lg border border-void-lighter">
          <Users className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <h2 className="text-lg font-medium text-text mb-2">No attempts yet</h2>
          <p className="text-text-muted">
            Share the quiz link to collect responses.
          </p>
        </div>
      ) : (
        <div className="bg-void-surface rounded-lg border border-void-lighter overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-void-lighter">
                <th className="text-left px-4 py-3 text-sm font-medium text-text-muted">Name</th>
                <th className="text-center px-4 py-3 text-sm font-medium text-text-muted">Score</th>
                <th className="text-center px-4 py-3 text-sm font-medium text-text-muted">%</th>
                <th className="text-center px-4 py-3 text-sm font-medium text-text-muted">Status</th>
                <th className="text-right px-4 py-3 text-sm font-medium text-text-muted">Completed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-void-lighter">
              {attempts.map((attempt) => (
                <AttemptRow key={attempt.id} attempt={attempt} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="bg-void-surface rounded-lg border border-void-lighter p-4">
      <div className={`${color} mb-2`}>{icon}</div>
      <div className="text-2xl font-semibold text-text">{value}</div>
      <div className="text-sm text-text-muted">{label}</div>
    </div>
  );
}

function AttemptRow({ attempt }: { attempt: QuizAttempt }) {
  return (
    <tr className="hover:bg-void-lighter/50 transition-colors">
      <td className="px-4 py-3">
        <span className="font-medium text-text">{attempt.takerName}</span>
      </td>
      <td className="text-center px-4 py-3 text-text">
        {attempt.score}/{attempt.total}
      </td>
      <td className="text-center px-4 py-3">
        <span className={attempt.percentage >= 60 ? 'text-green-400' : 'text-yellow-400'}>
          {attempt.percentage}%
        </span>
      </td>
      <td className="text-center px-4 py-3">
        {attempt.completedAt ? (
          attempt.passed ? (
            <span className="inline-flex items-center gap-1 text-green-400">
              <CheckCircle className="w-4 h-4" />
              Passed
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-red-400">
              <XCircle className="w-4 h-4" />
              Failed
            </span>
          )
        ) : (
          <span className="text-text-muted">In Progress</span>
        )}
      </td>
      <td className="text-right px-4 py-3 text-text-muted text-sm">
        {attempt.completedAt
          ? new Date(attempt.completedAt).toLocaleString()
          : '-'}
      </td>
    </tr>
  );
}
