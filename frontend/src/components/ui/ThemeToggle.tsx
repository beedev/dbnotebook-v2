import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../contexts';

interface ThemeToggleProps {
  className?: string;
}

export function ThemeToggle({ className = '' }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className={`
        flex items-center gap-2 px-3 py-2
        rounded-lg transition-all duration-200
        bg-void-surface hover:bg-void-lighter
        text-text-muted hover:text-text
        ${className}
      `}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? (
        <>
          <Sun className="w-4 h-4" />
          <span className="text-xs font-medium">Light</span>
        </>
      ) : (
        <>
          <Moon className="w-4 h-4" />
          <span className="text-xs font-medium">Dark</span>
        </>
      )}
    </button>
  );
}

export default ThemeToggle;
