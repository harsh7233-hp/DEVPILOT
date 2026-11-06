import { classNames } from "@/lib/utils";

interface EmptyStateProps {
  icon: string;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={classNames(
        "flex flex-col items-center justify-center py-16 text-center",
        className
      )}
    >
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-lg font-medium mb-1" style={{ color: "var(--foreground)" }}>{title}</h3>
      <p className="text-sm max-w-sm mb-6" style={{ color: "var(--muted-foreground)" }}>{description}</p>
      {action}
    </div>
  );
}
