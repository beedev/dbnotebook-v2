import { memo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  User,
  Sparkles,
  Copy,
  Check,
  FileText,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from 'lucide-react';
import type { Message, SourceCitation } from '../../../types';
import { TimingBreakdown, RAG_CHAT_STAGES } from '../../shared/TimingBreakdown';

interface MessageBubbleProps {
  message: Message;
  onCopy?: (content: string) => void;
}

export const MessageBubble = memo(function MessageBubble({
  message,
  onCopy,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    onCopy?.(message.content);
  };

  return (
    <div
      className={`
        group flex gap-4 px-6 py-5
        animate-[slide-up_0.25s_ease-out]
        ${isUser ? '' : 'bg-[var(--color-bg-secondary)]'}
      `}
    >
      {/* Avatar */}
      <div
        className={`
          flex-shrink-0 w-8 h-8 rounded-full
          flex items-center justify-center
          ${isUser
            ? 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'
            : 'bg-[var(--color-accent-subtle)] text-[var(--color-accent)]'
          }
        `}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : (
          <Sparkles className="w-4 h-4" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-3">
        {/* Role label */}
        <div className="flex items-center gap-2">
          <span
            className={`
              text-sm font-medium
              font-[family-name:var(--font-display)]
              ${isUser ? 'text-[var(--color-text-secondary)]' : 'text-[var(--color-accent)]'}
            `}
          >
            {isUser ? 'You' : 'Assistant'}
          </span>
          <span className="text-xs text-[var(--color-text-muted)]">
            {formatTime(message.timestamp)}
          </span>
        </div>

        {/* Message content */}
        <div className="prose max-w-none">
          {message.isStreaming && !message.content ? (
            <TypingIndicator />
          ) : (
            <ReactMarkdown
              components={{
                p: ({ children }) => (
                  <p className="text-[var(--color-text-primary)] leading-relaxed mb-4 last:mb-0">
                    {children}
                  </p>
                ),
                code: ({ className, children, ...props }) => {
                  const isInline = !className;
                  return isInline ? (
                    <code
                      className="px-1.5 py-0.5 rounded-[var(--radius-sm)] bg-[var(--color-bg-tertiary)] text-[var(--color-accent)] font-[family-name:var(--font-mono)] text-sm"
                      {...props}
                    >
                      {children}
                    </code>
                  ) : (
                    <code
                      className="block p-4 rounded-[var(--radius-md)] bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] font-[family-name:var(--font-mono)] text-sm overflow-x-auto border border-[var(--color-border-subtle)]"
                      {...props}
                    >
                      {children}
                    </code>
                  );
                },
                pre: ({ children }) => (
                  <pre className="bg-transparent overflow-hidden my-4">
                    {children}
                  </pre>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc list-outside ml-5 text-[var(--color-text-primary)] space-y-1.5 my-3">
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal list-outside ml-5 text-[var(--color-text-primary)] space-y-1.5 my-3">
                    {children}
                  </ol>
                ),
                li: ({ children }) => (
                  <li className="text-[var(--color-text-primary)] pl-1">{children}</li>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] underline underline-offset-2 inline-flex items-center gap-0.5"
                  >
                    {children}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                ),
                strong: ({ children }) => (
                  <strong className="font-semibold text-[var(--color-text-primary)]">
                    {children}
                  </strong>
                ),
                em: ({ children }) => (
                  <em className="italic text-[var(--color-text-secondary)]">
                    {children}
                  </em>
                ),
                blockquote: ({ children }) => (
                  <blockquote className="border-l-3 border-[var(--color-border)] pl-4 my-4 text-[var(--color-text-secondary)] italic">
                    {children}
                  </blockquote>
                ),
                h1: ({ children }) => (
                  <h1 className="text-xl font-semibold text-[var(--color-text-primary)] mt-6 mb-3 font-[family-name:var(--font-display)]">
                    {children}
                  </h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mt-5 mb-2 font-[family-name:var(--font-display)]">
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-base font-semibold text-[var(--color-text-primary)] mt-4 mb-2 font-[family-name:var(--font-display)]">
                    {children}
                  </h3>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Generated images */}
        {message.images && message.images.length > 0 && (
          <div className="grid grid-cols-2 gap-3 mt-4">
            {message.images.map((image, index) => (
              <div
                key={index}
                className="relative rounded-[var(--radius-lg)] overflow-hidden border border-[var(--color-border)] group/img"
              >
                <img
                  src={image}
                  alt={`Generated image ${index + 1}`}
                  className="w-full h-auto"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-[var(--color-bg-primary)]/60 opacity-0 group-hover/img:opacity-100 transition-opacity flex items-center justify-center">
                  <a
                    href={image}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 rounded-[var(--radius-md)] bg-[var(--color-bg-elevated)] text-[var(--color-text-primary)] text-sm font-medium shadow-[var(--shadow-md)] hover:bg-[var(--color-bg-hover)]"
                  >
                    View Full Size
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Source citations */}
        {!isUser && message.sources && message.sources.length > 0 && !message.isStreaming && (
          <SourceCitations sources={message.sources} />
        )}

        {/* Performance timings */}
        {!isUser && message.metadata?.timings && Object.keys(message.metadata.timings).length > 0 && !message.isStreaming && (
          <div className="mt-4">
            <TimingBreakdown
              totalTimeMs={message.metadata.execution_time_ms || 0}
              timings={message.metadata.timings}
              stages={RAG_CHAT_STAGES}
              title="Performance Timings"
            />
          </div>
        )}

        {/* Streaming cursor */}
        {message.isStreaming && message.content && (
          <span className="inline-block w-0.5 h-5 bg-[var(--color-accent)] ml-0.5 animate-[pulse-subtle_1s_ease-in-out_infinite]" />
        )}
      </div>

      {/* Copy button */}
      {!isUser && message.content && !message.isStreaming && (
        <button
          onClick={handleCopy}
          className={`
            flex-shrink-0 p-2 rounded-[var(--radius-md)]
            opacity-0 group-hover:opacity-100
            transition-all duration-[var(--transition-fast)]
            hover:bg-[var(--color-bg-hover)]
            ${copied
              ? 'text-[var(--color-success)]'
              : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
            }
          `}
          title="Copy to clipboard"
        >
          {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
        </button>
      )}
    </div>
  );
});

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-2">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="w-2 h-2 rounded-full bg-[var(--color-accent)]"
          style={{
            animation: `typing-dot 1.4s ease-in-out infinite`,
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
    </div>
  );
}

function formatTime(date: Date): string {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(date);
}

interface SourceCitationsProps {
  sources: SourceCitation[];
}

function SourceCitations({ sources }: SourceCitationsProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const displaySources = isExpanded ? sources : sources.slice(0, 3);
  const hasMore = sources.length > 3;

  return (
    <div className="mt-4 pt-4 border-t border-[var(--color-border-subtle)]">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-4 h-4 text-[var(--color-text-muted)]" />
        <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wide">
          Sources ({sources.length})
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {displaySources.map((source, index) => (
          <div
            key={index}
            className="
              flex items-center gap-2 px-3 py-2
              bg-[var(--color-bg-elevated)] rounded-[var(--radius-md)]
              border border-[var(--color-border-subtle)]
              hover:border-[var(--color-border)]
              transition-colors cursor-default
              max-w-xs
            "
            title={source.snippet}
          >
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[var(--color-accent-subtle)] text-[var(--color-accent)] text-xs font-medium flex items-center justify-center">
              {index + 1}
            </span>
            <span className="text-sm text-[var(--color-text-primary)] truncate">
              {source.filename}
            </span>
            {source.page && (
              <span className="flex-shrink-0 text-xs text-[var(--color-text-muted)]">
                p.{source.page}
              </span>
            )}
            {source.score && (
              <span className="flex-shrink-0 badge text-xs">
                {Math.round(source.score * 100)}%
              </span>
            )}
          </div>
        ))}
      </div>

      {hasMore && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-2 flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-accent)] transition-colors"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="w-3 h-3" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="w-3 h-3" />
              Show {sources.length - 3} more
            </>
          )}
        </button>
      )}
    </div>
  );
}

export default MessageBubble;
