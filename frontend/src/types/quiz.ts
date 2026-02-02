/**
 * Quiz feature TypeScript types
 *
 * Types for the adaptive Q&A quiz system including:
 * - Quiz configuration (admin)
 * - Questions and answers (including code-based questions)
 * - Quiz attempts (test-taker)
 * - Results and statistics
 */

// Difficulty modes
export type DifficultyMode = 'adaptive' | 'easy' | 'medium' | 'hard';
export type DifficultyLevel = 'easy' | 'medium' | 'hard';

// Question source - where questions are generated from
export type QuestionSource = 'notebook_only' | 'extended';

// Question types
export type QuestionType = 'multiple_choice' | 'code_output' | 'code_fill_blank' | 'code_bug_fix';

/**
 * Quiz configuration created by admin
 */
export interface Quiz {
  id: string;
  notebookId: string;
  notebookName: string;
  title: string;
  numQuestions: number;
  difficultyMode: DifficultyMode;
  timeLimitMinutes: number | null;
  isActive: boolean;
  attemptCount: number;
  link: string;
  createdAt: string;
  questionSource?: QuestionSource;
  includeCodeQuestions?: boolean;
}

/**
 * Single question displayed to test-taker
 */
export interface Question {
  text: string;
  question?: string; // Alias for text (backend compatibility)
  options: string[];
  questionNum?: number;
  total?: number;
  difficulty: DifficultyLevel;
  type?: QuestionType;
  code_snippet?: string;  // Markdown code block for code questions
}

/**
 * Full question data (includes answer - for results)
 */
export interface QuestionWithAnswer extends Question {
  correctAnswer: string;
  explanation: string;
  topic: string;
  type?: QuestionType;
  code_snippet?: string;
}

/**
 * Answer record for a single question
 */
export interface AnswerRecord {
  question: string;
  options: string[];
  userAnswer: string | null;
  correctAnswer: string;
  correct: boolean;
  explanation: string;
  topic: string;
  type?: QuestionType;
  code_snippet?: string;
}

/**
 * Quiz attempt by a test-taker
 */
export interface QuizAttempt {
  id: string;
  quizId: string;
  takerName: string;
  score: number;
  total: number;
  percentage: number;
  passed: boolean;
  startedAt: string;
  completedAt: string | null;
  answers?: AnswerRecord[];
}

/**
 * Quiz results with all answers (for results page)
 */
export interface QuizResults {
  score: number;
  total: number;
  percentage: number;
  passed: boolean;
  answers: AnswerRecord[];
}

/**
 * Statistics for a quiz (admin dashboard)
 */
export interface QuizStatistics {
  totalAttempts: number;
  completedAttempts: number;
  avgScore: number;
  avgPercentage: number;
  passRate: number;
}

/**
 * Full quiz results response (admin)
 */
export interface QuizResultsResponse {
  quiz: Quiz;
  statistics: QuizStatistics;
  attempts: QuizAttempt[];
}

/**
 * Quiz public info (landing page)
 */
export interface QuizPublicInfo {
  quizId: string;
  title: string;
  numQuestions: number;
  difficultyMode: DifficultyMode;
  timeLimit: number | null;
  hasTimeLimit: boolean;
  questionSource?: QuestionSource;
  includeCodeQuestions?: boolean;
}

/**
 * Start attempt response
 */
export interface StartAttemptResponse {
  attemptId: string;
  quizTitle: string;
  resumed: boolean;
  question: QuestionWithAnswer | null;
  questionNum: number;
  total: number;
  score?: number;
  timeLimit: number | null;
  difficulty: DifficultyLevel;
}

/**
 * Submit answer response (during quiz)
 */
export interface SubmitAnswerResponse {
  correct: boolean;
  explanation: string;
  correctAnswer: string;
  completed: boolean;
  nextQuestion?: {
    question: string;
    options: string[];
    questionNum: number;
    total: number;
    difficulty: DifficultyLevel;
    type?: QuestionType;
    code_snippet?: string;
  };
  results?: QuizResults;
}

/**
 * Attempt status response (for resuming)
 */
export interface AttemptStatusResponse {
  completed: boolean;
  quizTitle?: string;
  takerName?: string;
  questionNum?: number;
  total?: number;
  score?: number;
  currentQuestion?: {
    question: string;
    options: string[];
    difficulty: DifficultyLevel;
  };
  results?: QuizResults;
}

// === Improvement Suggestions ===

/**
 * LLM-generated suggestion for extended quizzes
 */
export interface LLMSuggestion {
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  topics: string[];
}

/**
 * Study resource recommendation
 */
export interface StudyResource {
  type: 'concept' | 'practice' | 'reference';
  title: string;
  description: string;
}

/**
 * Document section for notebook_only quizzes
 */
export interface DocumentSection {
  topic: string;
  source_id: string;
  filename: string;
  preview: string;
  relevance_score: number;
}

/**
 * Topic with related document sections
 */
export interface TopicSections {
  topic: string;
  documents: DocumentSection[];
}

/**
 * Base improvement suggestions response
 */
export interface BaseImprovementSuggestions {
  type: 'llm_generated' | 'document_linked' | 'perfect_score';
  wrong_count?: number;
  message?: string;
  summary?: string;
  weak_areas?: string[];
}

/**
 * LLM-generated suggestions response (for extended quizzes)
 */
export interface LLMImprovementSuggestions extends BaseImprovementSuggestions {
  type: 'llm_generated';
  total_topics?: string[];
  suggestions: LLMSuggestion[];
  resources: StudyResource[];
}

/**
 * Document-linked suggestions response (for notebook_only quizzes)
 */
export interface DocumentImprovementSuggestions extends BaseImprovementSuggestions {
  type: 'document_linked';
  sections: TopicSections[];
  total_sections?: number;
}

/**
 * Perfect score response (no suggestions needed)
 */
export interface PerfectScoreSuggestions extends BaseImprovementSuggestions {
  type: 'perfect_score';
  message: string;
  suggestions: never[];
}

/**
 * Union type for all suggestion responses
 */
export type ImprovementSuggestions =
  | LLMImprovementSuggestions
  | DocumentImprovementSuggestions
  | PerfectScoreSuggestions;

/**
 * API response for improvement suggestions
 */
export interface ImprovementSuggestionsResponse extends QuizApiResponse {
  type?: 'llm_generated' | 'document_linked' | 'perfect_score';
  wrong_count?: number;
  message?: string;
  summary?: string;
  weak_areas?: string[];
  suggestions?: LLMSuggestion[];
  resources?: StudyResource[];
  sections?: TopicSections[];
  total_sections?: number;
}

// === Request types ===

export interface CreateQuizRequest {
  notebookId: string;
  title: string;
  numQuestions?: number;
  difficultyMode?: DifficultyMode;
  timeLimit?: number | null;
  llmModel?: string | null; // Optional: "provider:model" format
  questionSource?: QuestionSource;
  includeCodeQuestions?: boolean;
}

/**
 * Available LLM model option
 */
export interface LLMModelOption {
  value: string;
  label: string;
}

/**
 * Get available models response
 */
export interface GetModelsResponse extends QuizApiResponse {
  models?: LLMModelOption[];
  default?: string;
}

export interface StartAttemptRequest {
  takerName: string;
  takerEmail?: string;
}

export interface SubmitAnswerRequest {
  answer: 'A' | 'B' | 'C' | 'D';
}

// === API Response wrappers ===

export interface QuizApiResponse {
  success: boolean;
  error?: string;
}

export interface CreateQuizResponse extends QuizApiResponse {
  quizId?: string;
  link?: string;
  title?: string;
  numQuestions?: number;
  difficultyMode?: DifficultyMode;
  timeLimit?: number | null;
}

export interface ListQuizzesResponse extends QuizApiResponse {
  quizzes?: Quiz[];
}

export interface QuizInfoResponse extends QuizApiResponse, Partial<QuizPublicInfo> {}

// === Quiz state for context ===

export type QuizTakingState =
  | 'landing'      // Entering name
  | 'loading'      // Loading question
  | 'question'     // Answering question
  | 'feedback'     // Showing answer feedback
  | 'complete';    // Quiz finished

export interface QuizTakingContextState {
  state: QuizTakingState;
  quizInfo: QuizPublicInfo | null;
  attemptId: string | null;
  takerName: string;
  currentQuestion: Question | null;
  questionNum: number;
  totalQuestions: number;
  score: number;
  timeLimit: number | null;
  startTime: Date | null;
  lastFeedback: {
    correct: boolean;
    explanation: string;
    correctAnswer: string;
  } | null;
  results: QuizResults | null;
  error: string | null;
  currentQuestionType?: QuestionType;
  currentCodeSnippet?: string;
}
