"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingState } from "@/components/ui/LoadingState";
import { api, type DevPilotInsight } from "@/lib/api";

const TONE_STYLES: Record<string, { color: string; bg: string }> = {
  critical: { color: "#dc2626", bg: "rgba(220,38,38,0.08)" },
  warning: { color: "#d97706", bg: "rgba(217,119,6,0.08)" },
  info: { color: "#2563eb", bg: "rgba(37,99,235,0.06)" },
  good: { color: "#059669", bg: "rgba(5,150,105,0.06)" },
  neutral: { color: "#6b7280", bg: "rgba(107,114,128,0.06)" },
};

const KIND_ICONS: Record<string, string> = {
  security: "\uD83D\uDEE1\uFE0F",
  dependency: "\uD83D\uDCE6",
  performance: "\u26A1",
  testing: "\u2705",
  architecture: "\uD83D\uDDC2\uFE0F",
  "good-practice": "\u2B50",
  info: "\uD83D\uDCCA",
};

export function InsightsPanel({ owner, repo }: { owner: string; repo: string }) {
  const [insights, setInsights] = useState<DevPilotInsight[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await api.ai2.insights(owner, repo);
      setInsights(res.insights);
    } catch {
      setInsights([]);
    } finally {
      setLoading(false);
    }
  }, [owner, repo]);

  useEffect(() => {
    if (owner && repo) load();
  }, [owner, repo, load]);

  if (loading) {
    return (
      <section aria-label="AI insights">
        <h2 className="text-sm font-semibold mb-2.5">AI Insights</h2>
        <Card padding="sm">
          <LoadingState message="Loading insights..." className="!py-2" />
        </Card>
      </section>
    );
  }

  return (
    <section aria-label="AI insights">
      <h2 className="text-sm font-semibold mb-2.5">AI Insights</h2>
      <Card padding="none">
        <div className="divide-y" style={{ borderColor: "var(--border)" }}>
          {insights.map((insight) => {
            const style = TONE_STYLES[insight.tone] || TONE_STYLES.neutral;
            const icon = KIND_ICONS[insight.kind] || "\uD83D\uDCCA";
            return (
              <div key={insight.id} className="px-4 py-3 flex items-start gap-3" style={{ background: style.bg }}>
                <span className="text-base shrink-0 mt-0.5">{icon}</span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium" style={{ color: style.color }}>{insight.title}</p>
                  <p className="text-[11px] mt-0.5" style={{ color: "var(--muted-foreground)" }}>{insight.detail}</p>
                  {insight.evidence && insight.evidence.length > 0 && (
                    <div className="mt-1.5 space-y-0.5">
                      {insight.evidence.map((ev, i) => (
                        <div key={i} className="flex items-center gap-1.5 text-[10px] font-mono" style={{ color: "var(--muted-foreground)" }}>
                          {ev.file && <span>{ev.file}{ev.line ? `:${ev.line}` : ""}</span>}
                          {!ev.file && <span>{ev.label}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {insight.href && (
                  <Link href={insight.href} className="text-[10px] shrink-0 underline mt-0.5" style={{ color: "var(--muted-foreground)" }}>
                    View
                  </Link>
                )}
              </div>
            );
          })}
        </div>
      </Card>
    </section>
  );
}
