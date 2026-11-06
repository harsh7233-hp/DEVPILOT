import { classNames } from "@/lib/utils";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={classNames(
        "flex flex-col items-center justify-center py-16 text-center",
        className
      )}
    >
      <div className="h-12 w-12 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
        <span className="text-red-400 text-xl">!</span>
      </div>
      <h3 className="text-lg font-medium mb-1" style={{ color: "var(--foreground)" }}>{title}</h3>
      <p className="text-sm max-w-sm mb-6" style={{ color: "var(--muted-foreground)" }}>{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 text-sm font-medium rounded-lg border transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800"
          style={{ background: "var(--input-bg)", borderColor: "var(--input-border)", color: "var(--foreground)" }}
        >
          Try again
        </button>
      )}
    </div>
  );
}
