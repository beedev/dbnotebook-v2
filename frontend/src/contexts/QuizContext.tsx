/**
 * Quiz Context - Quiz session state management
 *
 * Manages:
 * - Current quiz attempt state
 * - Question navigation
 * - Answer submission
 * - Feedback display
 * - Results tracking
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import type {
  QuizAttempt,
  QuizPublicInfo,
  Question,
  DifficultyLevel,
} from '../types/quiz';
import {
  getQuizInfo,
  startQuizAttempt,
  submitQuizAnswer,
} from '../services/api';

type QuizPhase = 'landing' | 'question' | 'feedback' | 'results' | 'error';

interface AnswerFeedback {
  isCorrect: boolean;
  selectedAnswer: 'A' | 'B' | 'C' | 'D';
  correctAnswer: string;
  explanation: string;
}

interface QuizState {
  phase: QuizPhase;
  quizInfo: QuizPublicInfo | null;
  attemptId: string | null;
  takerName: string | null;
  currentQuestion: Question | null;
  questionNum: number;
  totalQuestions: number;
  score: number;
  currentDifficulty: DifficultyLevel;
  attempt: QuizAttempt | null;
  feedback: AnswerFeedback | null;
  nextQuestion: Question | null;  // Store next question while showing feedback
  timeLimit: number | null;  // Time limit in minutes
  startTime: Date | null;    // When quiz started
  error: string | null;
  isLoading: boolean;
}

interface QuizContextValue extends QuizState {
  // Actions
  loadQuiz: (quizId: string) => Promise<void>;
  startQuiz: (quizId: string, name: string, email?: string) => Promise<void>;
  submitAnswer: (answer: 'A' | 'B' | 'C' | 'D') => Promise<void>;
  continueToNext: () => void;  // Move from feedback to next question
  handleTimeUp: () => void;    // Handle timer expiration
  resetQuiz: () => void;
}

const initialState: QuizState = {
  phase: 'landing',
  quizInfo: null,
  attemptId: null,
  takerName: null,
  currentQuestion: null,
  questionNum: 0,
  totalQuestions: 0,
  score: 0,
  currentDifficulty: 'medium',
  attempt: null,
  feedback: null,
  nextQuestion: null,
  timeLimit: null,
  startTime: null,
  error: null,
  isLoading: false,
};

const QuizContext = createContext<QuizContextValue | undefined>(undefined);

export function QuizProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<QuizState>(initialState);

  const loadQuiz = useCallback(async (quizId: string) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const info = await getQuizInfo(quizId);
      setState(prev => ({
        ...prev,
        quizInfo: info,
        totalQuestions: info.numQuestions,
        phase: 'landing',
        isLoading: false,
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load quiz';
      setState(prev => ({
        ...prev,
        error: message,
        phase: 'error',
        isLoading: false,
      }));
    }
  }, []);

  const startQuiz = useCallback(async (quizId: string, name: string, email?: string) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const response = await startQuizAttempt(quizId, name, email);

      // Handle case where question might be null (resumed but already answered current)
      if (!response.question) {
        // This shouldn't normally happen, but handle gracefully
        setState(prev => ({
          ...prev,
          error: 'Unable to load question. Please try again.',
          phase: 'error',
          isLoading: false,
        }));
        return;
      }

      // Map the response to Question format
      const question: Question = {
        text: response.question.question || '',
        options: response.question.options,
        questionNum: response.questionNum,
        total: response.total,
        difficulty: response.difficulty,
        type: response.question.type,
        code_snippet: response.question.code_snippet,
      };

      setState(prev => ({
        ...prev,
        attemptId: response.attemptId,
        takerName: name,
        currentQuestion: question,
        questionNum: response.questionNum,
        totalQuestions: response.total,
        score: response.score || 0,  // Preserve score when resuming
        currentDifficulty: response.difficulty,
        timeLimit: response.timeLimit,
        startTime: new Date(),  // Note: For resumed quizzes, time restarts
        phase: 'question',
        isLoading: false,
      }));

      // Log if resuming
      if (response.resumed) {
        console.log('Resumed existing quiz attempt');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start quiz';
      setState(prev => ({
        ...prev,
        error: message,
        phase: 'error',
        isLoading: false,
      }));
    }
  }, []);

  const submitAnswer = useCallback(async (answer: 'A' | 'B' | 'C' | 'D') => {
    if (!state.attemptId) return;

    setState(prev => ({ ...prev, isLoading: true }));
    try {
      const response = await submitQuizAnswer(state.attemptId, answer);

      // Create feedback object
      const feedback: AnswerFeedback = {
        isCorrect: response.correct,
        selectedAnswer: answer,
        correctAnswer: response.correctAnswer,
        explanation: response.explanation,
      };

      if (response.results) {
        // Quiz complete - show feedback then results
        const attempt: QuizAttempt = {
          id: state.attemptId,
          quizId: state.quizInfo?.quizId || '',
          takerName: state.takerName || '',
          score: response.results.score,
          total: response.results.total,
          percentage: response.results.percentage,
          passed: response.results.passed,
          startedAt: new Date().toISOString(),
          completedAt: new Date().toISOString(),
          answers: response.results.answers,
        };
        setState(prev => ({
          ...prev,
          attempt,
          score: response.results!.score,
          feedback,
          nextQuestion: null,  // No next question - quiz complete
          phase: 'feedback',
          isLoading: false,
        }));
      } else if (response.nextQuestion) {
        // Next question available - show feedback first
        const nextQ: Question = {
          text: response.nextQuestion.question,
          options: response.nextQuestion.options,
          questionNum: response.nextQuestion.questionNum,
          total: response.nextQuestion.total,
          difficulty: response.nextQuestion.difficulty,
          type: response.nextQuestion.type,
          code_snippet: response.nextQuestion.code_snippet,
        };
        setState(prev => ({
          ...prev,
          score: response.correct ? prev.score + 1 : prev.score,
          feedback,
          nextQuestion: nextQ,
          currentDifficulty: response.nextQuestion!.difficulty,
          phase: 'feedback',
          isLoading: false,
        }));
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to submit answer';
      setState(prev => ({
        ...prev,
        error: message,
        phase: 'error',
        isLoading: false,
      }));
    }
  }, [state.attemptId, state.quizInfo?.quizId, state.takerName]);

  const continueToNext = useCallback(() => {
    setState(prev => {
      if (prev.nextQuestion) {
        // Move to next question
        return {
          ...prev,
          currentQuestion: prev.nextQuestion,
          questionNum: prev.questionNum + 1,
          nextQuestion: null,
          feedback: null,
          phase: 'question',
        };
      } else {
        // No next question - show results
        return {
          ...prev,
          feedback: null,
          phase: 'results',
        };
      }
    });
  }, []);

  const handleTimeUp = useCallback(() => {
    // Time expired - show results with current score
    setState(prev => {
      const attempt: QuizAttempt = {
        id: prev.attemptId || '',
        quizId: prev.quizInfo?.quizId || '',
        takerName: prev.takerName || '',
        score: prev.score,
        total: prev.totalQuestions,
        percentage: prev.totalQuestions > 0 ? Math.round((prev.score / prev.totalQuestions) * 100) : 0,
        passed: prev.totalQuestions > 0 ? (prev.score / prev.totalQuestions) >= 0.6 : false,
        startedAt: prev.startTime?.toISOString() || new Date().toISOString(),
        completedAt: new Date().toISOString(),
        answers: [],
      };
      return {
        ...prev,
        attempt,
        error: 'Time expired! Quiz has ended.',
        phase: 'results',
        isLoading: false,
      };
    });
  }, []);

  const resetQuiz = useCallback(() => {
    setState(prev => ({
      ...initialState,
      quizInfo: prev.quizInfo,
      totalQuestions: prev.quizInfo?.numQuestions || 0,
    }));
  }, []);

  const value: QuizContextValue = {
    ...state,
    loadQuiz,
    startQuiz,
    submitAnswer,
    continueToNext,
    handleTimeUp,
    resetQuiz,
  };

  return <QuizContext.Provider value={value}>{children}</QuizContext.Provider>;
}

export function useQuiz() {
  const context = useContext(QuizContext);
  if (context === undefined) {
    throw new Error('useQuiz must be used within a QuizProvider');
  }
  return context;
}

export { QuizContext };
