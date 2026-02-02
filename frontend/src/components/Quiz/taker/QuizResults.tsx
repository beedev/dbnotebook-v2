import { Trophy, XCircle, CheckCircle, RotateCcw, X, Code, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import type { QuizAttempt, AnswerRecord, QuestionType } from '../../../types/quiz';
import { ImprovementSuggestions } from './ImprovementSuggestions';

// Helper functions for code snippets
function detectLanguage(codeBlock: string): string {
  const match = codeBlock.match(/```(\w+)/);
  return match ? match[1] : 'plaintext';
}

function extractCode(codeBlock: string): string {
  return codeBlock.replace(/```\w*\n?/g, '').replace(/```$/g, '').trim();
}

function formatQuestionType(type: QuestionType): string {
  const labels: Record<QuestionType, string> = {
    'multiple_choice': 'Multiple Choice',
    'code_output': 'Output Prediction',
    'code_fill_blank': 'Fill in the Blank',
    'code_bug_fix': 'Bug Identification'
  };
  return labels[type] || 'Code Question';
}

interface QuizResultsProps {
  attempt: QuizAttempt;
  attemptId?: string;  // For fetching improvement suggestions
  onRetry?: () => void;
  onClose?: () => void;
}

export function QuizResults({ attempt, attemptId, onRetry, onClose }: QuizResultsProps) {
  const isPassed = attempt.passed;
  const percentage = attempt.percentage;
  const [showAnswers, setShowAnswers] = useState(false);

  // Show suggestions if there are wrong answers
  const hasWrongAnswers = attempt.answers?.some(a => !a.correct) ?? false;
  const effectiveAttemptId = attemptId || attempt.id;

  return (
    <div className="min-h-screen bg-void flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="bg-void-surface rounded-2xl border border-void-lighter p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4 ${
              isPassed ? 'bg-green-400/10' : 'bg-red-400/10'
            }`}>
              {isPassed ? (
                <Trophy className="w-10 h-10 text-green-400" />
              ) : (
                <XCircle className="w-10 h-10 text-red-400" />
              )}
            </div>

            <h1 className="text-2xl font-semibold text-text mb-2">
              {isPassed ? 'Quiz Complete!' : 'Quiz Finished'}
            </h1>
            <p className="text-text-muted">{attempt.takerName}</p>
          </div>

          {/* Score Card */}
          <div className="bg-void rounded-xl border border-void-lighter p-6 mb-8">
            <div className="flex items-center justify-center gap-8">
              <div className="text-center">
                <div className="text-4xl font-bold text-text">
                  {attempt.score}/{attempt.total}
                </div>
                <div className="text-sm text-text-muted mt-1">Score</div>
              </div>
              <div className="w-px h-16 bg-void-lighter" />
              <div className="text-center">
                <div className={`text-4xl font-bold ${
                  percentage >= 80 ? 'text-green-400' :
                  percentage >= 60 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {percentage}%
                </div>
                <div className="text-sm text-text-muted mt-1">Percentage</div>
              </div>
              <div className="w-px h-16 bg-void-lighter" />
              <div className="text-center">
                <div className={`text-lg font-medium px-3 py-1 rounded-full ${
                  isPassed ? 'bg-green-400/10 text-green-400' : 'bg-red-400/10 text-red-400'
                }`}>
                  {isPassed ? 'Passed' : 'Failed'}
                </div>
                <div className="text-sm text-text-muted mt-1">Status</div>
              </div>
            </div>
          </div>

          {/* Improvement Suggestions */}
          {hasWrongAnswers && effectiveAttemptId && (
            <div className="mb-8">
              <ImprovementSuggestions attemptId={effectiveAttemptId} />
            </div>
          )}

          {/* Answer Breakdown - Collapsible */}
          {attempt.answers && attempt.answers.length > 0 && (
            <div className="mb-8">
              <button
                onClick={() => setShowAnswers(!showAnswers)}
                className="w-full flex items-center justify-between px-4 py-3 bg-void rounded-xl border border-void-lighter hover:bg-void-lighter transition-colors"
              >
                <h2 className="text-lg font-medium text-text">Answer Breakdown</h2>
                <div className="flex items-center gap-2 text-text-muted">
                  <span className="text-sm">
                    {attempt.score}/{attempt.total} correct
                  </span>
                  {showAnswers ? (
                    <ChevronUp className="w-5 h-5" />
                  ) : (
                    <ChevronDown className="w-5 h-5" />
                  )}
                </div>
              </button>
              {showAnswers && (
                <div className="mt-3 space-y-3">
                  {attempt.answers.map((answer, index) => (
                    <AnswerRow key={index} answer={answer} questionNum={index + 1} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            {onRetry && (
              <button
                onClick={onRetry}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors font-medium"
              >
                <RotateCcw className="w-5 h-5" />
                Try Again
              </button>
            )}
            {onClose && (
              <button
                onClick={onClose}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-void border border-void-lighter text-text rounded-xl hover:bg-void-lighter transition-colors font-medium"
              >
                <X className="w-5 h-5" />
                Close
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function AnswerRow({ answer, questionNum }: { answer: AnswerRecord; questionNum: number }) {
  const isCorrect = answer.correct;
  const isCodeQuestion = answer.type && answer.type !== 'multiple_choice' && answer.code_snippet;
  const detectedLanguage = answer.code_snippet ? detectLanguage(answer.code_snippet) : '';
  const extractedCode = answer.code_snippet ? extractCode(answer.code_snippet) : '';

  return (
    <div className={`p-4 rounded-lg border ${
      isCorrect
        ? 'bg-green-400/5 border-green-400/20'
        : 'bg-red-400/5 border-red-400/20'
    }`}>
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${
          isCorrect ? 'bg-green-400/20' : 'bg-red-400/20'
        }`}>
          {isCorrect ? (
            <CheckCircle className="w-4 h-4 text-green-400" />
          ) : (
            <XCircle className="w-4 h-4 text-red-400" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs text-text-muted">Q{questionNum}</span>
            {answer.topic && (
              <span className="text-xs px-2 py-0.5 bg-void-lighter rounded-full text-text-muted">
                {answer.topic}
              </span>
            )}
            {isCodeQuestion && answer.type && (
              <span className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded-full flex items-center gap-1">
                <Code className="w-3 h-3" />
                {formatQuestionType(answer.type)}
              </span>
            )}
          </div>
          <p className="text-sm text-text mb-2">{answer.question}</p>

          {/* Code Snippet (if present) */}
          {isCodeQuestion && extractedCode && (
            <div className="mb-3 rounded-lg bg-gray-900 border border-void-lighter overflow-hidden">
              <div className="flex items-center px-3 py-1.5 bg-gray-800/50 border-b border-void-lighter">
                <span className="text-xs text-text-muted font-mono">{detectedLanguage}</span>
              </div>
              <pre className="p-3 overflow-x-auto">
                <code className="text-xs font-mono text-gray-300 whitespace-pre">
                  {extractedCode}
                </code>
              </pre>
            </div>
          )}

          <div className="flex flex-wrap gap-2 text-xs">
            <span className={`px-2 py-1 rounded ${
              isCorrect ? 'bg-green-400/10 text-green-400' : 'bg-red-400/10 text-red-400'
            }`}>
              Your answer: {answer.userAnswer}
            </span>
            {!isCorrect && (
              <span className="px-2 py-1 rounded bg-green-400/10 text-green-400">
                Correct: {answer.correctAnswer}
              </span>
            )}
          </div>
          {answer.explanation && !isCorrect && (
            <p className="mt-2 text-xs text-text-muted italic">
              {answer.explanation}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
