"use client";

import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { PriorityItem } from "@/lib/api";
import { SEVERITY_STYLE } from "@/features/security/shared";

export function PriorityQueue({
  items,
  onSelect,
}: {
  items: PriorityItem[];
  onSelect: (item: PriorityItem) => void;
}) {
  const buckets = { Critical: [] as PriorityItem[], High: [] as PriorityItem[], Medium: [] as PriorityItem[], Low: [] as PriorityItem[] };
  for (const item of items) {
    const b = item.bucket as keyof typeof buckets;
    if (buckets[b]) buckets[b].push(item);
    else buckets.Low.push(item);
  }

  if (items.length === 0) {
    return (
      <section aria-label="Priority queue">
        <h2 className="text-sm font-semibold mb-2.5">Priority Queue</h2>
        <Card padding="md">
          <p className="text-xs text-center" style={{ color: "var(--muted-foreground)" }}>No findings in priority queue</p>
        </Card>
      </section>
    );
  }

  return (
    <section aria-label="Priority queue">
      <h2 className="text-sm font-semibold mb-2.5">Priority Queue ({items.length})</h2>
      <Card padding="none">
        <div className="divide-y" style={{ borderColor: "var(--border)" }}>
          {(["Critical", "High", "Medium", "Low"] as const).map((bucket) => {
            if (buckets[bucket].length === 0) return null;
            return (
              <div key={bucket}>
                <div className="px-4 py-1.5" style={{ background: "var(--muted)" }}>
                  <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: bucket === "Critical" ? "#dc2626" : bucket === "High" ? "#ea580c" : bucket === "Medium" ? "#d97706" : "#2563eb" }}>
                    {bucket} ({buckets[bucket].length})
                  </p>
                </div>
                {buckets[bucket].map((item) => (
                  <PriorityRow key={item.fingerprint} item={item} onSelect={onSelect} />
                ))}
              </div>
            );
          })}
        </div>
      </Card>
    </section>
  );
}

function PriorityRow({ item, onSelect }: { item: PriorityItem; onSelect: (item: PriorityItem) => void }) {
  const sevStyle = SEVERITY_STYLE[item.severity] || SEVERITY_STYLE.LOW;
  return (
    <button
      onClick={() => onSelect(item)}
      className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-black/[0.03] dark:hover:bg-white/[0.03] transition-colors"
    >
      <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: sevStyle.color }} />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium truncate">{item.title}</p>
        <p className="text-[10px] truncate" style={{ color: "var(--muted-foreground)" }}>
          {item.target.file}{item.target.line ? `:${item.target.line}` : ""}
          {item.target.symbol ? ` in ${item.target.symbol}` : ""}
        </p>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <Badge variant={item.severity === "CRITICAL" || item.severity === "HIGH" ? "error" : item.severity === "MEDIUM" ? "warning" : "info"}>
          {item.severity}
        </Badge>
        <span className="text-[10px] font-mono" style={{ color: "var(--muted-foreground)" }}>
          {item.priority_score}
        </span>
      </div>
    </button>
  );
}
