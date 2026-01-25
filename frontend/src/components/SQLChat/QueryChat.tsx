/**
 * Query Chat Component
 *
 * Chat interface for natural language queries with:
 * - Message history display
 * - Query input with send button
 * - Streaming state indicators
 * - Query suggestions
 */

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Send,
  Loader2,
  User,
  Bot,
  StopCircle,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import type { SQLChatMessage, QueryState, SQLQuerySettings } from '../../types/sqlChat';
import { SQLPreview } from './SQLPreview';
import { ResultsTable } from './ResultsTable';
import { TimingBreakdown, SQL_CHAT_STAGES } from '../shared/TimingBreakdown';
import { SQLQuerySettings as SQLQuerySettingsPanel, DEFAULT_SQL_QUERY_CONFIG, type SQLQueryConfig } from './SQLQuerySettings';

interface QueryChatProps {
  messages: SQLChatMessage[];
  queryState: QueryState;
  isQuerying: boolean;
  onSendQuery: (query: string, settings?: SQLQuerySettings) => void;
  onCancelQuery: () => void;
  onClearMessages: () => void;
  onAnalyzeInDashboard?: (file: File) => void;
  disabled?: boolean;
}

const QUERY_STATE_MESSAGES: Record<QueryState, string> = {
  idle: '',
  connecting: 'Connecting to database...',
  generating: 'Generating SQL...',
  validating: 'Validating query...',
  executing: 'Executing query...',
  complete: '',
  error: '',
};

const EXAMPLE_QUERIES = [
  'Show me the top 10 customers by total orders',
  'What is the average order value by month?',
  'List all products with low inventory',
  'How many users signed up this year?',
];

export function QueryChat({
  messages,
  queryState,
  isQuerying,
  onSendQuery,
  onCancelQuery,
  onClearMessages,
  onAnalyzeInDashboard,
  disabled = false,
}: QueryChatProps) {
  const [input, setInput] = useState('');
  const [querySettings, setQuerySettings] = useState<SQLQueryConfig>(DEFAULT_SQL_QUERY_CONFIG);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isQuerying && !disabled) {
      // Convert config to settings format
      const settings: SQLQuerySettings = {
        rerankerEnabled: querySettings.rerankerEnabled,
        rerankerModel: querySettings.rerankerModel,
        topK: querySettings.topK,
        hybridEnabled: querySettings.hybridEnabled,
      };
      onSendQuery(input.trim(), settings);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleExampleClick = (query: string) => {
    setInput(query);
    inputRef.current?.focus();
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          /* Empty state with example queries */
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Sparkles className="w-12 h-12 text-cyan-400 mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">
              Ask questions about your data
            </h3>
            <p className="text-slate-400 mb-6 max-w-md">
              Type a question in natural language and I'll generate and execute the SQL query for you.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {EXAMPLE_QUERIES.map((query, i) => (
                <button
                  key={i}
                  onClick={() => handleExampleClick(query)}
                  disabled={disabled}
                  className="px-3 py-2 text-sm text-left text-slate-300 bg-slate-800 hover:bg-slate-700
                             border border-slate-700 rounded-lg transition-colors disabled:opacity-50"
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Message history */
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {message.role !== 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-900/50 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-cyan-400" />
                  </div>
                )}

                <div
                  className={`max-w-[80%] space-y-3 ${
                    message.role === 'user' ? 'text-right' : ''
                  }`}
                >
                  {/* Message content */}
                  <div
                    className={`inline-block px-4 py-2 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-cyan-600 text-white'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {message.role === 'assistant' ? (
                      <div className="prose prose-sm prose-invert max-w-none
                        prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0
                        prose-headings:text-white prose-strong:text-white
                        prose-code:bg-slate-700 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                        prose-a:text-cyan-400 prose-a:no-underline hover:prose-a:underline">
                        <ReactMarkdown>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      message.content
                    )}
                  </div>

                  {/* SQL preview */}
                  {message.sql && (
                    <SQLPreview
                      sql={message.sql}
                      intent={message.result?.intent}
                      confidence={message.result?.confidence}
                    />
                  )}

                  {/* Results table */}
                  {message.result && message.result.success && (
                    <ResultsTable
                      result={message.result}
                      onAnalyzeInDashboard={onAnalyzeInDashboard}
                    />
                  )}

                  {/* Performance timings */}
                  {message.result && message.result.timings && (
                    <TimingBreakdown
                      totalTimeMs={message.result.executionTimeMs || 0}
                      timings={message.result.timings}
                      stages={SQL_CHAT_STAGES}
                      title="Performance Timings"
                    />
                  )}
                </div>

                {message.role === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center">
                    <User className="w-4 h-4 text-slate-400" />
                  </div>
                )}
              </div>
            ))}

            {/* Query state indicator */}
            {isQuerying && queryState !== 'idle' && queryState !== 'complete' && (
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-cyan-900/50 flex items-center justify-center">
                  <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                </div>
                <div className="text-sm text-slate-400">
                  {QUERY_STATE_MESSAGES[queryState]}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Clear messages button */}
      {messages.length > 0 && (
        <div className="px-4 pb-2">
          <button
            onClick={onClearMessages}
            className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" />
            Clear conversation
          </button>
        </div>
      )}

      {/* Query Settings Panel */}
      <SQLQuerySettingsPanel
        config={querySettings}
        onChange={setQuerySettings}
        disabled={disabled || isQuerying}
      />

      {/* Input area */}
      <div className="border-t border-slate-700 p-4">
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={disabled ? 'Select a connection to start...' : 'Ask a question about your data...'}
              disabled={disabled || isQuerying}
              rows={1}
              className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg
                         text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none
                         resize-none disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {isQuerying ? (
            <button
              type="button"
              onClick={onCancelQuery}
              className="p-3 bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors"
              title="Cancel query"
            >
              <StopCircle className="w-5 h-5" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim() || disabled}
              className="p-3 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed"
              title="Send query"
            >
              <Send className="w-5 h-5" />
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
