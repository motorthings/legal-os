import { AlertTriangle } from "lucide-react";

interface ErrorStateProps {
  error: string;
  onRetry: () => void;
}

export default function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-default)] p-6 border-l-4 border-l-red-500">
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-red-700 dark:text-red-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-1">
            Evaluation failed
          </h3>
          <p className="text-sm text-[var(--text-secondary)] break-words">
            {error}
          </p>
          <button
            onClick={onRetry}
            className="mt-3 inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium text-[#0a0e14] bg-primary-500 hover:bg-primary-400 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    </div>
  );
}
