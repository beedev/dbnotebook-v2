import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Plus, Loader2, ClipboardCheck, AlertCircle } from 'lucide-react';
import { listQuizzes, deleteQuiz } from '../../../services/api';
import type { Quiz } from '../../../types/quiz';
import { QuizCard } from './QuizCard';

export function QuizDashboard() {
  const location = useLocation();
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Check for success message from quiz creation
  useEffect(() => {
    if (location.state?.created) {
      setSuccessMessage(`Quiz created! Share this link: ${window.location.origin}${location.state.link}`);
      // Clear the state
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  // Load quizzes
  useEffect(() => {
    async function loadQuizzes() {
      try {
        const data = await listQuizzes();
        setQuizzes(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load quizzes';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    }
    loadQuizzes();
  }, []);

  const handleDelete = async (quizId: string) => {
    try {
      await deleteQuiz(quizId);
      setQuizzes(quizzes.filter(q => q.id !== quizId));
      setSuccessMessage('Quiz deleted');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete quiz';
      setError(message);
      setTimeout(() => setError(null), 5000);
    }
  };

  const handleCopyLink = (link: string) => {
    navigator.clipboard.writeText(link);
    setSuccessMessage('Link copied to clipboard!');
    setTimeout(() => setSuccessMessage(null), 3000);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <ClipboardCheck className="w-8 h-8 text-primary" />
          <div>
            <h1 className="text-2xl font-semibold text-text">My Quizzes</h1>
            <p className="text-sm text-text-muted mt-1">Create and manage quizzes from your notebooks</p>
          </div>
        </div>
        <Link
          to="/quizzes/create"
          className="flex items-center gap-2 px-5 py-2.5 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors font-medium"
        >
          <Plus className="w-5 h-5" />
          Create New Quiz
        </Link>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="mb-6 p-4 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400">
          {successMessage}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Quiz List */}
      {quizzes.length === 0 ? (
        <div className="text-center py-16 bg-void-surface rounded-xl border border-void-lighter max-w-2xl mx-auto">
          <ClipboardCheck className="w-16 h-16 text-text-muted mx-auto mb-6" />
          <h2 className="text-xl font-medium text-text mb-3">No quizzes yet</h2>
          <p className="text-text-muted mb-8 max-w-md mx-auto">
            Create your first quiz from a notebook to test knowledge retention and understanding.
          </p>
          <Link
            to="/quizzes/create"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors font-medium"
          >
            <Plus className="w-5 h-5" />
            Create New Quiz
          </Link>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {quizzes.map((quiz) => (
            <QuizCard
              key={quiz.id}
              quiz={quiz}
              onDelete={handleDelete}
              onCopyLink={handleCopyLink}
            />
          ))}
        </div>
      )}
    </div>
  );
}
