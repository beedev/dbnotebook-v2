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
    <div className="border-t border-void-surface/50 bg-gradient-to-t from-void-light to-transparent">
      <div className="max-w-3xl mx-auto p-4">
        <div
          className={`
            relative flex items-end gap-2 p-2
            bg-void-surface/50 rounded-2xl
            border border-void-lighter/50
            transition-all duration-300
            focus-within:border-glow/40 focus-within:bg-void-surface/70
            focus-within:shadow-[0_0_20px_rgba(0,229,204,0.1)]
          `}
        >
          {/* Left action buttons */}
          <div className="flex items-center gap-1 pl-1">
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
                  className="flex-shrink-0 p-2 rounded-xl text-text-dim hover:text-glow hover:bg-glow/10 transition-all duration-200 disabled:opacity-50"
                  title="Upload document"
                >
                  <Paperclip className="w-4 h-4" />
                </button>
              </>
            )}

            {/* Image generation hint */}
            <button
              onClick={() => setMessage((prev) => prev + ' [generate image] ')}
              disabled={isLoading || disabled}
              className="flex-shrink-0 p-2 rounded-xl text-text-dim hover:text-nebula hover:bg-nebula/10 transition-all duration-200 disabled:opacity-50"
              title="Generate image"
            >
              <ImageIcon className="w-4 h-4" />
            </button>
          </div>

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
              flex-1 resize-none py-2 px-1
              bg-transparent text-text
              placeholder:text-text-dim/70
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
              className="flex-shrink-0 p-2.5 rounded-xl bg-danger/20 text-danger hover:bg-danger/30 transition-all duration-200"
              title="Stop generating"
            >
              <Square className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!canSend}
              className={`
                flex-shrink-0 p-2.5 rounded-xl
                transition-all duration-200
                ${
                  canSend
                    ? 'bg-glow text-void hover:bg-glow-bright shadow-lg shadow-glow/20'
                    : 'bg-void-lighter text-text-dim cursor-not-allowed'
                }
              `}
              title="Send message (Enter)"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Keyboard shortcuts hint - more subtle */}
        <div className="flex items-center justify-center mt-2 gap-4">
          <p className="text-[11px] text-text-dim/60">
            <kbd className="px-1 py-0.5 rounded bg-void-surface/50 text-text-dim font-mono text-[10px]">↵</kbd>
            {' '}send
          </p>
          <p className="text-[11px] text-text-dim/60">
            <kbd className="px-1 py-0.5 rounded bg-void-surface/50 text-text-dim font-mono text-[10px]">⇧↵</kbd>
            {' '}new line
          </p>
          {message.length > 0 && (
            <p className="text-[11px] text-text-dim/60">
              {message.length} chars
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default InputBox;
