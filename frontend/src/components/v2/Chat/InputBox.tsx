import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { Send, Square, Paperclip, Image as ImageIcon, Mic } from 'lucide-react';

interface InputBoxProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isLoading?: boolean;
  isStreaming?: boolean;
  disabled?: boolean;
  placeholder?: string;
  onFileUpload?: (file: File) => void;
}

export function InputBox({
  onSend,
  onStop,
  isLoading = false,
  isStreaming = false,
  disabled = false,
  placeholder = 'Ask anything about your sources...',
  onFileUpload,
}: InputBoxProps) {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [message]);

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSend = () => {
    const trimmed = message.trim();
    if (!trimmed || isLoading || disabled) return;

    onSend(trimmed);
    setMessage('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onFileUpload) {
      onFileUpload(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const canSend = message.trim().length > 0 && !isLoading && !disabled;

  return (
    <div className="border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-primary)]">
      <div className="max-w-3xl mx-auto px-6 py-4">
        <div
          className={`
            relative flex items-end gap-2 p-3
            bg-[var(--color-bg-secondary)] rounded-[var(--radius-xl)]
            border transition-all duration-[var(--transition-normal)]
            ${isFocused
              ? 'border-[var(--color-accent)] shadow-[var(--shadow-focus)]'
              : 'border-[var(--color-border)]'
            }
          `}
        >
          {/* Left actions */}
          <div className="flex items-center gap-1">
            {/* File upload button */}
            {onFileUpload && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.txt,.docx,.epub,.pptx,.png,.jpg,.jpeg,.webp"
                  className="hidden"
                  onChange={handleFileChange}
                />
                <button
                  onClick={handleFileClick}
                  disabled={isLoading || disabled}
                  className="
                    p-2 rounded-[var(--radius-md)]
                    text-[var(--color-text-muted)]
                    hover:text-[var(--color-text-primary)]
                    hover:bg-[var(--color-bg-hover)]
                    transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                  "
                  title="Attach file"
                >
                  <Paperclip className="w-5 h-5" />
                </button>
              </>
            )}

            {/* Image generation hint */}
            <button
              onClick={() => setMessage((prev) => prev + ' [generate image] ')}
              disabled={isLoading || disabled}
              className="
                p-2 rounded-[var(--radius-md)]
                text-[var(--color-text-muted)]
                hover:text-[var(--color-secondary)]
                hover:bg-[var(--color-secondary-subtle)]
                transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
              title="Generate image"
            >
              <ImageIcon className="w-5 h-5" />
            </button>
          </div>

          {/* Text input */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="
              flex-1 resize-none
              bg-transparent
              text-[var(--color-text-primary)]
              placeholder:text-[var(--color-text-placeholder)]
              focus:outline-none
              font-[family-name:var(--font-body)]
              text-base leading-relaxed
              max-h-[180px]
              disabled:opacity-50
            "
          />

          {/* Right actions */}
          <div className="flex items-center gap-1">
            {/* Voice input (placeholder) */}
            <button
              disabled
              className="
                p-2 rounded-[var(--radius-md)]
                text-[var(--color-text-muted)]
                opacity-50 cursor-not-allowed
              "
              title="Voice input (coming soon)"
            >
              <Mic className="w-5 h-5" />
            </button>

            {/* Send/Stop button */}
            {isStreaming ? (
              <button
                onClick={onStop}
                className="
                  p-2 rounded-[var(--radius-md)]
                  bg-[var(--color-error-subtle)]
                  text-[var(--color-error)]
                  hover:bg-[var(--color-error)]
                  hover:text-white
                  transition-colors
                "
                title="Stop generating"
              >
                <Square className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!canSend}
                className={`
                  p-2 rounded-[var(--radius-md)]
                  transition-all duration-[var(--transition-fast)]
                  ${canSend
                    ? 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]'
                    : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)] cursor-not-allowed'
                  }
                `}
                title="Send message (Enter)"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* Helper text */}
        <div className="flex items-center justify-between mt-2 px-1">
          <p className="text-xs text-[var(--color-text-muted)]">
            <kbd className="px-1.5 py-0.5 rounded-[var(--radius-sm)] bg-[var(--color-bg-tertiary)] text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] text-[10px]">
              Enter
            </kbd>
            {' '}send{' '}
            <kbd className="px-1.5 py-0.5 rounded-[var(--radius-sm)] bg-[var(--color-bg-tertiary)] text-[var(--color-text-tertiary)] font-[family-name:var(--font-mono)] text-[10px]">
              Shift + Enter
            </kbd>
            {' '}new line
          </p>
          {message.length > 0 && (
            <p className="text-xs text-[var(--color-text-muted)]">
              {message.length} characters
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default InputBox;
