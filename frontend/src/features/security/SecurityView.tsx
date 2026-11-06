"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { RepoSelector } from "@/components/ui/RepoSelector";
import { HealthOverviewCards } from "@/features/security/HealthOverviewCards";
import { FindingDetailPanel } from "@/features/security/FindingDetailPanel";
import { PriorityQueue } from "@/features/security/PriorityQueue";
import { SecurityCoverage } from "@/features/security/SecurityCoverage";
import { SecurityDisclaimer } from "@/features/security/SecurityDisclaimer";
import {
  useDeepScan,
  scoreColor,
  severityBadgeVariant,
  confidenceBadgeVariant,
  SEVERITY_STYLE,
  ScoreRing,
} from "@/features/security/shared";
import { api } from "@/lib/api";
import type { DeepScanJobStatus, DeepScanReport, SecurityFinding, PriorityItem, SecretFinding, PerformanceFinding } from "@/lib/api";

export function SecurityView() {
  const [repoValue, setRepoValue] = useState("");
  const [owner = "", repo = ""] = repoValue.split("/");
  const { report, loading, scanning, job, error, startScan } = useDeepScan(owner, repo);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 pb-3 border-b shrink-0" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="min-w-0">
            <h1 className="text-lg sm:text-xl font-bold tracking-tight truncate">Security & Code Health</h1>
            <p className="text-xs mt-0.5 hidden sm:block" style={{ color: "var(--muted-foreground)" }}>
              Evidence-based security posture, code health scores, and performance analysis
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <RepoSelector value={repoValue} onChange={(o, r) => setRepoValue(`${o}/${r}`)} className="flex-1 min-w-0 sm:max-w-56" />
          <Button size="sm" onClick={() => startScan()} disabled={!owner || scanning} className="shrink-0 whitespace-nowrap">
            {scanning ? "Scanning..." : report ? "Run Deep Scan" : "Start Deep Scan"}
          </Button>
        </div>
        <SecurityDisclaimer className="mt-3" placement="bottom" />
      </div>

      {scanning && job && <ScanProgress job={job} />}
      {error && <ErrorState message={error} onRetry={() => startScan()} />}

      {!owner || !repo ? (
        <div className="flex-1 flex items-center justify-center p-4">
          <EmptyState icon="🛡️" title="Select a repository" description="Choose a repository to run a comprehensive security and health analysis." />
        </div>
      ) : loading ? (
        <LoadingState message="Loading security report..." />
      ) : !report ? (
        <div className="flex-1 flex items-center justify-center p-4">
          <EmptyState
            icon="🛡️"
            title="No deep scan yet"
            description="Run a deep scan to analyze security rules, detect secrets, measure code health, and detect performance patterns."
            action={<Button onClick={() => startScan()}>{scanning ? "Scanning..." : "Start Deep Scan"}</Button>}
          />
        </div>
      ) : (
        <SecurityReportContent report={report} owner={owner} repo={repo} onRescan={() => startScan()} scanning={scanning} />
      )}
    </div>
  );
}

function SecurityReportContent({
  report,
  owner,
  repo,
  onRescan,
  scanning,
}: {
  report: DeepScanReport;
  owner: string;
  repo: string;
  onRescan: () => void;
  scanning: boolean;
}) {
  const [selectedFinding, setSelectedFinding] = useState<SecurityFinding | null>(null);
  const [selectedPriority, setSelectedPriority] = useState<PriorityItem | null>(null);
  const [updating, setUpdating] = useState(false);

  const handleStatusChange = useCallback(async (fingerprint: string, status: string, note: string) => {
    setUpdating(true);
    try {
      await api.security.updateFindingStatus(owner, repo, fingerprint, status, note);
      // Refresh the report
      window.location.reload();
    } catch {
      // ignore
    } finally {
      setUpdating(false);
    }
  }, [owner, repo]);

  const handlePrioritySelect = useCallback((item: PriorityItem) => {
    // Find the matching finding
    const match = report.findings.find((f) => f.fingerprint === item.fingerprint);
    if (match) {
      setSelectedFinding(match);
      setSelectedPriority(null);
    }
  }, [report.findings]);

  const posture = report.posture;
  const secrets = report.secrets || [];
  const findings = report.findings || [];
  const perfIssues = report.performance_issues || [];
  const priorityItems = report.priority_queue || [];
  const deps = report.dependencies;

  return (
    <div className="flex-1 overflow-y-auto overscroll-contain p-4 space-y-6 max-w-6xl">
      {/* Header row with posture score */}
      <div className="flex flex-col sm:flex-row items-center gap-6">
        <ScoreRing score={posture?.score ?? null} size={120} />
        <div className="min-w-0 flex-1 w-full space-y-2">
          <h2 className="text-sm font-semibold">Security Posture</h2>
          {posture ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={posture.score != null && posture.score >= 70 ? "success" : posture.score != null && posture.score >= 40 ? "warning" : "error"}>
                  {posture.score}/100
                </Badge>
                <span className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
                  {posture.executed_checks} checks executed · {posture.passed_checks} passed · {posture.open_findings} open findings
                </span>
              </div>
              <div className="rounded-lg p-2.5" style={{ background: "var(--muted)" }}>
                <p className="text-[10px] uppercase tracking-wider font-semibold mb-0.5" style={{ color: "var(--muted-foreground)" }}>How is Security Posture calculated?</p>
                <p className="text-[10px] font-mono">{posture.formula}</p>
                <p className="text-[10px] mt-1" style={{ color: "var(--muted-foreground)" }}>{posture.note}</p>
              </div>
            </>
          ) : (
            <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>No security checks were executable — posture not analyzed.</p>
          )}
        </div>
      </div>

      {/* Health overview cards */}
      <HealthOverviewCards report={report} />

      {/* Counts summary */}
      <CountsSummary report={report} />

      {/* Security findings */}
      <section aria-label="Security findings">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-sm font-semibold">Security Findings ({findings.length})</h2>
          <div className="flex gap-1.5">
            {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((sev) => {
              const count = findings.filter((f) => f.severity === sev && (f.status || "open") === "open").length;
              if (count === 0) return null;
              return <Badge key={sev} variant={severityBadgeVariant(sev)} className="text-[9px]">{sev}: {count}</Badge>;
            })}
          </div>
        </div>
        {selectedFinding ? (
          <FindingDetailPanel
            finding={selectedFinding}
            onClose={() => setSelectedFinding(null)}
            onStatusChange={handleStatusChange}
            updating={updating}
          />
        ) : findings.length === 0 ? (
          <Card padding="md">
            <EmptyState icon="🔒" title="No security findings" description="No security rule violations detected in analyzed source files." />
          </Card>
        ) : (
          <Card padding="none">
            <div className="divide-y max-h-80 overflow-y-auto" style={{ borderColor: "var(--border)" }}>
              {findings.slice(0, 50).map((f) => (
                <FindingRow key={f.fingerprint} finding={f} onClick={() => setSelectedFinding(f)} />
              ))}
              {findings.length > 50 && (
                <div className="px-4 py-2 text-[10px] text-center" style={{ color: "var(--muted-foreground)" }}>
                  Showing 50 of {findings.length} findings
                </div>
              )}
            </div>
          </Card>
        )}
      </section>

      {/* Secrets */}
      {secrets.length > 0 && (
        <section aria-label="Secret detection">
          <h2 className="text-sm font-semibold mb-2.5">Secret Detection ({secrets.length})</h2>
          <Card padding="none">
            <div className="divide-y max-h-60 overflow-y-auto" style={{ borderColor: "var(--border)" }}>
              {secrets.map((s) => (
                <SecretRow key={s.fingerprint} secret={s} />
              ))}
            </div>
          </Card>
        </section>
      )}

      {/* Performance issues */}
      {perfIssues.length > 0 && (
        <section aria-label="Performance issues">
          <h2 className="text-sm font-semibold mb-2.5">Performance Patterns ({perfIssues.length})</h2>
          <Card padding="none">
            <div className="divide-y max-h-60 overflow-y-auto" style={{ borderColor: "var(--border)" }}>
              {perfIssues.slice(0, 30).map((p) => (
                <PerfRow key={p.fingerprint} perf={p} />
              ))}
            </div>
          </Card>
          <p className="text-[10px] mt-1.5" style={{ color: "var(--muted-foreground)" }}>
            Static analysis only — no runtime measurements. All results are potential issues.
          </p>
        </section>
      )}

      {/* Dependencies */}
      {deps && deps.packages.length > 0 && (
        <section aria-label="Dependencies">
          <h2 className="text-sm font-semibold mb-2.5">Dependencies ({deps.packages.length})</h2>
          {deps.vulnerabilities.length > 0 && (
            <div className="rounded-xl p-4 mb-3 border-l-4" style={{ borderColor: "#dc2626", background: "var(--card)", border: "1px solid var(--border)", borderLeftColor: "#dc2626" }}>
              <p className="text-xs font-semibold" style={{ color: "#dc2626" }}>
                {deps.vulnerabilities.length} known vulnerability/vulnerabilities detected
              </p>
              <div className="mt-2 space-y-1.5">
                {deps.vulnerabilities.map((v, i) => (
                  <div key={i} className="text-[11px]">
                    <span className="font-medium">{v.package}</span>
                    <span className="mx-1" style={{ color: "var(--muted-foreground)" }}>·</span>
                    <Badge variant={v.severity === "CRITICAL" || v.severity === "HIGH" ? "error" : "warning"} className="text-[9px]">{v.severity}</Badge>
                    <span className="mx-1" style={{ color: "var(--muted-foreground)" }}>{v.vulnerability_id}</span>
                    {v.recommended_version && (
                      <span className="ml-1" style={{ color: "#059669" }}>→ update to {v.recommended_version}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          <Card padding="sm">
            <div className="flex flex-wrap gap-1.5">
              {deps.packages.slice(0, 30).map((p) => (
                <span key={p.name} className="text-[10px] font-mono px-1.5 py-0.5 rounded" style={{ background: "var(--muted)" }}>
                  {p.name}{p.version ? `@${p.version}` : ""}
                </span>
              ))}
              {deps.packages.length > 30 && (
                <span className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>+{deps.packages.length - 30} more</span>
              )}
            </div>
          </Card>
        </section>
      )}

      {/* Priority queue */}
      <PriorityQueue items={priorityItems} onSelect={handlePrioritySelect} />

      {/* Security coverage */}
      {report.coverage && <SecurityCoverage coverage={report.coverage} />}

      {/* Scan metadata */}
      <div className="rounded-lg p-3 text-[10px]" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}>
        <p><strong>Analysis kind:</strong> {report.analysis_kind}</p>
        <p className="mt-0.5"><strong>Disclaimer:</strong> {report.disclaimer}</p>
        <p className="mt-0.5"><strong>Generated:</strong> {new Date(report.generated_at * 1000).toLocaleString()}</p>
        <p className="mt-0.5"><strong>Branch:</strong> {report.branch}</p>
      </div>
    </div>
  );
}

/* ── Sub-components ── */

function ScanProgress({ job }: { job: DeepScanJobStatus }) {
  return (
    <div className="border-b px-4 py-3" style={{ borderColor: "var(--border)", background: "var(--muted)" }}>
      <div className="flex items-center gap-3">
        <div className="animate-spin h-4 w-4 border-2 border-t-transparent rounded-full" style={{ borderColor: "var(--border)", borderTopColor: "transparent" }} />
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium">{job.message}</p>
          <div className="h-1.5 rounded-full mt-1.5 overflow-hidden" style={{ background: "var(--border)" }}>
            <div className="h-full rounded-full transition-all duration-500" style={{ width: `${job.progress * 100}%`, background: "#10b981" }} />
          </div>
        </div>
        <span className="text-[10px] shrink-0" style={{ color: "var(--muted-foreground)" }}>{Math.round(job.progress * 100)}%</span>
      </div>
      {job.stages && job.stages.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {job.stages.map((stage, i) => (
            <span
              key={i}
              className="text-[9px] px-1.5 py-0.5 rounded"
              style={{
                background: i < job.stage ? "#059669" : i === job.stage ? "#10b981" : "var(--border)",
                color: i <= job.stage ? "white" : "var(--muted-foreground)",
              }}
            >
              {stage}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function CountsSummary({ report }: { report: DeepScanReport }) {
  const counts = report.counts;
  const secCounts = counts.security;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <CountCard label="Security" value={findingsOpen(secCounts)} color="#dc2626" detail={`${counts.total_findings} total findings`} />
      <CountCard label="Secrets" value={counts.secrets} color="#d97706" detail="Masked previews shown" />
      <CountCard label="Performance" value={findingsOpen(counts.performance)} color="#2563eb" detail="Static analysis patterns" />
      <CountCard label="Priority" value={report.priority_queue.length} color="#8b5cf6" detail="Items in queue" />
    </div>
  );
}

function findingsOpen(counts: Record<string, number>): number {
  return (counts.CRITICAL || 0) + (counts.HIGH || 0) + (counts.MEDIUM || 0) + (counts.LOW || 0);
}

function CountCard({ label, value, color, detail }: { label: string; value: number; color: string; detail: string }) {
  return (
    <Card padding="sm">
      <p className="text-[10px] uppercase tracking-wider font-medium" style={{ color: "var(--muted-foreground)" }}>{label}</p>
      <p className="text-xl font-bold mt-0.5" style={{ color }}>{value}</p>
      <p className="text-[9px] mt-0.5" style={{ color: "var(--muted-foreground)" }}>{detail}</p>
    </Card>
  );
}

function FindingRow({ finding, onClick }: { finding: SecurityFinding; onClick: () => void }) {
  const sevStyle = SEVERITY_STYLE[finding.severity] || SEVERITY_STYLE.LOW;
  const status = finding.status || "open";
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-black/[0.03] dark:hover:bg-white/[0.03] transition-colors"
    >
      <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: sevStyle.color }} />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium truncate">{finding.title}</p>
        <p className="text-[10px] truncate" style={{ color: "var(--muted-foreground)" }}>
          {finding.file}:{finding.line}{finding.symbol ? ` in ${finding.symbol}` : ""}
        </p>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <Badge variant={severityBadgeVariant(finding.severity)} className="text-[9px]">{finding.severity}</Badge>
        <Badge variant={confidenceBadgeVariant(finding.confidence)} className="text-[9px]">{finding.confidence}</Badge>
        {status !== "open" && (
          <Badge variant="default" className="text-[9px]">{status}</Badge>
        )}
        <Link
          href="/code-explorer"
          className="text-[9px] underline ml-1"
          style={{ color: "var(--muted-foreground)" }}
          onClick={(e) => e.stopPropagation()}
        >
          View file
        </Link>
      </div>
    </button>
  );
}

function SecretRow({ secret }: { secret: SecretFinding }) {
  return (
    <div className="px-4 py-2.5">
      <div className="flex items-center gap-2">
        <Badge variant="error" className="text-[9px]">{secret.severity}</Badge>
        <span className="text-xs font-mono font-medium" style={{ color: "#dc2626" }}>{secret.masked_preview}</span>
      </div>
      <p className="text-[10px] mt-1 truncate" style={{ color: "var(--muted-foreground)" }}>
        {secret.file}:{secret.line} · {secret.title}
      </p>
    </div>
  );
}

function PerfRow({ perf }: { perf: PerformanceFinding }) {
  const sevStyle = SEVERITY_STYLE[perf.severity] || SEVERITY_STYLE.LOW;
  return (
    <div className="px-4 py-2.5 flex items-start gap-3">
      <span className="h-2 w-2 rounded-full shrink-0 mt-1" style={{ background: sevStyle.color }} />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium">{perf.title}</p>
        <p className="text-[10px] truncate" style={{ color: "var(--muted-foreground)" }}>
          {perf.file}:{perf.line}{perf.symbol ? ` in ${perf.symbol}` : ""}
        </p>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <Badge variant={perf.severity === "HIGH" ? "error" : perf.severity === "MEDIUM" ? "warning" : "info"} className="text-[9px]">
          {perf.severity}
        </Badge>
        <Link
          href="/code-explorer"
          className="text-[9px] underline"
          style={{ color: "var(--muted-foreground)" }}
        >
          View file
        </Link>
      </div>
    </div>
  );
}
