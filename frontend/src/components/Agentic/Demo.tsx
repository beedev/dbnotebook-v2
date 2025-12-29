/**
 * Demo component showcasing Agentic UI components
 * This file is for development/testing purposes only
 */

import { useState } from 'react';
import { SuggestionCard, QueryRefinement, InsightPanel, SourceSuggestion } from './index';
import type { Suggestion, Insight } from './index';

export function AgenticDemo() {
  const [showQueryRefinement, setShowQueryRefinement] = useState(true);
  const [showSourceSuggestion, setShowSourceSuggestion] = useState(true);
  const [dismissedSuggestions, setDismissedSuggestions] = useState<Set<string>>(new Set());

  // Sample data
  const suggestions: Suggestion[] = [
    {
      id: 'sug-1',
      type: 'document',
      title: 'More context recommended',
      description: 'Your notebook could benefit from additional background documentation.',
      action: {
        label: 'Upload documents',
        onClick: () => alert('Upload triggered')
      }
    },
    {
      id: 'sug-2',
      type: 'query',
      title: 'Refine your query',
      description: 'I can help make your search more specific and effective.',
      action: {
        label: 'Show suggestions',
        onClick: () => setShowQueryRefinement(true)
      }
    },
    {
      id: 'sug-3',
      type: 'action',
      title: 'Generate content',
      description: 'Create an infographic based on your documents.',
      action: {
        label: 'Go to Studio',
        onClick: () => alert('Navigate to Content Studio')
      }
    }
  ];

  const insights: Insight[] = [
    {
      type: 'stat',
      content: 'Document contains 5,234 words across 42 pages with 12 sections'
    },
    {
      type: 'warning',
      content: 'Some technical terms detected that may need clarification'
    },
    {
      type: 'tip',
      content: 'Try asking specific questions about the methodology section for detailed insights'
    },
    {
      type: 'stat',
      content: 'Estimated reading time: 21 minutes'
    }
  ];

  const handleDismissSuggestion = (id: string) => {
    setDismissedSuggestions(prev => new Set([...prev, id]));
  };

  const visibleSuggestions = suggestions.filter(s => !dismissedSuggestions.has(s.id));

  return (
    <div className="min-h-screen bg-void p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-text mb-2 font-[family-name:var(--font-display)]">
            Agentic Components Demo
          </h1>
          <p className="text-text-muted">
            Interactive showcase of intelligent UI components
          </p>
        </div>

        {/* Section: Suggestion Cards */}
        <section className="space-y-4">
          <div className="mb-4">
            <h2 className="text-xl font-semibold text-text mb-1 font-[family-name:var(--font-display)]">
              Suggestion Cards
            </h2>
            <p className="text-sm text-text-muted">
              Proactive suggestions with dismissible actions
            </p>
          </div>

          <div className="space-y-3">
            {visibleSuggestions.map((suggestion, index) => (
              <SuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                onDismiss={handleDismissSuggestion}
                variant={index === 0 ? 'floating' : 'inline'}
              />
            ))}
            {visibleSuggestions.length === 0 && (
              <p className="text-center text-text-muted py-4">
                All suggestions dismissed. Refresh to reset.
              </p>
            )}
          </div>
        </section>

        {/* Section: Query Refinement */}
        {showQueryRefinement && (
          <section className="space-y-4">
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-text mb-1 font-[family-name:var(--font-display)]">
                Query Refinement
              </h2>
              <p className="text-sm text-text-muted">
                AI-powered query improvement suggestions
              </p>
            </div>

            <QueryRefinement
              originalQuery="what is ai"
              suggestions={[
                'What are the fundamental concepts and principles of artificial intelligence?',
                'How does artificial intelligence work in modern applications and systems?',
                'What are the different types of AI and their specific use cases?'
              ]}
              confidence={0.85}
              onSelectSuggestion={(query) => {
                alert(`Using refined query: "${query}"`);
                setShowQueryRefinement(false);
              }}
              onKeepOriginal={() => {
                alert('Keeping original query');
                setShowQueryRefinement(false);
              }}
            />
          </section>
        )}

        {/* Section: Insight Panel */}
        <section className="space-y-4">
          <div className="mb-4">
            <h2 className="text-xl font-semibold text-text mb-1 font-[family-name:var(--font-display)]">
              Insight Panel
            </h2>
            <p className="text-sm text-text-muted">
              Document analysis insights with collapsible interface
            </p>
          </div>

          <InsightPanel
            documentName="AI_Research_Paper_2024.pdf"
            insights={insights}
            onExplore={() => alert('Exploring document')}
            onDismiss={() => alert('Panel dismissed')}
          />
        </section>

        {/* Section: Source Suggestion */}
        {showSourceSuggestion && (
          <section className="space-y-4">
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-text mb-1 font-[family-name:var(--font-display)]">
                Source Suggestion
              </h2>
              <p className="text-sm text-text-muted">
                Smart suggestions for missing knowledge sources
              </p>
            </div>

            <SourceSuggestion
              reason="Your question requires information about recent AI developments and research papers not currently in your notebook"
              suggestedQuery="latest artificial intelligence breakthroughs 2024 research papers"
              onSearchWeb={(query) => {
                alert(`Searching web for: "${query}"`);
                setShowSourceSuggestion(false);
              }}
              onUpload={() => {
                alert('Opening upload dialog');
                setShowSourceSuggestion(false);
              }}
              onSkip={() => {
                alert('Skipping suggestion');
                setShowSourceSuggestion(false);
              }}
            />
          </section>
        )}

        {/* Reset button */}
        <div className="flex justify-center pt-8 border-t border-void-surface">
          <button
            onClick={() => {
              setShowQueryRefinement(true);
              setShowSourceSuggestion(true);
              setDismissedSuggestions(new Set());
            }}
            className="px-6 py-2 text-sm font-medium text-glow hover:text-glow-bright bg-glow/5 hover:bg-glow/10 border border-glow/20 hover:border-glow/40 rounded-lg transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-glow"
          >
            Reset Demo
          </button>
        </div>
      </div>
    </div>
  );
}

export default AgenticDemo;
