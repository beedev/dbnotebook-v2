interface QuizProgressProps {
  current: number;
  total: number;
  score: number;
}

export function QuizProgress({ current, total, score }: QuizProgressProps) {
  const progress = Math.round((current / total) * 100);

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between text-sm text-text-muted mb-2">
        <span>Question {current} of {total}</span>
        <span>Score: {score}</span>
      </div>
      <div className="h-2 bg-void-lighter rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
