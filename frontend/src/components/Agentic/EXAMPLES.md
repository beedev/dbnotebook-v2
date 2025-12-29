# Agentic Components - Usage Examples

Practical examples showing how to integrate Agentic components into your application.

## Example 1: Simple Suggestion Flow

Display a suggestion after document upload:

```tsx
import { SuggestionCard } from '@/components/Agentic';
import type { Suggestion } from '@/components/Agentic';

function DocumentUploadSuccess() {
  const suggestion: Suggestion = {
    id: 'post-upload-1',
    type: 'action',
    title: 'Ready to chat',
    description: 'Your document has been processed. Start asking questions!',
    action: {
      label: 'Ask a question',
      onClick: () => {
        document.querySelector('textarea')?.focus();
      }
    }
  };

  return (
    <div className="space-y-4">
      <div className="text-success">✓ Document uploaded successfully</div>
      <SuggestionCard suggestion={suggestion} />
    </div>
  );
}
```

## Example 2: Query Refinement on Poor Results

Show query refinement when search returns few results:

```tsx
import { useState } from 'react';
import { QueryRefinement } from '@/components/Agentic';

function ChatContainer({ searchResults, query }) {
  const [showRefinement, setShowRefinement] = useState(false);

  // Trigger refinement if results are poor
  useEffect(() => {
    if (searchResults.length < 3 && query.length > 5) {
      setShowRefinement(true);
    }
  }, [searchResults, query]);

  const handleRefinedQuery = async (newQuery: string) => {
    await performSearch(newQuery);
    setShowRefinement(false);
  };

  if (!showRefinement) return null;

  return (
    <QueryRefinement
      originalQuery={query}
      suggestions={[
        `What are the detailed aspects of ${query}?`,
        `Explain ${query} in the context of this document`,
        `Find specific examples of ${query}`
      ]}
      confidence={0.75}
      onSelectSuggestion={handleRefinedQuery}
      onKeepOriginal={() => setShowRefinement(false)}
    />
  );
}
```

## Example 3: Document Insights Panel

Show insights after document processing:

```tsx
import { InsightPanel } from '@/components/Agentic';
import type { Insight } from '@/components/Agentic';

function DocumentAnalysis({ document, analysis }) {
  const insights: Insight[] = [
    {
      type: 'stat',
      content: `${analysis.wordCount} words, ${analysis.pageCount} pages, ${analysis.readingTime} min read`
    },
    {
      type: 'stat',
      content: `${analysis.sections} sections identified with ${analysis.topics.length} main topics`
    }
  ];

  // Add warnings if needed
  if (analysis.complexTerms > 10) {
    insights.push({
      type: 'warning',
      content: `Document contains ${analysis.complexTerms} technical terms that may need explanation`
    });
  }

  // Add tips
  insights.push({
    type: 'tip',
    content: 'Try asking about specific sections or concepts for detailed explanations'
  });

  return (
    <InsightPanel
      documentName={document.filename}
      insights={insights}
      onExplore={() => {
        // Navigate to document viewer or detailed analysis
        navigate(`/documents/${document.id}`);
      }}
      onDismiss={() => {
        localStorage.setItem(`insight-dismissed-${document.id}`, 'true');
      }}
    />
  );
}
```

## Example 4: Source Suggestion on Knowledge Gap

Detect knowledge gaps and suggest sources:

```tsx
import { SourceSuggestion } from '@/components/Agentic';

function KnowledgeGapDetector({ query, searchResults }) {
  const [showSuggestion, setShowSuggestion] = useState(false);
  const [gapInfo, setGapInfo] = useState(null);

  useEffect(() => {
    // Detect knowledge gap
    if (searchResults.confidence < 0.5) {
      const topics = extractTopics(query);
      setGapInfo({
        reason: `Your query about "${topics.join(', ')}" requires information not found in your current documents`,
        query: `${topics.join(' ')} comprehensive guide latest research`
      });
      setShowSuggestion(true);
    }
  }, [searchResults, query]);

  if (!showSuggestion || !gapInfo) return null;

  return (
    <SourceSuggestion
      reason={gapInfo.reason}
      suggestedQuery={gapInfo.query}
      onSearchWeb={(searchQuery) => {
        navigate(`/web-search?q=${encodeURIComponent(searchQuery)}`);
      }}
      onUpload={() => {
        openUploadDialog();
      }}
      onSkip={() => {
        setShowSuggestion(false);
      }}
    />
  );
}
```

## Example 5: Contextual Suggestions Based on State

Provide different suggestions based on application state:

```tsx
import { SuggestionCard } from '@/components/Agentic';
import type { Suggestion } from '@/components/Agentic';

function ContextualSuggestions({ notebook, documents, hasAskedQuestions }) {
  const getSuggestions = (): Suggestion[] => {
    // No documents yet
    if (documents.length === 0) {
      return [{
        id: 'sug-no-docs',
        type: 'document',
        title: 'Add your first document',
        description: 'Upload PDFs, documents, or import from web to get started',
        action: {
          label: 'Upload documents',
          onClick: () => openUploadDialog()
        }
      }];
    }

    // Has documents but no questions
    if (!hasAskedQuestions) {
      return [{
        id: 'sug-first-question',
        type: 'query',
        title: 'Ask your first question',
        description: 'Try asking about key topics, summaries, or specific details',
        action: {
          label: 'See examples',
          onClick: () => showExampleQuestions()
        }
      }];
    }

    // Advanced suggestions
    return [{
      id: 'sug-generate-content',
      type: 'action',
      title: 'Generate visual content',
      description: 'Create infographics or mind maps from your documents',
      action: {
        label: 'Open Content Studio',
        onClick: () => navigate('/studio')
      }
    }];
  };

  return (
    <div className="space-y-3">
      {getSuggestions().map(sug => (
        <SuggestionCard
          key={sug.id}
          suggestion={sug}
          variant="inline"
        />
      ))}
    </div>
  );
}
```

## Example 6: Multi-Component Integration

Combine multiple components for a rich experience:

```tsx
import { useState } from 'react';
import {
  SuggestionCard,
  QueryRefinement,
  InsightPanel,
  SourceSuggestion
} from '@/components/Agentic';

function IntelligentChatInterface() {
  const [activeSuggestions, setActiveSuggestions] = useState<Suggestion[]>([]);
  const [showQueryRefinement, setShowQueryRefinement] = useState(false);
  const [documentInsights, setDocumentInsights] = useState<Insight[]>([]);
  const [showSourceSuggestion, setShowSourceSuggestion] = useState(false);

  // Called after each chat response
  const handleChatResponse = (response: AgenticChatResponse) => {
    // Show proactive suggestions
    if (response.suggestions) {
      setActiveSuggestions(response.suggestions);
    }

    // Show query refinement if low confidence
    if (response.confidence < 0.6 && response.refinedQueries) {
      setShowQueryRefinement(true);
    }

    // Show source suggestion if knowledge gap
    if (response.knowledgeGap) {
      setShowSourceSuggestion(true);
    }
  };

  // Called after document upload
  const handleDocumentUploaded = (insights: Insight[]) => {
    setDocumentInsights(insights);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Active suggestions */}
      {activeSuggestions.map(sug => (
        <SuggestionCard
          key={sug.id}
          suggestion={sug}
          onDismiss={(id) => {
            setActiveSuggestions(prev => prev.filter(s => s.id !== id));
          }}
          variant="floating"
        />
      ))}

      {/* Query refinement */}
      {showQueryRefinement && (
        <QueryRefinement
          originalQuery={currentQuery}
          suggestions={refinedQueries}
          confidence={queryConfidence}
          onSelectSuggestion={handleRefinedQuery}
          onKeepOriginal={() => setShowQueryRefinement(false)}
        />
      )}

      {/* Document insights */}
      {documentInsights.length > 0 && (
        <InsightPanel
          documentName={lastUploadedDocument}
          insights={documentInsights}
          onExplore={exploreDocument}
          onDismiss={() => setDocumentInsights([])}
        />
      )}

      {/* Source suggestion */}
      {showSourceSuggestion && (
        <SourceSuggestion
          reason={knowledgeGapReason}
          suggestedQuery={suggestedSearchQuery}
          onSearchWeb={handleWebSearch}
          onUpload={openUploadDialog}
          onSkip={() => setShowSourceSuggestion(false)}
        />
      )}

      {/* Main chat interface */}
      <ChatMessages messages={messages} />
      <ChatInput onSend={handleSendMessage} />
    </div>
  );
}
```

## Example 7: Persistent Suggestions with Local Storage

Remember dismissed suggestions across sessions:

```tsx
import { useState, useEffect } from 'react';
import { SuggestionCard } from '@/components/Agentic';

function PersistentSuggestions() {
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  // Load dismissed IDs from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('dismissed-suggestions');
    if (stored) {
      setDismissedIds(new Set(JSON.parse(stored)));
    }
  }, []);

  const handleDismiss = (id: string) => {
    const updated = new Set([...dismissedIds, id]);
    setDismissedIds(updated);
    localStorage.setItem('dismissed-suggestions', JSON.stringify([...updated]));
  };

  const allSuggestions = generateSuggestions();
  const visibleSuggestions = allSuggestions.filter(
    s => !dismissedIds.has(s.id)
  );

  return (
    <div className="space-y-3">
      {visibleSuggestions.map(sug => (
        <SuggestionCard
          key={sug.id}
          suggestion={sug}
          onDismiss={handleDismiss}
        />
      ))}
    </div>
  );
}
```

## Example 8: Animated Entry/Exit

Smooth animations when suggestions appear and disappear:

```tsx
import { AnimatePresence, motion } from 'framer-motion';
import { SuggestionCard } from '@/components/Agentic';

function AnimatedSuggestions({ suggestions }) {
  return (
    <AnimatePresence mode="popLayout">
      {suggestions.map((sug, index) => (
        <motion.div
          key={sug.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, x: 100 }}
          transition={{ delay: index * 0.1 }}
        >
          <SuggestionCard
            suggestion={sug}
            onDismiss={handleDismiss}
            variant="floating"
          />
        </motion.div>
      ))}
    </AnimatePresence>
  );
}
```

## Example 9: Accessibility-First Implementation

Ensure keyboard navigation and screen reader support:

```tsx
import { useRef } from 'react';
import { QueryRefinement } from '@/components/Agentic';

function AccessibleQueryRefinement({ onClose }) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Trap focus within refinement component
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  return (
    <div role="dialog" aria-labelledby="refinement-title">
      <QueryRefinement
        originalQuery={query}
        suggestions={suggestions}
        confidence={confidence}
        onSelectSuggestion={handleSelect}
        onKeepOriginal={onClose}
      />
      <div className="sr-only" aria-live="polite">
        Query refinement suggestions available. Press Escape to dismiss.
      </div>
    </div>
  );
}
```

## Example 10: Mobile-Optimized Layout

Responsive design for mobile devices:

```tsx
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { SuggestionCard } from '@/components/Agentic';

function MobileSuggestions({ suggestions }) {
  const isMobile = useMediaQuery('(max-width: 768px)');

  return (
    <div className={`
      ${isMobile ? 'fixed bottom-4 left-4 right-4 z-50' : 'relative'}
      space-y-2
    `}>
      {suggestions.map((sug, index) => (
        <SuggestionCard
          key={sug.id}
          suggestion={sug}
          variant={isMobile && index === 0 ? 'floating' : 'inline'}
          onDismiss={handleDismiss}
        />
      ))}
    </div>
  );
}
```

---

**Note:** These examples assume you have appropriate API endpoints and state management set up. Adjust import paths and function names to match your project structure.
