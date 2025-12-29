import { memo } from 'react';
import { Book, MoreHorizontal, Trash2, Download, Sun, Moon } from 'lucide-react';
import { useState } from 'react';

interface ChatHeaderProps {
  notebookName: string | null;
  notebookDescription?: string;
  messageCount?: number;
  onClearChat?: () => void;
  onExport?: () => void;
  onToggleTheme?: () => void;
  isDarkMode?: boolean;
}

export const ChatHeader = memo(function ChatHeader({
  notebookName,
  notebookDescription,
  messageCount = 0,
  onClearChat,
  onExport,
  onToggleTheme,
  isDarkMode = false,
}: ChatHeaderProps) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <header
      className="
        flex items-center justify-between px-6 py-4
        bg-[var(--color-bg-primary)]
        border-b border-[var(--color-border-subtle)]
      "
    >
      {/* Left: Notebook info */}
      <div className="flex items-center gap-3 min-w-0">
        {notebookName ? (
          <>
            <div
              className="
                flex-shrink-0 w-9 h-9 rounded-[var(--radius-md)]
                bg-[var(--color-accent-subtle)]
                flex items-center justify-center
              "
            >
              <Book className="w-5 h-5 text-[var(--color-accent)]" />
            </div>
            <div className="min-w-0">
              <h1
                className="
                  text-base font-semibold text-[var(--color-text-primary)]
                  font-[family-name:var(--font-display)]
                  truncate
                "
              >
                {notebookName}
              </h1>
              {notebookDescription && (
                <p className="text-xs text-[var(--color-text-muted)] truncate">
                  {notebookDescription}
                </p>
              )}
            </div>
          </>
        ) : (
          <div className="flex items-center gap-3">
            <div
              className="
                w-9 h-9 rounded-[var(--radius-md)]
                bg-[var(--color-bg-tertiary)]
                flex items-center justify-center
              "
            >
              <Book className="w-5 h-5 text-[var(--color-text-muted)]" />
            </div>
            <span className="text-sm text-[var(--color-text-muted)]">
              Select a notebook to start
            </span>
          </div>
        )}
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Message count */}
        {messageCount > 0 && (
          <span className="px-2 py-1 text-xs text-[var(--color-text-muted)] bg-[var(--color-bg-tertiary)] rounded-[var(--radius-full)]">
            {messageCount} {messageCount === 1 ? 'message' : 'messages'}
          </span>
        )}

        {/* Theme toggle */}
        {onToggleTheme && (
          <button
            onClick={onToggleTheme}
            className="
              p-2 rounded-[var(--radius-md)]
              text-[var(--color-text-muted)]
              hover:text-[var(--color-text-primary)]
              hover:bg-[var(--color-bg-hover)]
              transition-colors duration-[var(--transition-fast)]
            "
            title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDarkMode ? (
              <Sun className="w-4 h-4" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
          </button>
        )}

        {/* More options */}
        {notebookName && (onClearChat || onExport) && (
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="
                p-2 rounded-[var(--radius-md)]
                text-[var(--color-text-muted)]
                hover:text-[var(--color-text-primary)]
                hover:bg-[var(--color-bg-hover)]
                transition-colors duration-[var(--transition-fast)]
              "
            >
              <MoreHorizontal className="w-4 h-4" />
            </button>

            {showMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowMenu(false)}
                />
                <div
                  className="
                    absolute right-0 top-full mt-1 z-20
                    w-44 py-1
                    bg-[var(--color-bg-elevated)]
                    border border-[var(--color-border)]
                    rounded-[var(--radius-md)]
                    shadow-[var(--shadow-lg)]
                  "
                >
                  {onExport && (
                    <button
                      onClick={() => {
                        onExport();
                        setShowMenu(false);
                      }}
                      className="
                        w-full flex items-center gap-2 px-3 py-2
                        text-sm text-[var(--color-text-secondary)]
                        hover:bg-[var(--color-bg-hover)]
                        transition-colors
                      "
                    >
                      <Download className="w-4 h-4" />
                      Export chat
                    </button>
                  )}
                  {onClearChat && (
                    <button
                      onClick={() => {
                        onClearChat();
                        setShowMenu(false);
                      }}
                      className="
                        w-full flex items-center gap-2 px-3 py-2
                        text-sm text-[var(--color-error)]
                        hover:bg-[var(--color-error-subtle)]
                        transition-colors
                      "
                    >
                      <Trash2 className="w-4 h-4" />
                      Clear chat
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </header>
  );
});

export default ChatHeader;
