import { classNames } from "@/lib/utils";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
  onClick?: () => void;
}

const paddings = {
  none: "",
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

export function Card({ children, className, padding = "md", onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={classNames(
        "rounded-xl border",
        onClick && "cursor-pointer hover:border-zinc-400 dark:hover:border-zinc-700 transition-colors",
        paddings[padding],
        className
      )}
      style={{ borderColor: "var(--border)", background: "var(--card)", color: "var(--card-foreground)" }}
    >
      {children}
    </div>
  );
}
