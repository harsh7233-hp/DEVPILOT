import { classNames } from "@/lib/utils";

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({ message = "Loading...", className }: LoadingStateProps) {
  return (
    <div
      className={classNames(
        "flex flex-col items-center justify-center py-16",
        className
      )}
    >
      <div className="relative h-10 w-10 mb-4">
        <div className="absolute inset-0 rounded-full border-2" style={{ borderColor: "var(--border)" }} />
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-emerald-500 animate-spin" />
      </div>
      <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>{message}</p>
    </div>
  );
}
