import { classNames } from "@/lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-2.5 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonProps) {
  const variantStyles: React.CSSProperties = {};
  let variantClass = "";

  if (variant === "primary") {
    variantClass = "bg-emerald-600 text-white hover:bg-emerald-500 shadow-sm";
  } else if (variant === "danger") {
    variantClass = "bg-red-50 dark:bg-red-600/10 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-500/20 hover:bg-red-100 dark:hover:bg-red-600/20";
  } else if (variant === "secondary") {
    variantStyles.background = "var(--btn-secondary-bg)";
    variantStyles.color = "var(--btn-secondary-text)";
    variantStyles.borderColor = "var(--btn-secondary-border)";
    variantClass = "border hover:brightness-95";
  } else if (variant === "ghost") {
    variantStyles.color = "var(--btn-ghost-text)";
    variantClass = "hover:brightness-95";
  }

  return (
    <button
      className={classNames(
        "inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed",
        variantClass,
        sizes[size],
        className
      )}
      style={variantStyles}
      {...props}
    />
  );
}
