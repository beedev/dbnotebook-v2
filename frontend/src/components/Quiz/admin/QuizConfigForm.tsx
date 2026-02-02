import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Sparkles, Code2, Zap } from 'lucide-react';
import { getNotebooks, createQuiz, getQuizModels } from '../../../services/api';
import type { Notebook } from '../../../types';
import type { DifficultyMode, QuestionSource, CreateQuizRequest, LLMModelOption } from '../../../types/quiz';

export function QuizConfigForm() {
  const navigate = useNavigate();
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [isLoadingNotebooks, setIsLoadingNotebooks] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState('');
  const [selectedNotebookId, setSelectedNotebookId] = useState<string>('');
  const [numQuestions, setNumQuestions] = useState(10);
  const [difficultyMode, setDifficultyMode] = useState<DifficultyMode>('adaptive');
  const [timeLimit, setTimeLimit] = useState<number | null>(null);
  const [hasTimeLimit, setHasTimeLimit] = useState(false);
  const [llmModel, setLlmModel] = useState<string>('');
  const [availableModels, setAvailableModels] = useState<LLMModelOption[]>([]);
  const [questionSource, setQuestionSource] = useState<QuestionSource>('notebook_only');
  const [includeCodeQuestions, setIncludeCodeQuestions] = useState(false);

  // Load notebooks and available models
  useEffect(() => {
    async function loadNotebooks() {
      try {
        const response = await getNotebooks();
        setNotebooks(response.notebooks);
        if (response.notebooks.length > 0) {
          setSelectedNotebookId(response.notebooks[0].id);
        }
      } catch (err) {
        setError('Failed to load notebooks');
        console.error(err);
      } finally {
        setIsLoadingNotebooks(false);
      }
    }

    async function loadModels() {
      try {
        const models = await getQuizModels();
        setAvailableModels(models);
      } catch (err) {
        console.error('Failed to load LLM models:', err);
        // Use default if loading fails
        setAvailableModels([{ value: '', label: 'Default' }]);
      }
    }

    loadNotebooks();
    loadModels();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedNotebookId || !title.trim()) return;

    setIsCreating(true);
    setError(null);

    try {
      const request: CreateQuizRequest = {
        notebookId: selectedNotebookId,
        title: title.trim(),
        numQuestions,
        difficultyMode,
        timeLimit: hasTimeLimit ? timeLimit : null,
        llmModel: llmModel || null,
        questionSource,
        includeCodeQuestions,
      };

      const result = await createQuiz(request);

      // Navigate to dashboard with success message
      navigate('/quizzes', {
        state: { created: true, quizId: result.quizId, link: result.link },
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create quiz';
      setError(message);
    } finally {
      setIsCreating(false);
    }
  };

  if (isLoadingNotebooks) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const selectedNotebook = notebooks.find(n => n.id === selectedNotebookId);

  return (
    <div className="max-w-2xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate('/quizzes')}
          className="p-2 hover:bg-void-surface rounded-lg text-text-muted hover:text-text transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-2xl font-semibold text-text">Create New Quiz</h1>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Quiz Title */}
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Quiz Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., HR Policy Assessment"
            className="w-full px-4 py-2.5 bg-void-surface border border-void-lighter rounded-lg text-text placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary/50"
            required
          />
        </div>

        {/* Select Notebook */}
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Source Notebook
          </label>
          {notebooks.length === 0 ? (
            <p className="text-text-muted">
              No notebooks available. Create a notebook with documents first.
            </p>
          ) : (
            <select
              value={selectedNotebookId}
              onChange={(e) => setSelectedNotebookId(e.target.value)}
              className="w-full px-4 py-2.5 bg-void-surface border border-void-lighter rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-primary/50"
              required
            >
              {notebooks.map((nb) => (
                <option key={nb.id} value={nb.id}>
                  {nb.name} ({nb.documentCount || 0} documents)
                </option>
              ))}
            </select>
          )}
          {selectedNotebook && (selectedNotebook.documentCount || 0) === 0 && (
            <p className="mt-2 text-sm text-yellow-400">
              This notebook has no documents. Add documents before creating a quiz.
            </p>
          )}
        </div>

        {/* Number of Questions */}
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Number of Questions
          </label>
          <div className="flex gap-3">
            {[5, 10, 15, 20].map((num) => (
              <button
                key={num}
                type="button"
                onClick={() => setNumQuestions(num)}
                className={`px-4 py-2 rounded-lg border transition-colors ${
                  numQuestions === num
                    ? 'bg-primary border-primary text-white'
                    : 'bg-void-surface border-void-lighter text-text hover:border-primary/50'
                }`}
              >
                {num}
              </button>
            ))}
          </div>
        </div>

        {/* Difficulty Mode */}
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Difficulty Mode
          </label>
          <div className="space-y-2">
            {[
              { value: 'adaptive', label: 'Adaptive', description: 'Adjusts based on performance' },
              { value: 'easy', label: 'Easy Only', description: 'Basic recall and definitions' },
              { value: 'medium', label: 'Medium Only', description: 'Understanding and application' },
              { value: 'hard', label: 'Hard Only', description: 'Analysis and synthesis' },
            ].map((option) => (
              <label
                key={option.value}
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  difficultyMode === option.value
                    ? 'bg-primary/10 border-primary'
                    : 'bg-void-surface border-void-lighter hover:border-primary/30'
                }`}
              >
                <input
                  type="radio"
                  name="difficultyMode"
                  value={option.value}
                  checked={difficultyMode === option.value}
                  onChange={(e) => setDifficultyMode(e.target.value as DifficultyMode)}
                  className="mt-1"
                />
                <div>
                  <span className="font-medium text-text">{option.label}</span>
                  <p className="text-sm text-text-muted">{option.description}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Time Limit */}
        <div>
          <label className="block text-sm font-medium text-text mb-2">
            Time Limit (optional)
          </label>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={hasTimeLimit}
                onChange={(e) => {
                  setHasTimeLimit(e.target.checked);
                  if (e.target.checked && !timeLimit) {
                    setTimeLimit(15);
                  }
                }}
                className="rounded"
              />
              <span className="text-text">Enable time limit</span>
            </label>
            {hasTimeLimit && (
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={timeLimit || ''}
                  onChange={(e) => setTimeLimit(parseInt(e.target.value) || null)}
                  min={1}
                  max={120}
                  className="w-20 px-3 py-2 bg-void-surface border border-void-lighter rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                <span className="text-text-muted">minutes</span>
              </div>
            )}
          </div>
        </div>

        {/* AI Model Selection */}
        {availableModels.length > 1 && (
          <div>
            <label className="block text-sm font-medium text-text mb-2">
              <span className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-primary" />
                AI Model for Questions
              </span>
            </label>
            <select
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              className="w-full px-4 py-2.5 bg-void-surface border border-void-lighter rounded-lg text-text focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {availableModels.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
            <p className="mt-1.5 text-sm text-text-muted">
              Choose which AI model generates quiz questions. Different models may produce different question styles.
            </p>
          </div>
        )}

        {/* Question Options Divider */}
        <div className="border-t border-void-lighter pt-6">
          <h3 className="text-sm font-medium text-text mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            Advanced Question Options
          </h3>

          {/* Question Source */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-text mb-2">
              Question Source
            </label>
            <div className="space-y-2">
              {[
                {
                  value: 'notebook_only',
                  label: 'From Notebook Only',
                  description: 'Questions are generated strictly from content in the notebook'
                },
                {
                  value: 'extended',
                  label: 'Extended (Recommended for deeper testing)',
                  description: 'Questions may include related topics and concepts beyond notebook content'
                },
              ].map((option) => (
                <label
                  key={option.value}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    questionSource === option.value
                      ? 'bg-primary/10 border-primary'
                      : 'bg-void-surface border-void-lighter hover:border-primary/30'
                  }`}
                >
                  <input
                    type="radio"
                    name="questionSource"
                    value={option.value}
                    checked={questionSource === option.value}
                    onChange={(e) => setQuestionSource(e.target.value as QuestionSource)}
                    className="mt-1"
                  />
                  <div>
                    <span className="font-medium text-text">{option.label}</span>
                    <p className="text-sm text-text-muted">{option.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Include Code Questions */}
          <div>
            <label className="flex items-start gap-3 p-4 rounded-lg border border-void-lighter bg-void-surface cursor-pointer hover:border-primary/30 transition-colors">
              <input
                type="checkbox"
                checked={includeCodeQuestions}
                onChange={(e) => setIncludeCodeQuestions(e.target.checked)}
                className="mt-0.5 rounded"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-primary" />
                  <span className="font-medium text-text">Include code-based questions</span>
                </div>
                <p className="text-sm text-text-muted mt-1">
                  When enabled, generates code snippets for technical content
                  (output prediction, fill-in-blank, bug identification).
                  Only applies if notebook contains programming content.
                </p>
              </div>
            </label>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-4 pt-4 border-t border-void-lighter">
          <button
            type="button"
            onClick={() => navigate('/quizzes')}
            className="px-6 py-2.5 text-text-muted hover:text-text transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isCreating || !selectedNotebookId || !title.trim()}
            className="px-6 py-2.5 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isCreating && <Loader2 className="w-4 h-4 animate-spin" />}
            Create Quiz
          </button>
        </div>
      </form>
    </div>
  );
}
