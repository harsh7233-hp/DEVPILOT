import { classNames } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "info";
  className?: string;
}

const variants = {
  default: "border",
  success: "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20",
  warning: "bg-amber-50 dark:bg-yellow-500/10 text-amber-700 dark:text-yellow-400 border-amber-200 dark:border-yellow-500/20",
  error: "bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-400 border-red-200 dark:border-red-500/20",
  info: "bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-500/20",
};

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={classNames(
        "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-md",
        variant === "default" ? "" : variants[variant],
        className
      )}
      style={variant === "default" ? {
        background: "var(--badge-default-bg)",
        color: "var(--badge-default-text)",
        borderColor: "var(--badge-default-border)",
        borderWidth: "1px",
      } : undefined}
    >
      {children}
    </span>
  );
}
