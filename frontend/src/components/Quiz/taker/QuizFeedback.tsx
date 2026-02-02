import { CheckCircle2, XCircle, ArrowRight, Trophy } from 'lucide-react';

interface QuizFeedbackProps {
  isCorrect: boolean;
  selectedAnswer: 'A' | 'B' | 'C' | 'D';
  correctAnswer: string;
  explanation: string;
  questionNum: number;
  totalQuestions: number;
  currentScore: number;
  isLastQuestion: boolean;
  onContinue: () => void;
}

export function QuizFeedback({
  isCorrect,
  selectedAnswer,
  correctAnswer,
  explanation,
  questionNum,
  totalQuestions,
  currentScore,
  isLastQuestion,
  onContinue,
}: QuizFeedbackProps) {
  return (
    <div className="min-h-screen bg-void flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        <div className="bg-void-surface rounded-2xl border border-void-lighter p-6 md:p-8">
          {/* Result Icon */}
          <div className="flex justify-center mb-6">
            <div className={`w-20 h-20 rounded-full flex items-center justify-center ${
              isCorrect ? 'bg-green-400/10' : 'bg-red-400/10'
            }`}>
              {isCorrect ? (
                <CheckCircle2 className="w-10 h-10 text-green-400" />
              ) : (
                <XCircle className="w-10 h-10 text-red-400" />
              )}
            </div>
          </div>

          {/* Result Text */}
          <h2 className={`text-2xl font-bold text-center mb-2 ${
            isCorrect ? 'text-green-400' : 'text-red-400'
          }`}>
            {isCorrect ? 'Correct!' : 'Incorrect'}
          </h2>

          {/* Score Progress */}
          <p className="text-text-muted text-center mb-6">
            Question {questionNum} of {totalQuestions} | Score: {currentScore}/{questionNum}
          </p>

          {/* Answer Details */}
          <div className="bg-void rounded-xl p-4 mb-6 space-y-3">
            {!isCorrect && (
              <div className="flex items-start gap-3">
                <span className="text-text-muted text-sm min-w-[100px]">Your answer:</span>
                <span className="text-red-400 font-medium">{selectedAnswer}</span>
              </div>
            )}
            <div className="flex items-start gap-3">
              <span className="text-text-muted text-sm min-w-[100px]">Correct answer:</span>
              <span className="text-green-400 font-medium">{correctAnswer}</span>
            </div>
          </div>

          {/* Explanation */}
          <div className="bg-void-lighter/30 rounded-xl p-5 mb-8 border border-void-lighter">
            <h3 className="text-sm font-medium text-text-muted mb-2 uppercase tracking-wide">
              Explanation
            </h3>
            <p className="text-text leading-relaxed">
              {explanation}
            </p>
          </div>

          {/* Continue Button */}
          <button
            onClick={onContinue}
            className="w-full py-4 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors flex items-center justify-center gap-2 text-lg font-medium"
          >
            {isLastQuestion ? (
              <>
                <Trophy className="w-5 h-5" />
                View Results
              </>
            ) : (
              <>
                Next Question
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
