# DBNotebook v2 UI - NotebookLM-Inspired Redesign

A clean, minimal, Notion-like redesign of the DBNotebook interface.

## Design Philosophy

**"Editorial Clarity"** - Premium productivity tool with warm minimalism, generous whitespace, and document-centric focus.

### Key Changes from v1

| Aspect | v1 (Deep Space Terminal) | v2 (Editorial Clarity) |
|--------|--------------------------|------------------------|
| Theme | Dark neon (cyan/purple) | Clean minimal (warm grays) |
| Typography | JetBrains Mono headers | Outfit + Source Sans 3 |
| Colors | Glow effects, high contrast | Subtle shadows, muted accents |
| Layout | Dense, busy | Spacious, focused |
| Mood | Techy, gamified | Professional, calm |

## Preview the New Design

### Option 1: Quick Preview (Recommended)

1. Update `main.tsx` to use v2:

```tsx
// main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/index.css';  // Use new theme
import { Preview } from './components/v2/Preview';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Preview />
  </StrictMode>
);
```

2. Run `npm run dev` and open http://localhost:5173

### Option 2: Side-by-Side Comparison

Create a new HTML entry for v2:

```html
<!-- index-v2.html -->
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>DBNotebook v2 Preview</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main-v2.tsx"></script>
  </body>
</html>
```

## Components

### New Components

| Component | Description |
|-----------|-------------|
| `SourcesPanel` | NotebookLM-style document cards with toggle |
| `ChatHeader` | Clean notebook title bar with actions |
| `EmptyState` | Minimal onboarding illustrations |

### Redesigned Components

| Component | Changes |
|-----------|---------|
| `Sidebar` | Collapsible sections, cleaner model selector |
| `MessageBubble` | More whitespace, subtle borders, chip sources |
| `InputBox` | Cleaner border, grouped actions |
| `NotebookCard` | Visual card with accent colors |

## Color Palette

### Light Mode
- Background: `#ffffff` → `#fafafa` → `#f5f5f5`
- Accent: `#0891b2` (muted teal)
- Text: `#1a1a1a` → `#4a4a4a` → `#6b6b6b`
- Border: `#e5e5e5`

### Dark Mode
- Background: `#1a1a1a` → `#222222` → `#2a2a2a`
- Accent: `#22d3ee` (brighter teal)
- Text: `#f5f5f5` → `#d4d4d4` → `#a3a3a3`
- Border: `#333333`

## Typography

- **Display**: Outfit (headers, titles)
- **Body**: Source Sans 3 (content, UI)
- **Code**: JetBrains Mono (code blocks)

## Migration Path

After approval, migrate components in waves:

### Wave 1: Core Layout
- [ ] Update `index.css` to import new theme
- [ ] Replace `Sidebar` with v2 version
- [ ] Add `ChatHeader` to `ChatArea`

### Wave 2: Chat Components
- [ ] Replace `MessageBubble`
- [ ] Replace `InputBox`
- [ ] Replace `MessageList` empty state

### Wave 3: Polish
- [ ] Update `Toast` component
- [ ] Update `Button` component
- [ ] Add theme toggle functionality

## Files Structure

```
frontend/src/
├── styles/
│   ├── theme.css      # New theme variables
│   └── index.css      # Entry (imports theme + tailwind)
├── components/
│   └── v2/
│       ├── Chat/
│       │   ├── ChatHeader.tsx
│       │   ├── MessageBubble.tsx
│       │   ├── InputBox.tsx
│       │   ├── EmptyState.tsx
│       │   └── index.tsx
│       ├── Sidebar/
│       │   ├── NotebookCard.tsx
│       │   └── index.tsx
│       ├── SourcesPanel/
│       │   ├── SourceCard.tsx
│       │   └── index.tsx
│       ├── Preview.tsx
│       └── index.tsx
└── main-v2.tsx        # Preview entry point
```
