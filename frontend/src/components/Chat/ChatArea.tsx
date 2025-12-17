import { MessageList } from './MessageList';
import { InputBox } from './InputBox';
import { useChat } from '../../hooks/useChat';

interface ChatAreaProps {
  notebookId?: string;
  selectedModel?: string;
  onCopy?: (content: string) => void;
  onFileUpload?: (file: File) => void;
}

export function ChatArea({ notebookId, selectedModel, onCopy, onFileUpload }: ChatAreaProps) {
  const {
    messages,
    isLoading,
    isStreaming,
    error,
    sendMessage,
    stopStreaming,
    clearMessages,
  } = useChat(notebookId, selectedModel);

  return (
    <div className="flex flex-col h-full bg-void">
      {/* Header with clear button */}
      {messages.length > 0 && (
        <div className="flex items-center justify-end px-4 py-2 border-b border-void-surface">
          <button
            onClick={clearMessages}
            className="px-3 py-1.5 rounded-lg text-sm text-text-dim hover:text-text hover:bg-void-surface transition-colors"
          >
            Clear chat
          </button>
        </div>
      )}

      {/* Messages */}
      <MessageList
        messages={messages}
        onCopy={onCopy}
        onSuggestionClick={sendMessage}
      />

      {/* Error display */}
      {error && (
        <div className="px-4 py-3 mx-4 mb-4 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">
          {error}
        </div>
      )}

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
    </div>
  );
}

export default ChatArea;
