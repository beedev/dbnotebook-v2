# Agentic Components

React UI components for agentic features in DBNotebook. These components provide intelligent, proactive user interactions for document analysis, query refinement, and content suggestions.

## Components

### SuggestionCard

A dismissible card component that displays AI-generated suggestions to the user.

**Props:**
- `suggestion: Suggestion` - Suggestion object with id, type, title, description, and optional action
- `onDismiss?: (id: string) => void` - Callback when suggestion is dismissed
- `variant?: 'inline' | 'floating'` - Display variant (default: 'inline')

**Usage:**
```tsx
import { SuggestionCard } from './components/Agentic';

const suggestion = {
  id: '1',
  type: 'document',
  title: 'Consider adding more context',
  description: 'Your document might benefit from additional background information.',
  action: {
    label: 'Upload more documents',
    onClick: () => console.log('Action clicked')
  }
};

<SuggestionCard
  suggestion={suggestion}
  onDismiss={(id) => console.log('Dismissed:', id)}
  variant="inline"
/>
```

### QueryRefinement

Shows query improvement suggestions with confidence indicators.

**Props:**
- `originalQuery: string` - The user's original query
- `suggestions: string[]` - Array of refined query suggestions
- `confidence: number` - Confidence score (0-1)
- `onSelectSuggestion: (query: string) => void` - Callback when suggestion is selected
- `onKeepOriginal: () => void` - Callback to keep original query

**Usage:**
```tsx
import { QueryRefinement } from './components/Agentic';

<QueryRefinement
  originalQuery="what is ai"
  suggestions={[
    'What are the fundamental concepts of artificial intelligence?',
    'How does artificial intelligence work in modern applications?'
  ]}
  confidence={0.85}
  onSelectSuggestion={(query) => console.log('Using:', query)}
  onKeepOriginal={() => console.log('Keeping original')}
/>
```

### InsightPanel

Collapsible panel displaying document insights after upload.

**Props:**
- `documentName: string` - Name of the analyzed document
- `insights: Insight[]` - Array of insights (type: 'stat' | 'warning' | 'tip')
- `onExplore?: () => void` - Optional callback to explore document
- `onDismiss?: () => void` - Optional callback to dismiss panel

**Usage:**
```tsx
import { InsightPanel } from './components/Agentic';

const insights = [
  { type: 'stat', content: 'Document contains 5,234 words and 42 pages' },
  { type: 'warning', content: 'Some technical terms may need clarification' },
  { type: 'tip', content: 'Try asking specific questions about the methodology section' }
];

<InsightPanel
  documentName="Research_Paper.pdf"
  insights={insights}
  onExplore={() => console.log('Exploring document')}
  onDismiss={() => console.log('Panel dismissed')}
/>
```

### SourceSuggestion

Suggests documents to add based on detected knowledge gaps.

**Props:**
- `reason: string` - Explanation why the source is suggested
- `suggestedQuery: string` - Suggested search query
- `onSearchWeb: (query: string) => void` - Callback to search web
- `onUpload: () => void` - Callback to upload document
- `onSkip: () => void` - Callback to skip suggestion

**Usage:**
```tsx
import { SourceSuggestion } from './components/Agentic';

<SourceSuggestion
  reason="Your question requires information about recent AI developments not in your documents"
  suggestedQuery="latest AI breakthroughs 2024"
  onSearchWeb={(query) => console.log('Searching:', query)}
  onUpload={() => console.log('Opening upload dialog')}
  onSkip={() => console.log('Skipping suggestion')}
/>
```

## Design System

All components follow the DBNotebook design system:

**Colors:**
- Primary accent: `text-glow`, `bg-glow`, `border-glow`
- Secondary accent: `text-nebula`, `bg-nebula`, `border-nebula`
- Backgrounds: `bg-void-light`, `bg-void-surface`, `bg-void-lighter`
- Text: `text-text`, `text-text-muted`, `text-text-dim`
- Status: `text-success`, `text-warning`, `text-danger`

**Fonts:**
- Display/Headers: `font-[family-name:var(--font-display)]` (JetBrains Mono)
- Body: Default (DM Sans)
- Code: `font-[family-name:var(--font-code)]` (Fira Code)

**Animations:**
- Slide up: `animate-[slide-up_0.4s_ease-out]`
- Slide in right: `animate-[slide-in-right_0.3s_ease-out]`
- Fade in: `animate-[fade-in_0.3s_ease-out]`

**Accessibility:**
- All interactive elements have focus-visible states
- Proper ARIA labels and roles
- Keyboard navigation support
- Semantic HTML structure
- Color contrast compliant with WCAG AA

## Integration Example

Here's a complete example showing how these components might work together:

```tsx
import { useState } from 'react';
import {
  SuggestionCard,
  QueryRefinement,
  InsightPanel,
  SourceSuggestion,
  type Suggestion,
  type Insight
} from './components/Agentic';

function ChatInterface() {
  const [showQueryRefinement, setShowQueryRefinement] = useState(false);
  const [showSourceSuggestion, setShowSourceSuggestion] = useState(false);

  const suggestions: Suggestion[] = [
    {
      id: '1',
      type: 'query',
      title: 'Improve your search',
      description: 'Your query could be more specific. Try refining it.',
      action: {
        label: 'Refine query',
        onClick: () => setShowQueryRefinement(true)
      }
    }
  ];

  const insights: Insight[] = [
    { type: 'stat', content: 'Found 12 relevant passages across 3 documents' },
    { type: 'tip', content: 'Ask follow-up questions for deeper insights' }
  ];

  return (
    <div className="space-y-4">
      {/* Proactive suggestions */}
      {suggestions.map(suggestion => (
        <SuggestionCard
          key={suggestion.id}
          suggestion={suggestion}
          onDismiss={() => console.log('Dismissed')}
        />
      ))}

      {/* Query refinement (conditional) */}
      {showQueryRefinement && (
        <QueryRefinement
          originalQuery="how does AI work"
          suggestions={[
            'How do neural networks function in artificial intelligence?',
            'What are the core mechanisms of machine learning algorithms?'
          ]}
          confidence={0.82}
          onSelectSuggestion={(query) => {
            console.log('Using refined query:', query);
            setShowQueryRefinement(false);
          }}
          onKeepOriginal={() => setShowQueryRefinement(false)}
        />
      )}

      {/* Document insights */}
      <InsightPanel
        documentName="AI_Research.pdf"
        insights={insights}
        onExplore={() => console.log('Exploring')}
      />

      {/* Source suggestion (conditional) */}
      {showSourceSuggestion && (
        <SourceSuggestion
          reason="You're asking about topics not covered in your documents"
          suggestedQuery="machine learning fundamentals 2024"
          onSearchWeb={(q) => console.log('Searching:', q)}
          onUpload={() => console.log('Upload')}
          onSkip={() => setShowSourceSuggestion(false)}
        />
      )}
    </div>
  );
}
```

## Component States

### Light/Dark Mode
All components automatically adapt to the current theme via CSS variables. No additional props needed.

### Loading States
Components don't include built-in loading states. Wrap them in your own loading container if needed.

### Error States
Components are designed to be defensive - they handle empty arrays and missing optional props gracefully.

## Browser Support
- Modern browsers with ES2020+ support
- Requires CSS Grid and Flexbox
- Uses backdrop-filter (fallback provided via opacity)

## Testing
Components are built with testability in mind:
- All interactive elements have accessible labels
- Callback props for all user actions
- No hard-coded API calls
- Pure presentation components
