import { useState, useRef, useCallback, useEffect } from 'react';
import { MessageList } from './MessageList';
import { InputBox } from './InputBox';
import { ContentStudio } from './ContentStudio';
import { ChatHeader, type ViewMode } from './ChatHeader';
import { QuerySettingsPanel, DEFAULT_QUERY_SETTINGS, type QuerySettings } from './QuerySettingsPanel';
import { useChatV2 } from '../../hooks/useChatV2';
import { useDocument } from '../../contexts';
import { useQueryAnalysis } from '../../hooks';
import { QueryRefinement, InsightPanel, SourceSuggestion, type Insight } from '../Agentic';

interface ChatAreaProps {
  notebookId?: string;
  notebookName?: string;
  selectedModel?: string;
  onCopy?: (content: string) => void;
  onFileUpload?: (file: File) => void;
}

export function ChatArea({ notebookId, notebookName, selectedModel: _selectedModel, onCopy, onFileUpload }: ChatAreaProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('chat');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Query settings state (per-request, not persisted)
  const [querySettings, setQuerySettings] = useState<QuerySettings>(DEFAULT_QUERY_SETTINGS);

  // Agentic UI state (purely presentation, does NOT affect routing)
  const [showQueryRefinement, setShowQueryRefinement] = useState(false);
  const [pendingQuery, setPendingQuery] = useState('');
  const [refinementSuggestions, setRefinementSuggestions] = useState<string[]>([]);
  const [refinementConfidence, setRefinementConfidence] = useState(0);

  // InsightPanel state - shows after document upload
  const [showInsightPanel, setShowInsightPanel] = useState(false);
  const [uploadedDocName, setUploadedDocName] = useState('');
  const [documentInsights, setDocumentInsights] = useState<Insight[]>([]);

  // SourceSuggestion state - shows when knowledge gaps detected
  const [showSourceSuggestion, setShowSourceSuggestion] = useState(false);
  const [sourceSuggestionReason, setSourceSuggestionReason] = useState('');
  const [suggestedSearchQuery, setSuggestedSearchQuery] = useState('');

  // Get documents from context to determine hasDocuments
  const { documents } = useDocument();

  // Query analysis hook (for agentic suggestions)
  const { analyzeQuery } = useQueryAnalysis();

  const {
    messages,
    isLoading,
    isStreaming,
    error,
    sendMessage: originalSendMessage,
    stopStreaming,
    clearMessages,
    sessionId: _sessionId,
    userId: _userId,
  } = useChatV2(notebookId);

  // Wrapper to analyze query before sending (agentic enhancement)
  const sendMessage = useCallback(async (message: string) => {
    // If we have documents, analyze the query for potential improvements
    if (documents.length > 0 && notebookId && message.length > 3) {
      const analysis = await analyzeQuery(message);

      // If query needs refinement (low complexity or has suggestions), show refinement UI
      if (analysis && analysis.refinements.length > 0 && analysis.complexity < 0.4) {
        setPendingQuery(message);
        setRefinementSuggestions(analysis.refinements.slice(0, 3));
        setRefinementConfidence(1 - analysis.complexity); // Higher confidence for simpler queries
        setShowQueryRefinement(true);
        return; // Don't send yet, wait for user decision
      }
    }

    // Send the message (routing happens on backend)
    originalSendMessage(message);
  }, [documents.length, notebookId, analyzeQuery, originalSendMessage]);

  // Handle selecting a refined query
  const handleSelectRefinement = useCallback((refinedQuery: string) => {
    setShowQueryRefinement(false);
    originalSendMessage(refinedQuery);
    setPendingQuery('');
    setRefinementSuggestions([]);
  }, [originalSendMessage]);

  // Handle keeping original query
  const handleKeepOriginal = useCallback(() => {
    setShowQueryRefinement(false);
    originalSendMessage(pendingQuery);
    setPendingQuery('');
    setRefinementSuggestions([]);
  }, [originalSendMessage, pendingQuery]);

  // Wrapper for file upload to show InsightPanel (agentic - does NOT affect routing)
  const handleFileUploadWithInsights = useCallback(async (file: File) => {
    if (onFileUpload) {
      await onFileUpload(file);

      // Show InsightPanel after successful upload
      setUploadedDocName(file.name);
      setDocumentInsights([
        { type: 'stat', content: `Document "${file.name}" added to notebook` },
        { type: 'tip', content: 'Try asking specific questions about this document' },
        { type: 'tip', content: 'Use "Summarize" to get an overview of the content' },
      ]);
      setShowInsightPanel(true);

      // Auto-hide after 10 seconds
      setTimeout(() => setShowInsightPanel(false), 10000);
    }
  }, [onFileUpload]);

  // Detect knowledge gaps in the latest response (agentic - does NOT affect routing)
  const lastMessage = messages[messages.length - 1];
  const hasKnowledgeGap = lastMessage?.role === 'assistant' &&
    !lastMessage.isStreaming &&
    lastMessage.sources?.length === 0 &&
    documents.length > 0 &&
    lastMessage.content.length > 50;

  // Show SourceSuggestion when knowledge gap detected
  useEffect(() => {
    if (hasKnowledgeGap && !showSourceSuggestion) {
      setSourceSuggestionReason('Your question may require information not in your current documents');
      setSuggestedSearchQuery('related topics');
      setShowSourceSuggestion(true);
    }
  }, [hasKnowledgeGap, showSourceSuggestion]);

  const handleExport = () => {
    // Export chat as JSON
    const exportData = {
      notebook: notebookName,
      exportedAt: new Date().toISOString(),
      messages: messages.map(m => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
        sources: m.sources,
      })),
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${notebookName || 'chat'}-export-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    for (const file of files) {
      await handleFileUploadWithInsights(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex flex-col h-full bg-void">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.txt,.md,.docx,.doc,.epub,.pptx,.ppt,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.webp"
        className="hidden"
        onChange={handleFileSelect}
      />

      {/* Chat Header with View Mode Switcher */}
      <ChatHeader
        notebookName={notebookName}
        notebookId={notebookId}
        messageCount={messages.length}
        isStreaming={isStreaming}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onClearChat={clearMessages}
        onExport={handleExport}
        onUpload={handleUploadClick}
      />

      {/* Conditional Content based on View Mode */}
      {viewMode === 'chat' ? (
        <>
          {/* Messages */}
          <MessageList
            messages={messages}
            onCopy={onCopy}
            onSuggestionClick={sendMessage}
            hasNotebook={!!notebookId}
            hasDocuments={documents.length > 0}
            notebookId={notebookId}
            notebookName={notebookName}
          />

          {/* Error display */}
          {error && (
            <div className="px-4 py-3 mx-4 mb-4 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">
              {error}
            </div>
          )}

          {/* Query Refinement UI (agentic - does NOT affect routing) */}
          {showQueryRefinement && refinementSuggestions.length > 0 && (
            <div className="px-4 mb-4">
              <QueryRefinement
                originalQuery={pendingQuery}
                suggestions={refinementSuggestions}
                confidence={refinementConfidence}
                onSelectSuggestion={handleSelectRefinement}
                onKeepOriginal={handleKeepOriginal}
              />
            </div>
          )}

          {/* InsightPanel - shows after document upload (agentic - does NOT affect routing) */}
          {showInsightPanel && documentInsights.length > 0 && (
            <div className="px-4 mb-4">
              <InsightPanel
                documentName={uploadedDocName}
                insights={documentInsights}
                onDismiss={() => setShowInsightPanel(false)}
                onExplore={() => {
                  setShowInsightPanel(false);
                  // Optionally trigger a suggestion to explore the document
                }}
              />
            </div>
          )}

          {/* SourceSuggestion - shows when knowledge gaps detected (agentic - does NOT affect routing) */}
          {showSourceSuggestion && (
            <div className="px-4 mb-4">
              <SourceSuggestion
                reason={sourceSuggestionReason}
                suggestedQuery={suggestedSearchQuery}
                onSearchWeb={(query) => {
                  console.log('Search web for:', query);
                  setShowSourceSuggestion(false);
                  // Could integrate with web search feature here
                }}
                onUpload={() => {
                  setShowSourceSuggestion(false);
                  handleUploadClick();
                }}
                onSkip={() => setShowSourceSuggestion(false)}
              />
            </div>
          )}

          {/* Query Settings Panel - collapsible above input */}
          <QuerySettingsPanel
            settings={querySettings}
            onChange={setQuerySettings}
            disabled={isLoading || isStreaming}
          />

          {/* Input */}
          <InputBox
            onSend={sendMessage}
            onStop={stopStreaming}
            isLoading={isLoading}
            isStreaming={isStreaming}
            onFileUpload={onFileUpload}
            placeholder={
              notebookId
                ? 'Ask about your documents...'
                : 'Ask anything...'
            }
          />
        </>
      ) : (
        /* Studio Mode - Full Content Studio */
        <div className="flex-1 overflow-hidden">
          <ContentStudio
            notebookId={notebookId || null}
            notebookName={notebookName}
            isFullScreen={true}
          />
        </div>
      )}
    </div>
  );
}

export default ChatArea;
