export const AI_DISCLAIMER =
  "AI can make mistakes. Please verify important information independently.";

export function AIDisclaimer({ className = "" }: { className?: string }) {
  return (
    <p
      role="note"
      className={`text-[10px] sm:text-[11px] text-center leading-relaxed ${className}`}
      style={{ color: "var(--muted-foreground)" }}
    >
      {AI_DISCLAIMER}
    </p>
  );
}
