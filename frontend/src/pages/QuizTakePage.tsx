/**
 * Quiz Take Page - Public page for taking a quiz
 *
 * This is the shareable link page that allows anyone to take a quiz.
 * No authentication required.
 *
 * URL: /quiz/:quizId
 */

import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Loader2, AlertCircle } from 'lucide-react';
import { QuizProvider, useQuiz } from '../contexts/QuizContext';
import { QuizLanding, QuizQuestion, QuizFeedback, QuizResults } from '../components/Quiz/taker';

function QuizTakeContent() {
  const { quizId } = useParams<{ quizId: string }>();
  const {
    phase,
    quizInfo,
    currentQuestion,
    questionNum,
    totalQuestions,
    currentDifficulty,
    score,
    attempt,
    feedback,
    nextQuestion,
    timeLimit,
    startTime,
    error,
    isLoading,
    loadQuiz,
    startQuiz,
    submitAnswer,
    continueToNext,
    handleTimeUp,
    resetQuiz,
  } = useQuiz();

  // Load quiz info on mount
  useEffect(() => {
    if (quizId) {
      loadQuiz(quizId);
    }
  }, [quizId, loadQuiz]);

  // Loading state
  if (isLoading && phase === 'landing' && !quizInfo) {
    return (
      <div className="min-h-screen bg-void flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  // Error state
  if (phase === 'error' || error) {
    // Determine error title based on error message
    const errorTitle = error?.includes('no longer available') || error?.includes('no longer active')
      ? 'Quiz Unavailable'
      : error?.includes('submit') || error?.includes('answer')
        ? 'Quiz Error'
        : 'Quiz Not Found';

    return (
      <div className="min-h-screen bg-void flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-void-surface rounded-2xl border border-void-lighter p-8 text-center">
          <div className="w-16 h-16 bg-red-400/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-red-400" />
          </div>
          <h1 className="text-xl font-semibold text-text mb-2">{errorTitle}</h1>
          <p className="text-text-muted">
            {error || 'This quiz may have been deleted or the link is invalid.'}
          </p>
        </div>
      </div>
    );
  }

  // Landing page - enter name and optional email
  if (phase === 'landing' && quizInfo) {
    return (
      <QuizLanding
        quizInfo={quizInfo}
        onStart={(name, email) => startQuiz(quizId!, name, email)}
      />
    );
  }

  // Question display
  if (phase === 'question' && currentQuestion) {
    return (
      <QuizQuestion
        question={currentQuestion.text}
        options={currentQuestion.options}
        questionNum={questionNum}
        total={totalQuestions}
        difficulty={currentDifficulty}
        timeLimit={timeLimit}
        startTime={startTime}
        onSubmit={submitAnswer}
        onTimeUp={handleTimeUp}
        questionType={currentQuestion.type}
        codeSnippet={currentQuestion.code_snippet}
      />
    );
  }

  // Feedback display (after answering)
  if (phase === 'feedback' && feedback && currentQuestion) {
    return (
      <QuizFeedback
        isCorrect={feedback.isCorrect}
        selectedAnswer={feedback.selectedAnswer}
        correctAnswer={feedback.correctAnswer}
        explanation={feedback.explanation}
        questionNum={questionNum}
        totalQuestions={totalQuestions}
        currentScore={score}
        isLastQuestion={nextQuestion === null}
        onContinue={continueToNext}
      />
    );
  }

  // Results display
  if (phase === 'results' && attempt) {
    return (
      <QuizResults
        attempt={attempt}
        onRetry={resetQuiz}
        onClose={() => window.close()}
      />
    );
  }

  // Fallback loading
  return (
    <div className="min-h-screen bg-void flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-primary" />
    </div>
  );
}

export function QuizTakePage() {
  return (
    <QuizProvider>
      <QuizTakeContent />
    </QuizProvider>
  );
}

export default QuizTakePage;
