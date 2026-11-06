"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { scoreColor, type HealthCard } from "@/features/security/shared";
import type { DeepScanReport } from "@/lib/api";

const CARD_KEYS = ["code_health", "reliability", "maintainability", "security_posture", "performance", "test_coverage"] as const;

const CARD_ICONS: Record<string, string> = {
  code_health: "\u2764\uFE0F",
  reliability: "\u26A1",
  maintainability: "\u2699\uFE0F",
  security_posture: "\uD83D\uDEE1\uFE0F",
  performance: "\u26A1",
  test_coverage: "\u2705",
};

const CARD_ICONS_COLORS: Record<string, string> = {
  code_health: "#10b981",
  reliability: "#8b5cf6",
  maintainability: "#3b82f6",
  security_posture: "#ef4444",
  performance: "#f59e0b",
  test_coverage: "#06b6d4",
};

export function HealthOverviewCards({ report }: { report: DeepScanReport }) {
  const [expandedCard, setExpandedCard] = useState<string | null>(null);
  const cards = report.health_cards;

  return (
    <section aria-label="Health overview">
      <h2 className="text-sm font-semibold mb-2.5">Health Overview</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {CARD_KEYS.map((key) => {
          const card = (cards as Record<string, HealthCard | undefined>)[key];
          if (!card) return null;
          return (
            <HealthMiniCard
              key={key}
              cardKey={key}
              card={card}
              expanded={expandedCard === key}
              onToggle={() => setExpandedCard(expandedCard === key ? null : key)}
            />
          );
        })}
      </div>
      {expandedCard && (cards as Record<string, HealthCard | undefined>)[expandedCard] && (
        <HealthCardDetail cardKey={expandedCard} card={(cards as Record<string, HealthCard>)[expandedCard]} />
      )}
    </section>
  );
}

function HealthMiniCard({
  cardKey,
  card,
  expanded,
  onToggle,
}: {
  cardKey: string;
  card: HealthCard;
  expanded: boolean;
  onToggle: () => void;
}) {
  const score = card.score;
  const icon = CARD_ICONS[cardKey] || "\uD83D\uDCCA";
  const iconColor = CARD_ICONS_COLORS[cardKey] || "#6b7280";

  return (
    <Card
      padding="sm"
      className={`min-w-0 cursor-pointer transition-all ${expanded ? "ring-2 ring-offset-1" : "hover:border-zinc-400 dark:hover:border-zinc-600"}`}
      onClick={onToggle}
    >
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-sm" style={{ color: iconColor }}>{icon}</span>
        <p className="text-[10px] font-medium uppercase tracking-wider truncate" style={{ color: "var(--muted-foreground)" }}>
          {card.title}
        </p>
      </div>
      {score != null ? (
        <p className="text-2xl font-bold leading-none" style={{ color: scoreColor(score) }}>
          {score}
        </p>
      ) : (
        <p className="text-lg font-bold" style={{ color: "var(--muted-foreground)" }}>—</p>
      )}
      {card.is_proxy && (
        <Badge variant="info" className="mt-1.5 text-[9px]">{card.proxy_label}</Badge>
      )}
      {card.analysis_kind && (
        <Badge variant="warning" className="mt-1.5 text-[9px]">{card.analysis_kind}</Badge>
      )}
      {card.unavailable_reason && (
        <p className="text-[9px] mt-1 truncate" style={{ color: "var(--muted-foreground)" }}>{card.unavailable_reason}</p>
      )}
      <p className="text-[9px] mt-1 truncate" style={{ color: "var(--muted-foreground)" }}>
        Click for details
      </p>
    </Card>
  );
}

function HealthCardDetail({ cardKey, card }: { cardKey: string; card: HealthCard }) {
  return (
    <Card padding="md" className="mt-3">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold">{card.title} — Detailed Analysis</h3>
        {card.score != null && (
          <span className="text-lg font-bold" style={{ color: scoreColor(card.score) }}>{card.score}/100</span>
        )}
      </div>
      <div className="space-y-3">
        <div className="rounded-lg p-3" style={{ background: "var(--muted)" }}>
          <p className="text-[10px] uppercase tracking-wider font-semibold mb-1" style={{ color: "var(--muted-foreground)" }}>How is this calculated?</p>
          <p className="text-xs font-mono" style={{ color: "var(--foreground)" }}>{card.formula}</p>
        </div>
        <div className="rounded-lg p-3" style={{ background: "var(--muted)" }}>
          <p className="text-[10px] uppercase tracking-wider font-semibold mb-1" style={{ color: "var(--muted-foreground)" }}>Methodology</p>
          <p className="text-xs" style={{ color: "var(--foreground)" }}>{card.methodology}</p>
        </div>
        {card.factors && card.factors.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wider font-semibold mb-2" style={{ color: "var(--muted-foreground)" }}>Score Factors</p>
            <div className="space-y-2">
              {card.factors.map((f: { name: string; score: number | null; weight: number; available: boolean; measurements: Record<string, unknown>; formula: string }) => (
                <div key={f.name} className="flex items-center gap-3">
                  <div className="w-28 shrink-0">
                    <p className="text-xs font-medium capitalize">{f.name}</p>
                    <p className="text-[9px]" style={{ color: "var(--muted-foreground)" }}>weight: {(f.weight * 100).toFixed(0)}%</p>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="h-2 rounded-full" style={{ background: "var(--muted)" }}>
                      {f.available && f.score != null && (
                        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${f.score}%`, background: scoreColor(f.score) }} />
                      )}
                    </div>
                  </div>
                  <span className="text-xs font-semibold w-8 text-right" style={{ color: f.available && f.score != null ? scoreColor(f.score) : "var(--muted-foreground)" }}>
                    {f.available && f.score != null ? f.score : "N/A"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        {card.measurements && Object.keys(card.measurements).length > 0 && (
          <div className="rounded-lg p-3" style={{ background: "var(--muted)" }}>
            <p className="text-[10px] uppercase tracking-wider font-semibold mb-1.5" style={{ color: "var(--muted-foreground)" }}>Raw Measurements</p>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(card.measurements).map(([k, v]) => (
                <div key={k}>
                  <p className="text-[10px] capitalize" style={{ color: "var(--muted-foreground)" }}>{k.replace(/_/g, " ")}</p>
                  <p className="text-xs font-medium">{v == null ? "—" : String(v)}</p>
                </div>
              ))}
            </div>
          </div>
        )}
        {card.smells && typeof card.smells === "object" && (
          <SmellsDetail smells={card.smells as Record<string, unknown>} />
        )}
        {card.details && typeof card.details === "object" && Object.keys(card.details).length > 0 && (
          <PostureDetail details={card.details as Record<string, unknown>} />
        )}
      </div>
    </Card>
  );
}

function SmellsDetail({ smells }: { smells: Record<string, unknown> }) {
  const longFuncs = smells["long_functions"] as string[] | undefined;
  const manyParams = smells["too_many_params"] as string[] | undefined;
  const deepNest = smells["deeply_nested"] as string[] | undefined;
  const godFiles = smells["god_files"] as { file: string; lines: number }[] | undefined;
  const todos = smells["todo_fixme_markers"] as number | undefined;
  const total = smells["total"] as number | undefined;

  return (
    <div className="rounded-lg p-3" style={{ background: "var(--muted)" }}>
      <p className="text-[10px] uppercase tracking-wider font-semibold mb-2" style={{ color: "var(--muted-foreground)" }}>
        Code Smells {total != null ? `(${total} total)` : ""}
      </p>
      <div className="grid grid-cols-2 gap-3 text-xs">
        {longFuncs && longFuncs.length > 0 && (
          <div>
            <p className="font-medium" style={{ color: "#ea580c" }}>Long functions ({longFuncs.length})</p>
            <p className="text-[10px] truncate" style={{ color: "var(--muted-foreground)" }}>{longFuncs.slice(0, 3).join(", ")}{longFuncs.length > 3 ? "..." : ""}</p>
          </div>
        )}
        {manyParams && manyParams.length > 0 && (
          <div>
            <p className="font-medium" style={{ color: "#d97706" }}>Too many params ({manyParams.length})</p>
            <p className="text-[10px] truncate" style={{ color: "var(--muted-foreground)" }}>{manyParams.slice(0, 3).join(", ")}{manyParams.length > 3 ? "..." : ""}</p>
          </div>
        )}
        {deepNest && deepNest.length > 0 && (
          <div>
            <p className="font-medium" style={{ color: "#8b5cf6" }}>Deeply nested ({deepNest.length})</p>
            <p className="text-[10px] truncate" style={{ color: "var(--muted-foreground)" }}>{deepNest.slice(0, 3).join(", ")}{deepNest.length > 3 ? "..." : ""}</p>
          </div>
        )}
        {godFiles && godFiles.length > 0 && (
          <div>
            <p className="font-medium" style={{ color: "#dc2626" }}>Large files ({godFiles.length})</p>
            {godFiles.slice(0, 2).map((g) => (
              <p key={g.file} className="text-[10px] truncate" style={{ color: "var(--muted-foreground)" }}>{g.file} ({g.lines} lines)</p>
            ))}
          </div>
        )}
        {todos != null && todos > 0 && (
          <div>
            <p className="font-medium" style={{ color: "#6b7280" }}>TODO/FIXME markers</p>
            <p className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>{todos} found</p>
          </div>
        )}
      </div>
    </div>
  );
}

function PostureDetail({ details }: { details: Record<string, unknown> }) {
  return (
    <div className="rounded-lg p-3" style={{ background: "var(--muted)" }}>
      <p className="text-[10px] uppercase tracking-wider font-semibold mb-2" style={{ color: "var(--muted-foreground)" }}>Security Posture Breakdown</p>
      <div className="grid grid-cols-3 gap-3 text-xs">
        <div>
          <p className="font-medium">Executed Checks</p>
          <p className="text-lg font-bold">{String(details["executed_checks"] ?? "—")}</p>
        </div>
        <div>
          <p className="font-medium" style={{ color: "#059669" }}>Passed</p>
          <p className="text-lg font-bold" style={{ color: "#059669" }}>{String(details["passed_checks"] ?? "—")}</p>
        </div>
        <div>
          <p className="font-medium" style={{ color: "#dc2626" }}>Failed</p>
          <p className="text-lg font-bold" style={{ color: "#dc2626" }}>{String(details["failed_checks"] ?? "—")}</p>
        </div>
        <div>
          <p className="font-medium">Open Findings</p>
          <p className="text-lg font-bold">{String(details["open_findings"] ?? "—")}</p>
        </div>
        <div>
          <p className="font-medium">Closed Findings</p>
          <p className="text-lg font-bold">{String(details["closed_findings"] ?? "—")}</p>
        </div>
        <div>
          <p className="font-medium">Applied Deduction</p>
          <p className="text-lg font-bold" style={{ color: "#dc2626" }}>−{String(details["applied_deduction"] ?? "—")}</p>
        </div>
      </div>
      {details["open_by_severity"] != null && (
        <div className="mt-2 pt-2 border-t" style={{ borderColor: "var(--border)" }}>
          <p className="text-[9px] uppercase tracking-wider font-semibold mb-1" style={{ color: "var(--muted-foreground)" }}>Open by Severity</p>
          <div className="flex gap-3">
            {Object.entries(details["open_by_severity"] as Record<string, number>).map(([sev, count]) => (
              <span key={sev} className="text-[10px] font-medium">
                <span style={{ color: sev === "CRITICAL" ? "#dc2626" : sev === "HIGH" ? "#ea580c" : sev === "MEDIUM" ? "#d97706" : "#2563eb" }}>{sev}</span>
                {" "}{count}
              </span>
            ))}
          </div>
        </div>
      )}
      {typeof details["formula"] === "string" && (
        <div className="mt-2 pt-2 border-t" style={{ borderColor: "var(--border)" }}>
          <p className="text-[9px] uppercase tracking-wider font-semibold mb-0.5" style={{ color: "var(--muted-foreground)" }}>Formula</p>
          <p className="text-[10px] font-mono">{String(details["formula"])}</p>
        </div>
      )}
    </div>
  );
}
