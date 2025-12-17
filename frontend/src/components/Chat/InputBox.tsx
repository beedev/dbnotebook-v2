import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { Send, Square, Paperclip, Image as ImageIcon } from 'lucide-react';

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
  placeholder = 'Ask anything...',
  onFileUpload,
}: InputBoxProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
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

    // Clear on Ctrl+K or Cmd+K
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      setMessage('');
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
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const canSend = message.trim().length > 0 && !isLoading && !disabled;

  return (
    <div className="border-t border-void-surface bg-void-light/50 backdrop-blur-sm">
      <div className="max-w-3xl mx-auto p-4">
        <div
          className={`
            relative flex items-end gap-2 p-3
            bg-void-light rounded-xl
            border border-void-surface
            transition-all duration-200
            focus-within:border-glow/30 focus-within:shadow-glow
          `}
        >
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
                className="flex-shrink-0 p-2 rounded-lg text-text-dim hover:text-text hover:bg-void-surface transition-colors disabled:opacity-50"
                title="Upload document"
              >
                <Paperclip className="w-5 h-5" />
              </button>
            </>
          )}

          {/* Image generation hint */}
          <button
            onClick={() => setMessage((prev) => prev + ' [generate image] ')}
            disabled={isLoading || disabled}
            className="flex-shrink-0 p-2 rounded-lg text-text-dim hover:text-nebula hover:bg-nebula/10 transition-colors disabled:opacity-50"
            title="Add image generation prompt"
          >
            <ImageIcon className="w-5 h-5" />
          </button>

          {/* Text input */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className={`
              flex-1 resize-none
              bg-transparent text-text
              placeholder:text-text-dim
              focus:outline-none
              font-[family-name:var(--font-body)]
              text-base leading-relaxed
              max-h-[200px]
              disabled:opacity-50
            `}
          />

          {/* Send/Stop button */}
          {isStreaming ? (
            <button
              onClick={onStop}
              className="flex-shrink-0 p-2 rounded-lg bg-danger/20 text-danger hover:bg-danger/30 transition-colors"
              title="Stop generating"
            >
              <Square className="w-5 h-5" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!canSend}
              className={`
                flex-shrink-0 p-2 rounded-lg
                transition-all duration-200
                ${
                  canSend
                    ? 'bg-glow/20 text-glow hover:bg-glow/30 hover:shadow-glow'
                    : 'bg-void-surface text-text-dim cursor-not-allowed'
                }
              `}
              title="Send message (Enter)"
            >
              <Send className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Keyboard shortcuts hint */}
        <div className="flex items-center justify-between mt-2 px-1">
          <p className="text-xs text-text-dim">
            <kbd className="px-1.5 py-0.5 rounded bg-void-surface text-text-muted">Enter</kbd>
            {' '}to send,{' '}
            <kbd className="px-1.5 py-0.5 rounded bg-void-surface text-text-muted">Shift+Enter</kbd>
            {' '}for new line
          </p>
          {message.length > 0 && (
            <p className="text-xs text-text-dim">
              {message.length} characters
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default InputBox;
