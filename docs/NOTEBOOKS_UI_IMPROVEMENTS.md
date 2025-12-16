# Notebooks UI Improvements - Implementation Plan

## Issues Identified

### 1. **.md File Upload Issue**
- **Problem**: `.md` files cannot be selected even after removing `accept` attribute
- **Root Cause**: macOS file picker behavior
- **Solution**: Use drag-and-drop upload as alternative method

### 2. **No Upload Progress Indicators**
- **Problem**: No visual feedback during file upload and embedding
- **Current Behavior**: Silent upload, no status updates
- **Solution**: Add loading spinner, progress bar, and status messages

### 3. **No Real-Time Embedding Feedback**
- **Problem**: Users don't know if files are being processed
- **Solution**: Show "Uploading → Processing → Embedding → Complete" states

### 4. **Document Count Not Updating**
- **Problem**: Document count doesn't update immediately after upload
- **Current**: Requires page refresh
- **Solution**: Auto-refresh after successful upload

### 5. **Limited Document Management**
- **Current**: Basic list with delete
- **Needed**:
  - Expandable document details
  - File type icons
  - Better metadata display
  - Bulk operations

### 6. **Chat UI Needs Improvement**
- **Problem**: Chat UI doesn't match notebooks modern design
- **Solution**: Redesign with similar look and feel

## Proposed Solutions

### Phase 1: Fix .md Upload + Add Drag-and-Drop (Priority 1)

**Changes to `notebooks.html`:**

1. **Remove accept attribute** (DONE)
   - File input: `<input type="file" id="file-input" multiple>`

2. **Add drag-and-drop zone:**
   ```html
   <div class="upload-drop-zone" id="drop-zone">
       <input type="file" id="file-input" multiple style="display: none;">
       <div class="drop-zone-content">
           <span class="drop-icon">📤</span>
           <p class="drop-text">Drag & drop files here or click to browse</p>
           <p class="drop-hint">Supported: PDF, TXT, DOCX, PPTX, EPUB, MD</p>
       </div>
   </div>
   ```

3. **JavaScript drag-and-drop handlers:**
   ```javascript
   const dropZone = document.getElementById('drop-zone');
   const fileInput = document.getElementById('file-input');

   // Click to browse
   dropZone.addEventListener('click', () => fileInput.click());

   // Drag-and-drop handlers
   dropZone.addEventListener('dragover', (e) => {
       e.preventDefault();
       dropZone.classList.add('drag-over');
   });

   dropZone.addEventListener('dragleave', () => {
       dropZone.classList.remove('drag-over');
   });

   dropZone.addEventListener('drop', (e) => {
       e.preventDefault();
       dropZone.classList.remove('drag-over');
       handleFiles(e.dataTransfer.files);
   });
   ```

### Phase 2: Upload Progress Indicators (Priority 1)

**Add upload progress UI:**

```html
<div id="upload-progress" class="upload-progress" style="display: none;">
    <div class="progress-header">
        <span class="progress-title"></span>
        <button class="progress-close" onclick="hideProgress()">✕</button>
    </div>
    <div class="progress-bar-container">
        <div class="progress-bar" id="progress-bar"></div>
    </div>
    <div class="progress-status" id="progress-status"></div>
</div>
```

**JavaScript progress tracking:**

```javascript
function showUploadProgress(filename, status, progress) {
    const progressEl = document.getElementById('upload-progress');
    const titleEl = progressEl.querySelector('.progress-title');
    const barEl = document.getElementById('progress-bar');
    const statusEl = document.getElementById('progress-status');

    progressEl.style.display = 'block';
    titleEl.textContent = filename;
    barEl.style.width = progress + '%';
    statusEl.textContent = status;
}

// Status states:
// - "Uploading..." (0-30%)
// - "Processing document..." (30-60%)
// - "Generating embeddings..." (60-90%)
// - "Complete!" (100%)
```

### Phase 3: Enhanced Document List (Priority 2)

**Improved document card design:**

```html
<div class="document-card">
    <div class="document-icon">📄</div>
    <div class="document-details">
        <div class="document-name">filename.pdf</div>
        <div class="document-meta">
            <span class="meta-item">📊 1.2 MB</span>
            <span class="meta-item">🔢 45 chunks</span>
            <span class="meta-item">🕒 2h ago</span>
        </div>
    </div>
    <div class="document-actions">
        <button class="btn-icon" onclick="viewDocument('id')">👁</button>
        <button class="btn-icon btn-danger" onclick="deleteDocument('id')">🗑</button>
    </div>
</div>
```

### Phase 4: Backend API Improvements (If Needed)

**Endpoint for upload status:**

```python
@app.route('/api/notebooks/<notebook_id>/documents/status/<task_id>')
def get_upload_status(notebook_id, task_id):
    """Get real-time upload/embedding status"""
    return jsonify({
        "status": "processing",  # uploading | processing | embedding | complete | error
        "progress": 45,          # 0-100
        "message": "Generating embeddings..."
    })
```

### Phase 5: Chat UI Redesign (Priority 2)

**Modernize chat interface to match notebooks design:**

1. **Message styling:**
   - User messages: Right-aligned, blue background
   - AI messages: Left-aligned, gray background
   - Modern bubble design

2. **Input area:**
   - Larger text area
   - Send button with icon
   - Character/token counter

3. **Chat header:**
   - Notebook name display
   - Document count badge
   - Clear chat button

## Implementation Order

1. ✅ **Phase 1a**: Remove accept attribute → Fix .md selection
2. 🔄 **Phase 1b**: Add drag-and-drop upload zone
3. 🔄 **Phase 2**: Upload progress indicators
4. ⏳ **Phase 3**: Enhanced document list
5. ⏳ **Phase 4**: Backend improvements (if needed for real-time status)
6. ⏳ **Phase 5**: Chat UI redesign

## CSS Additions Needed

```css
/* Drag-and-drop zone */
.upload-drop-zone {
    border: 2px dashed #cbd5e0;
    border-radius: 12px;
    padding: 40px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    background: #f7fafc;
}

.upload-drop-zone:hover {
    border-color: #4299e1;
    background: #ebf8ff;
}

.upload-drop-zone.drag-over {
    border-color: #3182ce;
    background: #bee3f8;
    transform: scale(1.02);
}

/* Progress indicator */
.upload-progress {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 350px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
    padding: 20px;
    z-index: 1000;
}

.progress-bar-container {
    background: #e2e8f0;
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    margin: 15px 0;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #4299e1, #3182ce);
    transition: width 0.3s ease;
}

/* Document cards */
.document-card {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 15px;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-bottom: 10px;
    transition: all 0.2s ease;
}

.document-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
}
```

## Testing Checklist

- [ ] .md files can be selected via drag-and-drop
- [ ] Upload progress shows all states
- [ ] Document count updates after upload
- [ ] Documents display with correct metadata
- [ ] Delete functionality works
- [ ] Chat UI matches notebooks design
- [ ] Mobile responsive design
- [ ] Error handling for failed uploads

## Next Steps

1. Implement Phase 1 & 2 together (drag-drop + progress)
2. Test with various file types including .md
3. Implement Phase 3 (enhanced document list)
4. Redesign chat UI (Phase 5)
5. Add backend improvements if needed (Phase 4)
