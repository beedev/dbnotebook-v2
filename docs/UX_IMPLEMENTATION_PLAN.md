# UX Implementation Plan - Incremental Approach

## Guiding Principles
1. **Never break existing functionality** - Each change is backwards compatible
2. **Test after each increment** - Verify before moving to next step
3. **Feature flags where needed** - New features can be toggled off
4. **Small, focused changes** - Each PR could be merged independently

---

## Phase 1: Quick Wins (Visual Polish)
**Goal**: Immediate visual improvements without changing functionality

### 1.1 Empty State Enhancement
- Replace animated orbs in chat empty state with cleaner design
- Add helpful suggestions/prompts
- **Files**: `components/Chat/MessageList.tsx`
- **Risk**: LOW

### 1.2 Message Bubble Refinement
- Add subtle hover states
- Improve source citation styling
- Better copy button placement
- **Files**: `components/Chat/MessageBubble.tsx`
- **Risk**: LOW

### 1.3 Sidebar Section Headers
- Cleaner section dividers
- Better collapse/expand animations
- **Files**: `components/Sidebar/Sidebar.tsx`
- **Risk**: LOW

---

## Phase 2: Agentic Features Integration
**Goal**: Surface AI-powered suggestions in the UI

### 2.1 Query Suggestions in Empty State
- When notebook selected + has documents
- Show 3-4 suggested questions based on document content
- Click suggestion to populate input
- **API**: `POST /api/agents/refine-query`
- **Files**: `components/Chat/MessageList.tsx` (add to empty state)
- **Risk**: MEDIUM

### 2.2 Follow-up Suggestions After Responses
- After assistant responds, show 2-3 follow-up suggestions
- Small pill buttons below message
- **API**: `POST /api/agents/analyze-query`
- **Files**: `components/Chat/MessageBubble.tsx`
- **Risk**: MEDIUM

### 2.3 Source Gap Suggestions
- In sidebar Sources section, show "Suggestions" when gaps detected
- "Your notebook might benefit from adding X"
- **API**: `POST /api/agents/suggest-sources`
- **Files**: `components/Sidebar/DocumentsList.tsx`
- **Risk**: MEDIUM

---

## Phase 3: Multi-Notebook Features
**Goal**: Enable cross-notebook search

### 3.1 Multi-Notebook Query Button
- Add "Search All" toggle in chat header
- When enabled, queries search across all notebooks
- **API**: `POST /api/multi-notebook/query`
- **Files**: `components/Chat/ChatHeader.tsx`, `components/Chat/ChatArea.tsx`
- **Risk**: MEDIUM

### 3.2 Source Attribution Enhancement
- Show notebook name in source citations
- Color-code by notebook
- **Files**: `components/Chat/MessageBubble.tsx`
- **Risk**: LOW

---

## Phase 4: Document Preview
**Goal**: Better document management experience

### 4.1 Document Preview Panel
- Click document in sidebar to preview
- Show document metadata, page count, chunks
- Quick actions (delete, toggle)
- **Files**: New `components/Sidebar/DocumentPreview.tsx`
- **Risk**: LOW (additive)

### 4.2 Drag-Drop Upload Feedback
- Better visual feedback during upload
- Progress indicator
- **Files**: `components/Sidebar/DocumentsList.tsx`
- **Risk**: LOW

---

## Implementation Order

```
Week 1: Phase 1 (All) + Phase 2.1
Week 2: Phase 2.2 + Phase 2.3
Week 3: Phase 3 (All)
Week 4: Phase 4 (All)
```

---

## Current Session: Phase 1 + Phase 2.1

### Step 1: Empty State Enhancement
Replace animated orbs with clean suggestions UI

### Step 2: Wire up Query Suggestions API
Add hook to fetch suggestions when notebook selected

### Step 3: Display Suggestions in Empty State
Show clickable suggestion cards

### Step 4: Test and Deploy
Verify functionality, rebuild Docker
