import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Copy, Trash2, BarChart3, ExternalLink, Clock, HelpCircle } from 'lucide-react';
import type { Quiz } from '../../../types/quiz';

interface QuizCardProps {
  quiz: Quiz;
  onDelete: (quizId: string) => void;
  onCopyLink: (link: string) => void;
}

export function QuizCard({ quiz, onDelete, onCopyLink }: QuizCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Delete quiz "${quiz.title}"? This cannot be undone.`)) return;
    setIsDeleting(true);
    try {
      await onDelete(quiz.id);
    } finally {
      setIsDeleting(false);
    }
  };

  const fullLink = `${window.location.origin}${quiz.link}`;

  const difficultyColors: Record<string, string> = {
    adaptive: 'text-purple-400 bg-purple-400/10',
    easy: 'text-green-400 bg-green-400/10',
    medium: 'text-yellow-400 bg-yellow-400/10',
    hard: 'text-red-400 bg-red-400/10',
  };

  return (
    <div className="bg-void-surface rounded-xl border border-void-lighter p-5 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 transition-all duration-200 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-text truncate" title={quiz.title}>{quiz.title}</h3>
          <p className="text-xs text-text-muted truncate mt-0.5" title={quiz.notebookName}>
            {quiz.notebookName}
          </p>
        </div>
        <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize shrink-0 ${difficultyColors[quiz.difficultyMode] || 'text-text-muted bg-void-lighter'}`}>
          {quiz.difficultyMode}
        </span>
      </div>

      {/* Stats */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-4 text-xs text-text-muted">
        <div className="flex items-center gap-1">
          <HelpCircle className="w-3.5 h-3.5" />
          <span>{quiz.numQuestions} Q</span>
        </div>
        <div className="flex items-center gap-1">
          <BarChart3 className="w-3.5 h-3.5" />
          <span>{quiz.attemptCount} taken</span>
        </div>
        {quiz.timeLimitMinutes && (
          <div className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            <span>{quiz.timeLimitMinutes}m</span>
          </div>
        )}
      </div>

      {/* Link */}
      <div className="flex items-center gap-1 mb-4 p-2 bg-void rounded-lg border border-void-lighter">
        <code className="flex-1 text-xs text-text-muted truncate">
          {quiz.link}
        </code>
        <button
          onClick={() => onCopyLink(fullLink)}
          className="p-1 hover:bg-void-lighter rounded text-text-muted hover:text-primary transition-colors"
          title="Copy link"
        >
          <Copy className="w-3.5 h-3.5" />
        </button>
        <a
          href={quiz.link}
          target="_blank"
          rel="noopener noreferrer"
          className="p-1 hover:bg-void-lighter rounded text-text-muted hover:text-primary transition-colors"
          title="Open quiz"
        >
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>

      {/* Spacer to push actions to bottom */}
      <div className="flex-1" />

      {/* Actions */}
      <div className="flex items-center justify-between pt-3 border-t border-void-lighter">
        <span className="text-xs text-text-muted">
          {new Date(quiz.createdAt).toLocaleDateString()}
        </span>
        <div className="flex items-center gap-1">
          <Link
            to={`/quizzes/${quiz.id}/results`}
            className="px-3 py-1.5 text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20 rounded-lg transition-colors"
          >
            Results
          </Link>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="p-1.5 text-red-400 hover:bg-red-400/10 rounded-lg transition-colors disabled:opacity-50"
            title="Delete quiz"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
