import { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';
import { MessageSquare } from 'lucide-react';
import type { Message } from '../../types';

interface MessageListProps {
  messages: Message[];
  onCopy?: (content: string) => void;
  onSuggestionClick?: (suggestion: string) => void;
}

export function MessageList({ messages, onCopy, onSuggestionClick }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  if (messages.length === 0) {
    return <EmptyState onSuggestionClick={onSuggestionClick} />;
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto overflow-x-hidden"
    >
      <div className="max-w-3xl mx-auto">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            onCopy={onCopy}
          />
        ))}
        <div ref={bottomRef} className="h-4" />
      </div>
    </div>
  );
}

interface EmptyStateProps {
  onSuggestionClick?: (suggestion: string) => void;
}

function EmptyState({ onSuggestionClick }: EmptyStateProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4">
      <div className="text-center max-w-md">
        {/* Animated logo */}
        <div className="relative mb-8">
          <div className="w-20 h-20 mx-auto rounded-2xl bg-glow/10 border border-glow/20 flex items-center justify-center animate-[float_6s_ease-in-out_infinite]">
            <MessageSquare className="w-10 h-10 text-glow" />
          </div>
          <div className="absolute inset-0 w-20 h-20 mx-auto rounded-2xl bg-glow/5 animate-[pulse-glow_2s_ease-in-out_infinite]" />
        </div>

        {/* Title */}
        <h2 className="text-2xl font-bold text-text mb-3 font-[family-name:var(--font-display)]">
          <span className="gradient-text">Start a Conversation</span>
        </h2>

        {/* Description */}
        <p className="text-text-muted mb-6">
          Ask questions about your documents, generate images, or just chat.
          I'm here to help!
        </p>

        {/* Quick suggestions */}
        <div className="flex flex-wrap gap-2 justify-center">
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              onClick={() => onSuggestionClick?.(suggestion)}
              className="px-3 py-1.5 rounded-lg bg-void-surface border border-void-lighter text-sm text-text-muted hover:border-glow/30 hover:text-text hover:bg-void-lighter transition-all cursor-pointer"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

const suggestions = [
  'Summarize my documents',
  'Generate an infographic',
  'Explain a concept',
  'Find key insights',
];

export default MessageList;
