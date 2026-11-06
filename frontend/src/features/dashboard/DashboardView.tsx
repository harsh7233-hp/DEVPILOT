"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { useAuth } from "@/lib/auth-context";
import { useSelectedRepo } from "@/lib/repo-context";
import { api } from "@/lib/api";
import type {
  IntelligenceReport,
  DeepScanReport,
  DevPilotInsight,
  SecurityFinding,
} from "@/lib/api";
import { scoreColor } from "@/features/intelligence/shared";

/* ═══════════════════════════════════════════════════════════════════════════════
   DashboardView — Clean summary page
   ═══════════════════════════════════════════════════════════════════════════════ */

export function DashboardView() {
  const { user, loading: authLoading } = useAuth();
  const { repo, branch } = useSelectedRepo();
  const [intelReport, setIntelReport] = useState<IntelligenceReport | null>(null);
  const [deepScan, setDeepScan] = useState<DeepScanReport | null>(null);
  const [insights, setInsights] = useState<DevPilotInsight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const owner = repo?.owner ?? "";
  const repoName = repo?.name ?? "";
  const hasRepo = Boolean(owner && repoName);

  useEffect(() => {
    if (authLoading) return;
    let cancelled = false;

    async function load() {
      if (!hasRepo) {
        setLoading(false);
        return;
      }
      try {
        const [intel, sec, ins] = await Promise.allSettled([
          api.intelligence.report(owner, repoName),
          api.security.report(owner, repoName),
          api.ai2.insights(owner, repoName),
        ]);
        if (cancelled) return;
        if (intel.status === "fulfilled") setIntelReport(intel.value.available ? intel.value : null);
        if (sec.status === "fulfilled") setDeepScan(sec.value.available ? sec.value : null);
        if (ins.status === "fulfilled") setInsights(ins.value.insights ?? []);
      } catch {
        if (!cancelled) setError("Failed to load dashboard data");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [authLoading, owner, repoName, hasRepo]);

  if (authLoading || loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  const userName = user?.name || user?.login;
  const greeting = getGreeting();

  // Not authenticated — show GitHub connection state
  if (!user) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 space-y-8 max-w-3xl mx-auto">
        <section>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight">
            {greeting} 👋
          </h1>
          <p className="text-sm mt-1.5" style={{ color: "var(--muted-foreground)" }}>
            Connect your GitHub account to get started.
          </p>
        </section>
        <Card className="text-center py-12">
          <div className="flex flex-col items-center gap-3">
            <div className="h-10 w-10 rounded-full flex items-center justify-center" style={{ background: "var(--muted)" }}>
              <svg className="h-5 w-5" style={{ color: "var(--muted-foreground)" }} fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.55 0-.27-.01-1.17-.02-2.12-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.19 1.76 1.19 1.03 1.75 2.69 1.25 3.34.95.1-.74.4-1.25.72-1.53-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11.1 11.1 0 015.8 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09 0 4.42-2.7 5.39-5.27 5.68.41.35.78 1.05.78 2.12 0 1.53-.01 2.76-.01 3.14 0 .3.2.67.8.55A11.51 11.51 0 0023.5 12C23.5 5.65 18.35.5 12 .5z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium">GitHub Not Connected</p>
              <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
                Connect your GitHub account to analyze repositories with DevPilot.
              </p>
            </div>
            <a
              href={api.auth.getGithubUrl()}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 transition-colors mt-1"
            >
              Connect GitHub
            </a>
          </div>
        </Card>
      </div>
    );
  }

  // Authenticated but no repo — show no repository state
  if (!hasRepo) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 space-y-8 max-w-3xl mx-auto">
        <section>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight">
            {greeting}{userName ? `, ${userName}` : ""} 👋
          </h1>
          <p className="text-sm mt-1.5" style={{ color: "var(--muted-foreground)" }}>
            Here&apos;s the current health of your repository.
          </p>
        </section>
        <Card className="text-center py-12">
          <div className="flex flex-col items-center gap-3">
            <div className="h-10 w-10 rounded-full flex items-center justify-center" style={{ background: "var(--muted)" }}>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" style={{ color: "var(--muted-foreground)" }}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium">No Repository Connected</p>
              <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
                Select a repository from the header to see its health overview.
              </p>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-8 max-w-3xl mx-auto">

      {/* ── Greeting ── */}
      <section>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight">
          {greeting}{userName ? `, ${userName}` : ""} 👋
        </h1>
        <p className="text-sm mt-1.5" style={{ color: "var(--muted-foreground)" }}>
          Here&apos;s the current health of your repository.
        </p>
        {hasRepo && (
          <div className="flex items-center gap-2 mt-3">
            <span className="text-sm font-medium">{repo!.fullName}</span>
            {branch && (
              <span className="text-xs px-1.5 py-0.5 rounded-md" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}>
                {branch}
              </span>
            )}
          </div>
        )}
      </section>

      {/* ── Primary Health Card ── */}
      {hasRepo && intelReport && (
        <HealthCard report={intelReport} />
      )}

      {/* ── Secondary Metrics ── */}
      {hasRepo && (
        <div className="grid grid-cols-3 gap-3">
          <SmallMetric
            label="Security"
            value={deepScan?.posture?.score != null ? String(deepScan.posture.score) : "—"}
            detail={deepScan?.posture ? (deepScan.posture.failed_checks > 0 ? `${deepScan.posture.failed_checks} failed` : "Secure") : "No scan"}
            color={deepScan?.posture?.score != null ? scoreColor(deepScan.posture.score) : undefined}
          />
          <SmallMetric
            label="Dependencies"
            value={intelReport ? String(intelReport.stats.external_dependencies) : "—"}
            detail={deepScan?.dependencies?.vulnerabilities?.length ? `${deepScan.dependencies.vulnerabilities.length} outdated` : "Up to date"}
            color={deepScan?.dependencies?.vulnerabilities?.length ? "#d97706" : undefined}
          />
          <SmallMetric
            label="Issues"
            value={intelReport ? String(intelReport.health.counts.critical + intelReport.health.counts.high + intelReport.health.counts.medium + intelReport.health.counts.low) : "—"}
            detail={intelReport && intelReport.health.counts.critical > 0 ? `${intelReport.health.counts.critical} critical` : "None critical"}
            color={intelReport && intelReport.health.counts.critical > 0 ? "#dc2626" : undefined}
          />
        </div>
      )}

      {/* ── Needs Attention ── */}
      {hasRepo && (
        <NeedsAttention deepScan={deepScan} intelReport={intelReport} />
      )}

      {/* ── Recent Activity ── */}
      {hasRepo && (
        <RecentActivity deepScan={deepScan} intelReport={intelReport} />
      )}

      {/* ── AI Recommendation ── */}
      {hasRepo && insights.length > 0 && (
        <AIRecommendation insight={insights[0]} />
      )}

      {/* ── No Data State ── */}
      {hasRepo && !intelReport && !deepScan && (
        <Card className="text-center py-10">
          <p className="text-sm mb-3" style={{ color: "var(--muted-foreground)" }}>
            No analysis data yet for this repository.
          </p>
          <Link href="/intelligence">
            <Button size="sm" variant="secondary">Run Code Intelligence</Button>
          </Link>
        </Card>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   Health Card — Primary
   ═══════════════════════════════════════════════════════════════════════════════ */

function HealthCard({ report }: { report: IntelligenceReport }) {
  const score = report.health.overall;
  const label = score >= 80 ? "GOOD" : score >= 60 ? "FAIR" : "NEEDS WORK";
  const categories = Object.entries(report.health.categories);

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center gap-6">
        {/* Score */}
        <div className="flex flex-col items-center shrink-0">
          <HealthRing score={score} size={100} />
          <p className="text-xs font-semibold mt-2 tracking-wide" style={{ color: scoreColor(score) }}>
            {label}
          </p>
        </div>

        {/* Category bars */}
        <div className="flex-1 space-y-2.5 min-w-0">
          {categories.map(([name, val]) => (
            <div key={name}>
              <div className="flex justify-between text-[11px] mb-0.5">
                <span className="truncate" style={{ color: "var(--muted-foreground)" }}>{name}</span>
                <span className="font-medium shrink-0 ml-2" style={{ color: scoreColor(val) }}>{val}</span>
              </div>
              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "var(--border)" }}>
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${val}%`, background: scoreColor(val) }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* View details */}
      <div className="mt-4 pt-3 border-t flex justify-end" style={{ borderColor: "var(--border)" }}>
        <Link href="/security" className="text-xs font-medium hover:underline" style={{ color: "var(--muted-foreground)" }}>
          View detailed health →
        </Link>
      </div>
    </Card>
  );
}

function HealthRing({ score, size = 100 }: { score: number; size?: number }) {
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} stroke="var(--border)" />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          strokeWidth={stroke} strokeLinecap="round"
          stroke={scoreColor(score)}
          strokeDasharray={`${(score / 100) * c} ${c}`}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold leading-none" style={{ color: scoreColor(score) }}>{score}</span>
        <span className="text-[9px] mt-0.5" style={{ color: "var(--muted-foreground)" }}>/ 100</span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   Small Metric
   ═══════════════════════════════════════════════════════════════════════════════ */

function SmallMetric({ label, value, detail, color }: {
  label: string;
  value: string;
  detail: string;
  color?: string;
}) {
  return (
    <div className="rounded-lg p-3" style={{ background: "var(--card)" }}>
      <p className="text-[10px] uppercase tracking-wider font-medium" style={{ color: "var(--muted-foreground)" }}>
        {label}
      </p>
      <p className="text-lg font-bold mt-0.5" style={{ color: color || "var(--foreground)" }}>
        {value}
      </p>
      <p className="text-[10px] mt-0.5" style={{ color: "var(--muted-foreground)" }}>
        {detail}
      </p>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   Needs Attention — Top 3
   ═══════════════════════════════════════════════════════════════════════════════ */

function NeedsAttention({ deepScan, intelReport }: { deepScan: DeepScanReport | null; intelReport: IntelligenceReport | null }) {
  const items = useMemo(() => {
    const result: { icon: string; text: string; href: string; color: string }[] = [];

    // Security findings
    if (deepScan?.findings) {
      const critical = deepScan.findings.filter((f) => f.severity === "CRITICAL" || f.severity === "HIGH");
      if (critical.length > 0) {
        result.push({
          icon: "🔴",
          text: `${critical.length} critical security ${critical.length === 1 ? "vulnerability" : "vulnerabilities"}`,
          href: "/security",
          color: "#dc2626",
        });
      }
    }

    // Dependency issues
    if (deepScan?.dependencies?.vulnerabilities?.length) {
      const vulns = deepScan.dependencies.vulnerabilities;
      result.push({
        icon: "🟠",
        text: `${vulns.length} outdated ${vulns.length === 1 ? "dependency" : "dependencies"}`,
        href: "/security",
        color: "#d97706",
      });
    }

    // High complexity / intelligence issues
    if (intelReport?.issues) {
      const high = intelReport.issues.filter((i) => i.severity === "CRITICAL" || i.severity === "HIGH");
      if (high.length > 0) {
        const top = high[0];
        result.push({
          icon: "🟡",
          text: `${top.problem.slice(0, 60)}${top.problem.length > 60 ? "..." : ""}`,
          href: "/intelligence",
          color: "#d97706",
        });
      }
    }

    // Fill remaining with medium items
    if (result.length < 3 && intelReport?.issues) {
      const medium = intelReport.issues.filter((i) => i.severity === "MEDIUM");
      for (const issue of medium) {
        if (result.length >= 3) break;
        if (result.some((r) => r.text === issue.problem.slice(0, 60))) continue;
        result.push({
          icon: "🟡",
          text: `${issue.problem.slice(0, 60)}${issue.problem.length > 60 ? "..." : ""}`,
          href: "/intelligence",
          color: "#d97706",
        });
      }
    }

    return result.slice(0, 3);
  }, [deepScan, intelReport]);

  if (items.length === 0) return null;

  return (
    <section>
      <h2 className="text-sm font-semibold mb-2">Needs Attention</h2>
      <div className="space-y-1.5">
        {items.map((item, i) => (
          <Link
            key={i}
            href={item.href}
            className="flex items-center justify-between px-3 py-2.5 rounded-lg border transition-colors hover:border-[var(--border-hover)]"
            style={{ borderColor: "var(--border)" }}
          >
            <span className="flex items-center gap-2 min-w-0">
              <span className="text-xs shrink-0">{item.icon}</span>
              <span className="text-[13px] truncate" style={{ color: "var(--foreground)" }}>{item.text}</span>
            </span>
            <span className="text-[11px] font-medium shrink-0 ml-2" style={{ color: "var(--muted-foreground)" }}>View →</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   Recent Activity — Max 4
   ═══════════════════════════════════════════════════════════════════════════════ */

function RecentActivity({ deepScan, intelReport }: { deepScan: DeepScanReport | null; intelReport: IntelligenceReport | null }) {
  const events = useMemo(() => {
    const result: { icon: string; text: string; time: string }[] = [];

    if (deepScan) {
      const ts = deepScan.generated_at;
      result.push({
        icon: "✓",
        text: "Security scan completed",
        time: formatTimeAgo(ts),
      });
    }

    if (intelReport) {
      const ts = intelReport.generated_at;
      result.push({
        icon: "✓",
        text: "Code intelligence analysis completed",
        time: formatTimeAgo(ts),
      });
    }

    if (deepScan?.dependencies?.status === "completed") {
      result.push({
        icon: "✓",
        text: "Dependency analysis completed",
        time: deepScan.generated_at ? formatTimeAgo(deepScan.generated_at) : "Recently",
      });
    }

    return result.slice(0, 4);
  }, [deepScan, intelReport]);

  if (events.length === 0) return null;

  return (
    <section>
      <h2 className="text-sm font-semibold mb-2">Recent Activity</h2>
      <div className="space-y-0.5">
        {events.map((event, i) => (
          <div key={i} className="flex items-center justify-between py-2 px-1">
            <span className="flex items-center gap-2 min-w-0">
              <span className="text-emerald-400 text-xs shrink-0">{event.icon}</span>
              <span className="text-[13px] truncate" style={{ color: "var(--foreground)" }}>{event.text}</span>
            </span>
            <span className="text-[11px] shrink-0 ml-3" style={{ color: "var(--muted-foreground)" }}>{event.time}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   AI Recommendation — Single
   ═══════════════════════════════════════════════════════════════════════════════ */

function AIRecommendation({ insight }: { insight: DevPilotInsight }) {
  return (
    <section>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-emerald-400 text-sm">✦</span>
        <h2 className="text-sm font-semibold">DevPilot Recommendation</h2>
      </div>
      <Link
        href={insight.href}
        className="block p-4 rounded-lg border transition-colors hover:border-emerald-500/30 hover:bg-emerald-500/5"
        style={{ borderColor: "var(--border)" }}
      >
        <p className="text-[13px] font-medium mb-1">{insight.title}</p>
        <p className="text-[12px] leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
          {insight.detail}
        </p>
        {insight.evidence.length > 0 && (
          <p className="text-[11px] mt-2" style={{ color: "var(--muted-foreground)" }}>
            {insight.evidence.slice(0, 2).map((e) => e.label).join(" · ")}
          </p>
        )}
      </Link>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════════════════════════ */

function getGreeting(): string {
  const h = new Date().getHours();
  if (h >= 5 && h < 12) return "Good morning";
  if (h >= 12 && h < 17) return "Good afternoon";
  return "Good evening";
}

function formatTimeAgo(ts: number): string {
  const diff = Math.floor((Date.now() / 1000) - ts);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
  return `${Math.floor(diff / 86400)} days ago`;
}
