import { Trash2, Download, Upload, MessageSquare, Sparkles } from 'lucide-react';

export type ViewMode = 'chat' | 'studio';

interface ChatHeaderProps {
  notebookName?: string;
  notebookId?: string;
  messageCount?: number;
  isStreaming?: boolean;
  viewMode?: ViewMode;
  onViewModeChange?: (mode: ViewMode) => void;
  onClearChat?: () => void;
  onExport?: () => void;
  onUpload?: () => void;
}

export function ChatHeader({
  notebookName,
  notebookId,
  messageCount = 0,
  isStreaming = false,
  viewMode = 'chat',
  onViewModeChange,
  onClearChat,
  onExport,
  onUpload,
}: ChatHeaderProps) {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-void-surface bg-void-light/50">
      {/* Left: Notebook info + View Mode Switcher */}
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-lg font-semibold text-text font-[family-name:var(--font-display)]">
            {notebookName || 'DBNotebook'}
          </h1>
          {notebookId && (
            <div className="flex items-center gap-2 mt-0.5">
              <StatusBadge isStreaming={isStreaming} />
              {viewMode === 'chat' && messageCount > 0 && (
                <span className="text-xs text-text-dim">
                  {messageCount} message{messageCount !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          )}
        </div>

        {/* View Mode Switcher */}
        {notebookId && onViewModeChange && (
          <div className="flex items-center bg-void-surface rounded-lg p-0.5">
            <ViewModeTab
              icon={<MessageSquare className="w-3.5 h-3.5" />}
              label="Chat"
              isActive={viewMode === 'chat'}
              onClick={() => onViewModeChange('chat')}
            />
            <ViewModeTab
              icon={<Sparkles className="w-3.5 h-3.5" />}
              label="Studio"
              isActive={viewMode === 'studio'}
              onClick={() => onViewModeChange('studio')}
            />
          </div>
        )}
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {notebookId && viewMode === 'chat' && (
          <ActionButton
            icon={<Upload className="w-4 h-4" />}
            label="Upload"
            onClick={onUpload}
            variant="primary"
          />
        )}
        {viewMode === 'chat' && messageCount > 0 && (
          <>
            <ActionButton
              icon={<Download className="w-4 h-4" />}
              label="Export"
              onClick={onExport}
            />
            <ActionButton
              icon={<Trash2 className="w-4 h-4" />}
              label="Clear"
              onClick={onClearChat}
              variant="danger"
            />
          </>
        )}
      </div>
    </header>
  );
}

interface StatusBadgeProps {
  isStreaming: boolean;
}

function StatusBadge({ isStreaming }: StatusBadgeProps) {
  if (isStreaming) {
    return (
      <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-glow/10 text-glow text-xs font-medium">
        <span className="w-1.5 h-1.5 rounded-full bg-glow animate-pulse" />
        Generating...
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-success/10 text-success text-xs font-medium">
      <span className="w-1.5 h-1.5 rounded-full bg-success" />
      Ready
    </div>
  );
}

interface ViewModeTabProps {
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  onClick: () => void;
}

function ViewModeTab({ icon, label, isActive, onClick }: ViewModeTabProps) {
  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200
        ${isActive
          ? 'bg-glow/20 text-glow'
          : 'text-text-muted hover:text-text hover:bg-void-lighter'
        }
      `}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

interface ActionButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  variant?: 'default' | 'primary' | 'danger';
}

function ActionButton({ icon, label, onClick, variant = 'default' }: ActionButtonProps) {
  const baseStyles = "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200";

  const variantStyles = {
    default: "text-text-muted hover:text-text bg-void-surface hover:bg-void-lighter border border-transparent",
    primary: "text-glow-bright bg-glow/10 hover:bg-glow/20 border border-glow/20",
    danger: "text-text-muted hover:text-danger bg-void-surface hover:bg-danger/10 border border-transparent hover:border-danger/20",
  };

  return (
    <button
      onClick={onClick}
      className={`${baseStyles} ${variantStyles[variant]}`}
      title={label}
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

export default ChatHeader;
