import { useState, useEffect } from 'react';
import { Clock, AlertTriangle } from 'lucide-react';

interface QuizTimerProps {
  /** Time limit in minutes */
  timeLimitMinutes: number;
  /** When the quiz started */
  startTime: Date;
  /** Called when time runs out */
  onTimeUp: () => void;
  /** Show compact version */
  compact?: boolean;
}

export function QuizTimer({
  timeLimitMinutes,
  startTime,
  onTimeUp,
  compact = false,
}: QuizTimerProps) {
  const [remainingSeconds, setRemainingSeconds] = useState<number>(() => {
    const totalSeconds = timeLimitMinutes * 60;
    const elapsed = Math.floor((Date.now() - startTime.getTime()) / 1000);
    return Math.max(0, totalSeconds - elapsed);
  });

  useEffect(() => {
    const interval = setInterval(() => {
      const totalSeconds = timeLimitMinutes * 60;
      const elapsed = Math.floor((Date.now() - startTime.getTime()) / 1000);
      const remaining = Math.max(0, totalSeconds - elapsed);

      setRemainingSeconds(remaining);

      if (remaining <= 0) {
        clearInterval(interval);
        onTimeUp();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [timeLimitMinutes, startTime, onTimeUp]);

  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;
  const isLowTime = remainingSeconds <= 60; // Last minute
  const isCritical = remainingSeconds <= 30; // Last 30 seconds

  const formatTime = () => {
    const m = String(minutes).padStart(2, '0');
    const s = String(seconds).padStart(2, '0');
    return `${m}:${s}`;
  };

  if (compact) {
    return (
      <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-sm font-medium ${
        isCritical
          ? 'bg-red-400/20 text-red-400 animate-pulse'
          : isLowTime
            ? 'bg-yellow-400/20 text-yellow-400'
            : 'bg-void-lighter text-text-muted'
      }`}>
        {isCritical ? (
          <AlertTriangle className="w-3.5 h-3.5" />
        ) : (
          <Clock className="w-3.5 h-3.5" />
        )}
        <span>{formatTime()}</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border ${
      isCritical
        ? 'bg-red-400/10 border-red-400/30 text-red-400'
        : isLowTime
          ? 'bg-yellow-400/10 border-yellow-400/30 text-yellow-400'
          : 'bg-void-lighter border-void-lighter text-text'
    }`}>
      {isCritical ? (
        <AlertTriangle className={`w-5 h-5 ${isCritical ? 'animate-pulse' : ''}`} />
      ) : (
        <Clock className="w-5 h-5" />
      )}
      <div>
        <div className="text-xs uppercase tracking-wide opacity-70">Time Remaining</div>
        <div className={`text-xl font-mono font-bold ${isCritical ? 'animate-pulse' : ''}`}>
          {formatTime()}
        </div>
      </div>
    </div>
  );
}
