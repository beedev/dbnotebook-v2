import { useState } from 'react';
import { Loader2, Code } from 'lucide-react';
import type { DifficultyLevel, QuestionType } from '../../../types/quiz';
import { QuizTimer } from './QuizTimer';

interface QuizQuestionProps {
  question: string;
  options: string[];
  questionNum: number;
  total: number;
  difficulty: DifficultyLevel;
  timeLimit?: number | null;
  startTime?: Date | null;
  onSubmit: (answer: 'A' | 'B' | 'C' | 'D') => Promise<void>;
  onTimeUp?: () => void;
  questionType?: QuestionType;
  codeSnippet?: string;
}

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

const optionLabels = ['A', 'B', 'C', 'D'] as const;

const difficultyColors: Record<DifficultyLevel, string> = {
  easy: 'text-green-400 bg-green-400/10',
  medium: 'text-yellow-400 bg-yellow-400/10',
  hard: 'text-red-400 bg-red-400/10',
};

export function QuizQuestion({
  question,
  options,
  questionNum,
  total,
  difficulty,
  timeLimit,
  startTime,
  onSubmit,
  onTimeUp,
  questionType = 'multiple_choice',
  codeSnippet,
}: QuizQuestionProps) {
  const [selectedOption, setSelectedOption] = useState<'A' | 'B' | 'C' | 'D' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!selectedOption) return;

    setIsSubmitting(true);
    try {
      await onSubmit(selectedOption);
    } finally {
      setIsSubmitting(false);
      setSelectedOption(null);
    }
  };

  const isCodeQuestion = questionType !== 'multiple_choice' && codeSnippet;
  const detectedLanguage = codeSnippet ? detectLanguage(codeSnippet) : '';
  const extractedCode = codeSnippet ? extractCode(codeSnippet) : '';

  return (
    <div className="min-h-screen bg-void flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="bg-void-surface rounded-2xl border border-void-lighter p-6 md:p-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <span className="text-text-muted">
              Question {questionNum} of {total}
            </span>
            <div className="flex items-center gap-3">
              {timeLimit && startTime && onTimeUp && (
                <QuizTimer
                  timeLimitMinutes={timeLimit}
                  startTime={startTime}
                  onTimeUp={onTimeUp}
                  compact
                />
              )}
              {/* Question type badge for code questions */}
              {isCodeQuestion && (
                <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-purple-500/20 text-purple-400 flex items-center gap-1">
                  <Code className="w-3 h-3" />
                  {formatQuestionType(questionType)}
                </span>
              )}
              <span className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize ${difficultyColors[difficulty]}`}>
                {difficulty}
              </span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="h-1.5 bg-void-lighter rounded-full mb-8 overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${(questionNum / total) * 100}%` }}
            />
          </div>

          {/* Question */}
          <h2 className="text-xl md:text-2xl font-medium text-text mb-6 leading-relaxed">
            {question}
          </h2>

          {/* Code Snippet (if present) */}
          {isCodeQuestion && extractedCode && (
            <div className="mb-8 rounded-xl bg-gray-900 border border-void-lighter overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2 bg-gray-800/50 border-b border-void-lighter">
                <span className="text-xs text-text-muted font-mono">{detectedLanguage}</span>
              </div>
              <pre className="p-4 overflow-x-auto">
                <code className="text-sm font-mono text-gray-300 whitespace-pre">
                  {extractedCode}
                </code>
              </pre>
            </div>
          )}

          {/* Options */}
          <div className="space-y-3 mb-8">
            {options.map((option, index) => {
              const label = optionLabels[index];
              const isSelected = selectedOption === label;

              return (
                <button
                  key={index}
                  onClick={() => setSelectedOption(label)}
                  disabled={isSubmitting}
                  className={`w-full p-4 rounded-xl border text-left transition-all ${
                    isSelected
                      ? 'bg-primary/10 border-primary text-text'
                      : 'bg-void border-void-lighter text-text hover:border-primary/50 hover:bg-void-lighter/50'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <div className="flex items-start gap-4">
                    <span className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center font-medium ${
                      isSelected ? 'bg-primary text-white' : 'bg-void-lighter text-text-muted'
                    }`}>
                      {label}
                    </span>
                    <span className="flex-1 pt-1">{option}</span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={!selectedOption || isSubmitting}
            className="w-full py-4 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-lg font-medium"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Checking...
              </>
            ) : (
              'Submit Answer'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
