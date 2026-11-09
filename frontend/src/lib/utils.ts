export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMinutes < 1) return "Just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
  });
}

export function classNames(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function isNetworkError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : "";
  return /failed to fetch|networkerror|load failed|network request failed/i.test(message);
}

export function friendlyErrorMessage(
  error: unknown,
  fallback = "Something went wrong"
): string {
  const message = error instanceof Error ? error.message : fallback;
  if (isNetworkError(error)) {
    return "Could not reach the backend. It may be starting up or redeploying—wait a few seconds, then click Try again.";
  }
  return message;
}

export function riskColor(level: "low" | "medium" | "high" | "critical"): string {
  switch (level) {
    case "low":
      return "text-emerald-400 bg-emerald-400/10 border-emerald-400/20";
    case "medium":
      return "text-yellow-400 bg-yellow-400/10 border-yellow-400/20";
    case "high":
      return "text-orange-400 bg-orange-400/10 border-orange-400/20";
    case "critical":
      return "text-red-400 bg-red-400/10 border-red-400/20";
  }
}

export function languageColor(lang: string): string {
  switch (lang) {
    case "TypeScript":
      return "bg-blue-500";
    case "JavaScript":
      return "bg-yellow-400";
    case "Python":
      return "bg-green-500";
    default:
      return "bg-zinc-500";
  }
}
