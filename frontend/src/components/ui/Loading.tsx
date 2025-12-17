interface LoadingProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  text?: string;
  variant?: 'spinner' | 'dots' | 'pulse';
}

const sizeMap = {
  sm: { container: 'gap-2', spinner: 'w-4 h-4', dots: 'w-1.5 h-1.5', text: 'text-sm' },
  md: { container: 'gap-3', spinner: 'w-6 h-6', dots: 'w-2 h-2', text: 'text-base' },
  lg: { container: 'gap-4', spinner: 'w-8 h-8', dots: 'w-2.5 h-2.5', text: 'text-lg' },
  xl: { container: 'gap-5', spinner: 'w-12 h-12', dots: 'w-3 h-3', text: 'text-xl' },
};

export function Loading({ size = 'md', text, variant = 'spinner' }: LoadingProps) {
  const styles = sizeMap[size];

  return (
    <div className={`flex flex-col items-center justify-center ${styles.container}`}>
      {variant === 'spinner' && <Spinner size={size} />}
      {variant === 'dots' && <Dots size={size} />}
      {variant === 'pulse' && <Pulse size={size} />}
      {text && (
        <span className={`text-text-muted ${styles.text}`}>{text}</span>
      )}
    </div>
  );
}

function Spinner({ size }: { size: 'sm' | 'md' | 'lg' | 'xl' }) {
  const styles = sizeMap[size];

  return (
    <div className={`relative ${styles.spinner}`}>
      <div
        className={`
          absolute inset-0 rounded-full
          border-2 border-void-surface
        `}
      />
      <div
        className={`
          absolute inset-0 rounded-full
          border-2 border-transparent border-t-glow
          animate-spin
        `}
      />
      <div
        className={`
          absolute inset-1 rounded-full
          bg-glow/10
          animate-pulse
        `}
      />
    </div>
  );
}

function Dots({ size }: { size: 'sm' | 'md' | 'lg' | 'xl' }) {
  const styles = sizeMap[size];

  return (
    <div className="flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className={`
            ${styles.dots} rounded-full bg-glow
            animate-[typing_1.2s_ease-in-out_infinite]
          `}
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}

function Pulse({ size }: { size: 'sm' | 'md' | 'lg' | 'xl' }) {
  const styles = sizeMap[size];

  return (
    <div className={`relative ${styles.spinner}`}>
      <div
        className={`
          absolute inset-0 rounded-full bg-glow/20
          animate-ping
        `}
      />
      <div
        className={`
          absolute inset-0 rounded-full bg-glow/40
          animate-pulse
        `}
      />
    </div>
  );
}

// Full-screen loading overlay
export function LoadingOverlay({ text = 'Loading...' }: { text?: string }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-void/80 backdrop-blur-sm">
      <Loading size="xl" text={text} variant="spinner" />
    </div>
  );
}

// Inline loading for content areas
export function LoadingInline({ text }: { text?: string }) {
  return (
    <div className="flex items-center justify-center py-8">
      <Loading size="md" text={text} variant="dots" />
    </div>
  );
}

export default Loading;
