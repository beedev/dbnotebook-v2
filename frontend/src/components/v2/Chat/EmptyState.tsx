import { memo } from 'react';
import { MessageSquare, Book, Upload, Sparkles } from 'lucide-react';

interface EmptyStateProps {
  hasNotebook: boolean;
  hasSources: boolean;
  notebookName?: string;
  onUploadClick?: () => void;
}

export const EmptyState = memo(function EmptyState({
  hasNotebook,
  hasSources,
  notebookName,
  onUploadClick,
}: EmptyStateProps) {
  // No notebook selected
  if (!hasNotebook) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-md text-center">
          {/* Illustration */}
          <div className="mb-6 relative">
            <div className="w-20 h-20 mx-auto rounded-2xl bg-[var(--color-bg-secondary)] border border-[var(--color-border-subtle)] flex items-center justify-center">
              <Book className="w-10 h-10 text-[var(--color-text-muted)]" />
            </div>
            <div className="absolute -right-2 -bottom-2 w-8 h-8 rounded-lg bg-[var(--color-accent-subtle)] border border-[var(--color-border-subtle)] flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-[var(--color-accent)]" />
            </div>
          </div>

          {/* Text */}
          <h2 className="text-xl font-semibold text-[var(--color-text-primary)] font-[family-name:var(--font-display)] mb-2">
            Welcome to DBNotebook
          </h2>
          <p className="text-[var(--color-text-secondary)] mb-6">
            Select a notebook from the sidebar to start chatting with your documents.
            Create a new notebook to organize your knowledge.
          </p>

          {/* Tips */}
          <div className="inline-flex flex-col gap-2 text-left bg-[var(--color-bg-secondary)] rounded-[var(--radius-lg)] p-4 border border-[var(--color-border-subtle)]">
            <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wide mb-1">
              Quick tips
            </p>
            <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
              <span className="w-5 h-5 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-accent)] flex items-center justify-center text-xs font-medium">1</span>
              Create a notebook for each project
            </div>
            <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
              <span className="w-5 h-5 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-accent)] flex items-center justify-center text-xs font-medium">2</span>
              Upload PDFs, docs, or images as sources
            </div>
            <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
              <span className="w-5 h-5 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-accent)] flex items-center justify-center text-xs font-medium">3</span>
              Ask questions and get AI-powered answers
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Notebook selected but no sources
  if (!hasSources) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-md text-center">
          {/* Illustration */}
          <div className="mb-6">
            <div className="w-20 h-20 mx-auto rounded-2xl bg-[var(--color-bg-secondary)] border-2 border-dashed border-[var(--color-border)] flex items-center justify-center">
              <Upload className="w-10 h-10 text-[var(--color-text-muted)]" />
            </div>
          </div>

          {/* Text */}
          <h2 className="text-xl font-semibold text-[var(--color-text-primary)] font-[family-name:var(--font-display)] mb-2">
            Add sources to {notebookName}
          </h2>
          <p className="text-[var(--color-text-secondary)] mb-6">
            Upload documents to start chatting. The AI will use your sources to provide accurate, contextual answers.
          </p>

          {/* Upload button */}
          {onUploadClick && (
            <button
              onClick={onUploadClick}
              className="
                inline-flex items-center gap-2 px-5 py-2.5
                bg-[var(--color-accent)]
                text-white font-medium
                rounded-[var(--radius-lg)]
                hover:bg-[var(--color-accent-hover)]
                transition-colors
                shadow-[var(--shadow-sm)]
              "
            >
              <Upload className="w-4 h-4" />
              Upload documents
            </button>
          )}

          {/* Supported formats */}
          <p className="mt-4 text-xs text-[var(--color-text-muted)]">
            Supports PDF, DOCX, PPTX, TXT, EPUB, and images
          </p>
        </div>
      </div>
    );
  }

  // Ready to chat
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-md text-center">
        {/* Illustration */}
        <div className="mb-6 relative">
          <div className="w-20 h-20 mx-auto rounded-2xl bg-[var(--color-accent-subtle)] border border-[var(--color-accent)]/20 flex items-center justify-center">
            <MessageSquare className="w-10 h-10 text-[var(--color-accent)]" />
          </div>
        </div>

        {/* Text */}
        <h2 className="text-xl font-semibold text-[var(--color-text-primary)] font-[family-name:var(--font-display)] mb-2">
          Ready to chat
        </h2>
        <p className="text-[var(--color-text-secondary)] mb-6">
          Ask anything about your documents. The AI will search through your sources and provide detailed answers with citations.
        </p>

        {/* Suggestions */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wide">
            Try asking
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {[
              'Summarize the main points',
              'What are the key findings?',
              'Compare the approaches',
            ].map((suggestion) => (
              <button
                key={suggestion}
                className="
                  px-3 py-1.5
                  text-sm text-[var(--color-text-secondary)]
                  bg-[var(--color-bg-secondary)]
                  border border-[var(--color-border)]
                  rounded-[var(--radius-full)]
                  hover:border-[var(--color-accent)]
                  hover:text-[var(--color-accent)]
                  transition-colors
                "
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
});

export default EmptyState;
