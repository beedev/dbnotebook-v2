import { useState } from 'react';
import { Loader2, ClipboardCheck, Clock, Shuffle, BarChart3, Mail } from 'lucide-react';
import type { QuizPublicInfo } from '../../../types/quiz';

interface QuizLandingProps {
  quizInfo: QuizPublicInfo;
  onStart: (name: string, email?: string) => Promise<void>;
}

export function QuizLanding({ quizInfo, onStart }: QuizLandingProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsStarting(true);
    setError(null);

    try {
      await onStart(name.trim(), email.trim() || undefined);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start quiz';
      setError(message);
      setIsStarting(false);
    }
  };

  const difficultyLabels: Record<string, string> = {
    adaptive: 'Adaptive Difficulty',
    easy: 'Easy',
    medium: 'Medium',
    hard: 'Hard',
  };

  return (
    <div className="min-h-screen bg-void flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-void-surface rounded-2xl border border-void-lighter p-8 text-center">
          {/* Icon */}
          <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <ClipboardCheck className="w-8 h-8 text-primary" />
          </div>

          {/* Title */}
          <h1 className="text-2xl font-semibold text-text mb-2">
            {quizInfo.title}
          </h1>

          {/* Quiz Info */}
          <div className="flex items-center justify-center gap-4 text-sm text-text-muted mb-6">
            <div className="flex items-center gap-1.5">
              <BarChart3 className="w-4 h-4" />
              <span>{quizInfo.numQuestions} Questions</span>
            </div>
            {quizInfo.hasTimeLimit && quizInfo.timeLimit && (
              <div className="flex items-center gap-1.5">
                <Clock className="w-4 h-4" />
                <span>{quizInfo.timeLimit} min</span>
              </div>
            )}
          </div>

          {/* Difficulty Badge */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-400/10 text-purple-400 rounded-full text-sm mb-8">
            <Shuffle className="w-4 h-4" />
            <span>{difficultyLabels[quizInfo.difficultyMode]}</span>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-6 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="block text-sm text-text-muted mb-2 text-left">
                Your name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter your name"
                className="w-full px-4 py-3 bg-void border border-void-lighter rounded-lg text-text placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary/50 text-lg"
                autoFocus
                required
              />
            </div>

            <div className="mb-6">
              <label className="block text-sm text-text-muted mb-2 text-left">
                <span className="flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5" />
                  Email (optional - allows you to resume later)
                </span>
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="w-full px-4 py-3 bg-void border border-void-lighter rounded-lg text-text placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary/50 text-lg"
              />
            </div>

            <button
              type="submit"
              disabled={isStarting || !name.trim()}
              className="w-full px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-lg font-medium"
            >
              {isStarting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Starting...
                </>
              ) : (
                'Start Quiz'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
