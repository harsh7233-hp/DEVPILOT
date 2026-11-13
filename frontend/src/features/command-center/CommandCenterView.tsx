"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAuth } from "@/lib/auth-context";
import { useSelectedRepo } from "@/lib/repo-context";
import { api, EMPTY_RISK_MAP, type RiskMapReport, type DeepScanReport, type DeepScanJobStatus, type PipelinesReport } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { scoreColor, useIntelligence } from "@/features/intelligence/shared";
import { StageProgress } from "@/features/intelligence/CodeIntelligenceView";
import { HealthOverviewCards } from "@/features/security/HealthOverviewCards";
import { InsightsPanel } from "@/features/ai-assistant/InsightsPanel";
import { AskDevPilotPanel } from "@/features/ai-assistant/AskDevPilotPanel";
import { ScoreRing as SecurityScoreRing } from "@/features/security/shared";

type MetricState =
  | { kind: "loading" }
  | { kind: "value"; value: string; sub?: string }
  | { kind: "unavailable"; reason: string };

export function CommandCenterView() {
  const { user, loading: authLoading } = useAuth();
  const { repo, branch, hydrated } = useSelectedRepo();
  const owner = repo?.owner ?? "";
  const name = repo?.name ?? "";

  const intel = useIntelligence(owner, name);
  const [repoMeta, setRepoMeta] = useState<Awaited<ReturnType<typeof api.dashboard.getRepo>> | null>(null);
  const [metaLoading, setMetaLoading] = useState(false);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [riskState, setRiskState] = useState<{ key: string; data: RiskMapReport } | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [graphBusy, setGraphBusy] = useState(false);
  const [deepScanReport, setDeepScanReport] = useState<DeepScanReport | null>(null);
  const [deepScanLoading, setDeepScanLoading] = useState(false);
  const [deepScanJob, setDeepScanJob] = useState<DeepScanJobStatus | null>(null);
  const [deepScanBusy, setDeepScanBusy] = useState(false);
  const [pipelines, setPipelines] = useState<PipelinesReport | null>(null);
  const repoKey = owner && name ? `${owner}/${name}` : "";

  /* ── Repository metadata + analysis jobs (real records) ── */
  useEffect(() => {
    if (!repoKey) return;
    let cancelled = false;
    queueMicrotask(() => {
      setMetaLoading(true);
      setMetaError(null);
    });
    api.dashboard
      .getRepo(owner, name)
      .then((d) => {
        if (!cancelled && d.owner === owner && d.repo === name) setRepoMeta(d);
      })
      .catch((err) => !cancelled && setMetaError(err instanceof Error ? err.message : "Failed to load repository state"))
      .finally(() => !cancelled && setMetaLoading(false));
    return () => {
      cancelled = true;
    };
  }, [owner, name, repoKey]);

  /* ── Architecture risk map (derived from the real dependency graph) ── */
  useEffect(() => {
    if (!repoKey) return;
    let cancelled = false;
    queueMicrotask(() => setRiskLoading(true));
    const [o, n] = repoKey.split("/");
    api.intelligence
      .riskMap(o, n)
      .then((r) => !cancelled && setRiskState({ key: repoKey, data: r }))
      .catch(() => !cancelled && setRiskState({ key: repoKey, data: EMPTY_RISK_MAP }))
      .finally(() => !cancelled && setRiskLoading(false));
    return () => {
      cancelled = true;
    };
  }, [repoKey]);

  const reloadRiskMap = useCallback(() => {
    if (!owner || !name) return;
    setRiskLoading(true);
    api.intelligence
      .riskMap(owner, name)
      .then((r) => setRiskState({ key: `${owner}/${name}`, data: r }))
      .catch(() => setRiskState({ key: `${owner}/${name}`, data: EMPTY_RISK_MAP }))
      .finally(() => setRiskLoading(false));
  }, [owner, name]);

  // Only render risk data that belongs to the currently selected repository.
  const riskMap = riskState && riskState.key === repoKey ? riskState.data : null;

  /* ── Deep scan report ── */
  useEffect(() => {
    if (!repoKey) return;
    let cancelled = false;
    queueMicrotask(() => setDeepScanLoading(true));
    const [o, n] = repoKey.split("/");
    api.security.report(o, n)
      .then((r) => {
        if (!cancelled) setDeepScanReport(r.available ? r : null);
      })
      .catch(() => { if (!cancelled) setDeepScanReport(null); })
      .finally(() => { if (!cancelled) setDeepScanLoading(false); });
    return () => { cancelled = true; };
  }, [repoKey]);

  /* ── Pipeline detection ── */
  useEffect(() => {
    if (!repoKey) return;
    let cancelled = false;
    const [o, n] = repoKey.split("/");
    api.intelligence
      .pipelines(o, n)
      .then((r) => !cancelled && setPipelines(r.available ? r : null))
      .catch(() => !cancelled && setPipelines(null));
    return () => { cancelled = true; };
  }, [repoKey]);

  const runDeepScan = useCallback(async () => {
    if (!owner || !name || deepScanBusy) return;
    setDeepScanBusy(true);
    try {
      const res = await api.security.startScan(owner, name, branch || "main", true);
      if (res.cached) {
        const r = await api.security.report(owner, name);
        setDeepScanReport(r.available ? r : null);
        return;
      }
      if (!res.job_id) return;
      setDeepScanJob({
        id: res.job_id, owner, repo: name, branch: branch || "main", status: "pending",
        progress: 0, stage: 0, message: "Starting deep scan...", stages: [], error: null,
      });
      const poll = setInterval(async () => {
        try {
          const { job: j } = await api.security.scanStatus(owner, name, res.job_id as string);
          setDeepScanJob(j);
          if (j.status === "completed" || j.status === "failed") {
            clearInterval(poll);
            setDeepScanBusy(false);
            if (j.status === "completed") {
              const r = await api.security.report(owner, name);
              setDeepScanReport(r.available ? r : null);
            }
          }
        } catch { /* keep polling */ }
      }, 1500);
    } catch {
      setDeepScanBusy(false);
    }
  }, [owner, name, branch, deepScanBusy]);

  const buildGraph = async () => {
    if (!owner || !name) return;
    setGraphBusy(true);
    try {
      await api.graph.build(owner, name);
      reloadRiskMap();
    } catch {
      /* error surfaced via empty risk map state */
    } finally {
      setGraphBusy(false);
    }
  };

  if (authLoading || !hydrated) {
    return (
      <div className="p-4 sm:p-6 max-w-7xl space-y-4" aria-busy="true">
        <SkeletonBlock className="h-24" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonBlock key={i} className="h-20" />
          ))}
        </div>
        <SkeletonBlock className="h-40" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="p-4 sm:p-6 max-w-7xl">
        <EmptyState
          icon="&#x1F517;"
          title="Connect your GitHub account"
          description="DevPilot reads live data from repositories you have access to. Connect GitHub to activate your Command Center."
          action={
            <a
              href={api.auth.getGithubUrl()}
              className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 transition-colors"
            >
              Connect GitHub
            </a>
          }
        />
      </div>
    );
  }

  if (!repo) {
    return (
      <div className="p-4 sm:p-6 max-w-7xl space-y-6">
        <CommandCenterHeader onRunAnalysis={undefined} canRun={false} deepScanRunning={false} onDeepScan={undefined} />
        <Card padding="lg">
          <EmptyState
            icon="&#x1F4C1;"
            title="No repository selected"
            description="Use the Repository selector in the header (or press ⌘K / Ctrl+K) to pick one of your GitHub repositories. Everything on this page reflects the selected repository only."
          />
        </Card>
      </div>
    );
  }

  const report = intel.report;
  const stats = report?.stats;
  const scanning = intel.scanning;
  const branchMismatch = Boolean(report && branch && report.branch !== branch);
  const coveragePartial = Boolean(stats && stats.filtered_files > stats.analyzed_files);

  return (
    <div className="p-4 sm:p-6 max-w-7xl space-y-5 sm:space-y-6 dp-fade-up">
      {/* Top area */}
      <CommandCenterHeader
        canRun={Boolean(owner && name)}
        running={scanning}
        onRunAnalysis={() => void intel.startScan(false, branch || undefined)}
        deepScanRunning={deepScanBusy}
        onDeepScan={runDeepScan}
      />

      {/* Analysis state banner (real status only) */}
      {scanning && intel.job && <StageProgress job={intel.job} />}

      {!scanning && metaError && (
        <Banner tone="error" title="Repository state could not be loaded" message={metaError} />
      )}

      {!scanning && intel.error && (
        <Banner
          tone="error"
          title="Analysis could not be completed."
          message={intel.error}
          action={
            <Button size="sm" variant="secondary" onClick={() => void intel.startScan(true, branch || undefined)}>
              Retry Analysis
            </Button>
          }
        />
      )}

      {!scanning && !intel.error && report && branchMismatch && (
        <Banner
          tone="warn"
          title={`Current analysis is for branch "${report.branch}"`}
          message={
            branch
              ? `You are viewing branch "${branch}". Run an analysis to compute statistics for this branch.`
              : "Select a branch, then run an analysis for it."
          }
          action={
            branch ? (
              <Button size="sm" variant="secondary" onClick={() => void intel.startScan(false, branch)}>
                Analyze &quot;{branch}&quot;
              </Button>
            ) : undefined
          }
        />
      )}

      {!scanning && report && (
        <p className="text-[11px] flex flex-wrap items-center gap-x-2 gap-y-1" style={{ color: "var(--muted-foreground)" }}>
          <Badge variant="success">Analyzed</Badge>
          <span>
            branch {report.branch} · {formatDate(new Date(report.generated_at * 1000).toISOString())}
            {coveragePartial && ` · analyzed ${stats!.analyzed_files.toLocaleString()} of ${stats!.filtered_files.toLocaleString()} code files (large files skipped)`}
          </span>
        </p>
      )}

      {/* Codebase Overview */}
      <section aria-label="Codebase overview">
        <SectionTitle>Codebase Overview</SectionTitle>
        {stats ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <MetricCard
              label="Files"
              state={{ kind: "value", value: fmt(stats.total_files), sub: `${fmt(stats.filtered_files)} source candidates` }}
              source="GitHub file tree of the selected repository."
            />
            <MetricCard
              label="Lines of Code"
              state={{
                kind: "value",
                value: fmt(stats.lines_of_code),
                sub: coveragePartial ? "partial coverage — large files skipped" : `${fmt(stats.analyzed_files)} files analyzed`,
              }}
              source="Counted by the analyzer while reading each file's content."
            />
            <MetricCard
              label="Languages"
              state={{ kind: "value", value: String(stats.language_count), sub: topLanguages(stats.languages, 2) }}
              source="Detected per file by extension during analysis."
            />
            <MetricCard
              label="Functions"
              state={{ kind: "value", value: fmt(stats.functions), sub: `${fmt(stats.methods)} methods` }}
              source="AST parser (tree-sitter / Python parser)."
            />
            <MetricCard
              label="Classes"
              state={{ kind: "value", value: fmt(stats.classes), sub: "" }}
              source="AST parser (tree-sitter / Python parser)."
            />
            <MetricCard
              label="Dependencies"
              state={{
                kind: "value",
                value: fmt(stats.external_dependencies),
                sub: stats.has_lockfile ? "lockfile present" : "no lockfile detected",
              }}
              source="Package manifests + import analysis."
            />
            <MetricCard
              label="Test Files"
              state={{ kind: "value", value: fmt(stats.test_files), sub: `${fmt(stats.source_files)} non-test` }}
              source="File-path patterns (tests/, *.test.*, _test.py ...)."
            />
            <MetricCard
              label="Contributors"
              state={
                stats.contributors == null
                  ? { kind: "unavailable", reason: "Not available" }
                  : { kind: "value", value: fmt(stats.contributors), sub: "via GitHub API" }
              }
              source="GitHub contributors endpoint."
            />
            <MetricCard
              label="Commits"
              state={
                stats.commits == null
                  ? { kind: "unavailable", reason: "Not available" }
                  : { kind: "value", value: fmt(stats.commits), sub: "default branch" }
              }
              source="GitHub commits endpoint (pagination count)."
            />
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {scanning
              ? Array.from({ length: 5 }).map((_, i) => <MetricCard key={i} label={["Files", "Lines of Code", "Languages", "Functions", "Classes"][i]} state={{ kind: "loading" }} />)
              : Array.from({ length: 5 }).map((_, i) => (
                  <MetricCard key={i} label={["Files", "Lines of Code", "Languages", "Functions", "Classes"][i]} state={{ kind: "unavailable", reason: "Run analysis" }} />
                ))}
          </div>
        )}
      </section>

      {/* Health strip */}
      {report && (
        <section aria-label="Code health">
          <SectionTitle>Code Health</SectionTitle>
          <Card padding="sm">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-2xl font-bold leading-none" style={{ color: scoreColor(report.health.overall) }}>
                  {report.health.overall}
                </span>
                <span className="text-[10px] leading-tight" style={{ color: "var(--muted-foreground)" }}>
                  health<br />/ 100
                </span>
              </div>
              <div className="flex-1 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-x-4 gap-y-2 min-w-0">
                {Object.entries(report.health.categories).map(([cat, v]) => (
                  <div key={cat} title={`${cat}: ${v}/100`}>
                    <div className="flex justify-between text-[10px] mb-1">
                      <span className="truncate" style={{ color: "var(--muted-foreground)" }}>{cat}</span>
                      <span className="font-medium" style={{ color: scoreColor(v) }}>{v}</span>
                    </div>
                    <div className="h-1 rounded-full overflow-hidden" style={{ background: "var(--muted)" }}>
                      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${v}%`, background: scoreColor(v) }} />
                    </div>
                  </div>
                ))}
              </div>
              <Link href="/intelligence" className="text-xs underline shrink-0 whitespace-nowrap" style={{ color: "var(--muted-foreground)" }}>
                Full report →
              </Link>
            </div>
          </Card>
        </section>
      )}

      {/* Architecture overview */}
      <section aria-label="Architecture overview">
        <SectionTitle>Architecture Overview</SectionTitle>
        <Card padding="md">
          {riskLoading ? (
            <div className="py-8 text-center text-sm" style={{ color: "var(--muted-foreground)" }}>Loading architecture data...</div>
          ) : riskMap?.has_graph ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2 text-xs" style={{ color: "var(--muted-foreground)" }}>
                <Badge variant="default">{riskMap.summary.nodes} nodes</Badge>
                <Badge variant="default">{riskMap.summary.relationships} relationships</Badge>
                {riskMap.summary.high_risk > 0 && <Badge variant="error">{riskMap.summary.high_risk} high-risk hotspots</Badge>}
                {riskMap.summary.circular_dependency_groups > 0 && (
                  <Badge variant="warning">{riskMap.summary.circular_dependency_groups} circular dep. groups</Badge>
                )}
                {riskMap.summary.high_risk === 0 && riskMap.summary.circular_dependency_groups === 0 && (
                  <Badge variant="success">No high-risk hotspots or cycles detected</Badge>
                )}
                <Link href="/architecture" className="ml-auto text-xs underline shrink-0" style={{ color: "var(--muted-foreground)" }}>
                  Full Architecture →
                </Link>
              </div>

              {riskMap.hotspots.length > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: "var(--muted-foreground)" }}>
                    Top hotspots (degree · fan-in · size)
                  </p>
                  <ul className="divide-y" style={{ borderColor: "var(--border)" }}>
                    {riskMap.hotspots.slice(0, 5).map((h) => (
                      <li key={h.node_id} className="flex items-center gap-2 py-1.5 min-w-0">
                        <span
                          className="h-2 w-2 rounded-full shrink-0"
                          title={`${h.risk} risk · score ${h.score}`}
                          style={{ background: h.risk === "high" ? "#dc2626" : h.risk === "medium" ? "#d97706" : "#059669" }}
                        />
                        <span className="text-xs font-medium truncate">{h.name || h.file_path}</span>
                        <span className="text-[10px] truncate hidden sm:block" style={{ color: "var(--muted-foreground)" }}>{h.file_path}</span>
                        <span className="ml-auto text-[10px] shrink-0 font-mono" style={{ color: "var(--muted-foreground)" }}>
                          ↓{h.metrics.fan_in} ↑{h.metrics.fan_out}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {riskMap.cycles.length > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: "var(--muted-foreground)" }}>Circular dependencies</p>
                  <ul className="space-y-1">
                    {riskMap.cycles.slice(0, 3).map((c, i) => (
                      <li key={i} className="text-[11px] font-mono truncate" style={{ color: "var(--muted-foreground)" }} title={c.files.join(" ↔ ")}>
                        {c.files.slice(0, 4).join(" ↔ ")}
                        {c.files.length > 4 ? ` +${c.files.length - 4} more` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <EmptyState
              icon="&#x1F9E9;"
              title="No architecture graph yet"
              description="The dependency graph is built from parsed code entities. Run an analysis first, then build the graph here or from the Architecture page."
              action={
                <Button size="sm" onClick={buildGraph} disabled={graphBusy || !report}>
                  {graphBusy ? "Building..." : "Build Graph"}
                </Button>
              }
            />
          )}
        </Card>
      </section>

      {/* Deep scan progress */}
      {deepScanBusy && deepScanJob && (
        <div className="border rounded-lg px-4 py-3" style={{ borderColor: "#10b981", background: "rgba(16,185,129,0.05)" }}>
          <div className="flex items-center gap-3">
            <div className="animate-spin h-4 w-4 border-2 border-t-transparent rounded-full" style={{ borderColor: "#10b981", borderTopColor: "transparent" }} />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium">{deepScanJob.message}</p>
              <div className="h-1.5 rounded-full mt-1.5 overflow-hidden" style={{ background: "var(--border)" }}>
                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${deepScanJob.progress * 100}%`, background: "#10b981" }} />
              </div>
            </div>
            <span className="text-[10px] shrink-0" style={{ color: "var(--muted-foreground)" }}>{Math.round(deepScanJob.progress * 100)}%</span>
          </div>
        </div>
      )}

      {/* Health Overview Cards from deep scan */}
      {deepScanReport && <HealthOverviewCards report={deepScanReport} />}

      {/* Security posture quick view */}
      {deepScanReport?.posture && (
        <section aria-label="Security posture">
          <SectionTitle>Security Posture</SectionTitle>
          <Card padding="sm">
            <div className="flex items-center gap-4">
              <SecurityScoreRing score={deepScanReport.posture.score} size={80} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 text-xs" style={{ color: "var(--muted-foreground)" }}>
                  <span>{deepScanReport.posture.executed_checks} checks executed</span>
                  <span>·</span>
                  <span style={{ color: "#059669" }}>{deepScanReport.posture.passed_checks} passed</span>
                  <span>·</span>
                  <span style={{ color: "#dc2626" }}>{deepScanReport.posture.open_findings} open findings</span>
                </div>
                <p className="text-[10px] mt-1" style={{ color: "var(--muted-foreground)" }}>
                  Evidence-based score. {deepScanReport.counts.secrets > 0 && `${deepScanReport.counts.secrets} secret(s) detected. `}
                  {deepScanReport.dependencies.vulnerabilities.length > 0 && `${deepScanReport.dependencies.vulnerabilities.length} dependency vulnerability/vulnerabilities.`}
                </p>
                <Link href="/security" className="text-xs underline mt-1 inline-block" style={{ color: "var(--muted-foreground)" }}>
                  Full security report →
                </Link>
              </div>
            </div>
          </Card>
        </section>
      )}

      {/* Deep scan button */}
      {report && !deepScanReport && !deepScanBusy && (
        <section>
          <Card padding="md">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold">Run Security Deep Scan</p>
                <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>
                  Analyze security rules, detect secrets, measure code health, and detect performance patterns.
                </p>
              </div>
              <Button size="sm" onClick={runDeepScan} disabled={deepScanBusy}>
                Start Deep Scan
              </Button>
            </div>
          </Card>
        </section>
      )}

      {/* Insights Panel */}
      {owner && name && <InsightsPanel owner={owner} repo={name} />}

      {/* Ask DevPilot */}
      {owner && name && <AskDevPilotPanel owner={owner} repo={name} />}

      {/* Recent activity — foundation */}
      <section aria-label="Recent activity">
        <SectionTitle>Recent Activity</SectionTitle>
        <Card padding="sm">
          {metaLoading ? (
            <div className="py-6 text-center text-xs" style={{ color: "var(--muted-foreground)" }}>Loading activity…</div>
          ) : (
            <ActivityFeed
              events={buildEvents({
                reportGeneratedAt: report?.generated_at,
                jobs: repoMeta?.analysis_jobs ?? [],
                deepScanGeneratedAt: deepScanReport?.generated_at,
                pipelineTotal: pipelines?.total ?? 0,
                pipelineCapabilities: pipelines?.overall_capabilities,
                hasSecurityFindings: (deepScanReport?.counts.total_findings ?? 0) > 0,
                hasSecrets: (deepScanReport?.counts.secrets ?? 0) > 0,
                hasVulnerabilities: (deepScanReport?.dependencies.vulnerabilities.length ?? 0) > 0,
              })}
            />
          )}
        </Card>
      </section>
    </div>
  );
}

/* ── Header ── */

function CommandCenterHeader({
  canRun,
  running,
  onRunAnalysis,
  deepScanRunning,
  onDeepScan,
}: {
  canRun: boolean;
  running?: boolean;
  onRunAnalysis?: () => void;
  deepScanRunning?: boolean;
  onDeepScan?: () => void;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight">Command Center</h1>
        <p className="text-sm mt-0.5" style={{ color: "var(--muted-foreground)" }}>
          Here&apos;s what is happening in your codebase.
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Link
          href="/code-explorer"
          className="inline-flex items-center justify-center gap-1.5 h-9 px-3.5 text-xs font-medium rounded-lg border transition-colors hover:brightness-95"
          style={{ borderColor: "var(--btn-secondary-border)", background: "var(--btn-secondary-bg)", color: "var(--btn-secondary-text)" }}
        >
          Explore Repository
        </Link>
        {canRun && onDeepScan && (
          <Button variant="secondary" size="sm" onClick={onDeepScan} disabled={deepScanRunning || !canRun} className="h-9">
            {deepScanRunning ? "Scanning…" : "Deep Scan"}
          </Button>
        )}
        {canRun && onRunAnalysis && (
          <Button onClick={onRunAnalysis} disabled={running} className="h-9">
            {running ? "Analyzing…" : "Run Analysis"}
          </Button>
        )}
      </div>
    </div>
  );
}

/* ── Metric card ── */

function MetricCard({ label, state, source }: { label: string; state: MetricState; source?: string }) {
  return (
    <Card padding="sm" className="min-w-0">
      <p className="text-[10px] font-medium uppercase tracking-wider truncate" title={source} style={{ color: "var(--muted-foreground)" }}>
        {label}
      </p>
      {state.kind === "loading" && (
        <div className="h-6 w-14 mt-1.5 rounded animate-pulse" style={{ background: "var(--muted)" }} aria-label={`${label} loading`} />
      )}
      {state.kind === "value" && (
        <>
          <p className="text-lg sm:text-xl font-bold mt-1 truncate" title={`${label}: ${state.value}`}>
            {state.value}
          </p>
          {state.sub ? (
            <p className="text-[10px] truncate mt-0.5" style={{ color: "var(--muted-foreground)" }}>{state.sub}</p>
          ) : null}
        </>
      )}
      {state.kind === "unavailable" && (
        <p className="text-sm mt-2 italic" title={source} style={{ color: "var(--muted-foreground)" }}>
          {state.reason}
        </p>
      )}
    </Card>
  );
}

/* ── Banner ── */

function Banner({
  tone,
  title,
  message,
  action,
}: {
  tone: "warn" | "error";
  title: string;
  message: string;
  action?: React.ReactNode;
}) {
  const color = tone === "error" ? "#dc2626" : "#d97706";
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className="rounded-lg border px-3.5 py-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3"
      style={{ borderColor: color, background: `color-mix(in srgb, ${color} 8%, transparent)` }}
    >
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold" style={{ color }}>{title}</p>
        <p className="text-xs mt-0.5 break-words" style={{ color: "var(--muted-foreground)" }}>{message}</p>
      </div>
      {action}
    </div>
  );
}

/* ── Recent activity feed (real events only) ── */

interface ActivityEvent {
  id: string;
  icon: string;
  tone: string;
  title: string;
  detail: string;
  time?: string;
}

function buildEvents(input: {
  reportGeneratedAt?: number;
  jobs: { id: string; branch: string; status: string; message: string }[];
  deepScanGeneratedAt?: number;
  pipelineTotal?: number;
  pipelineCapabilities?: Record<string, boolean>;
  hasSecurityFindings?: boolean;
  hasSecrets?: boolean;
  hasVulnerabilities?: boolean;
}): ActivityEvent[] {
  const events: ActivityEvent[] = [];
  if (input.deepScanGeneratedAt) {
    events.push({
      id: `deep-${input.deepScanGeneratedAt}`,
      icon: "\uD83D\uDEE1\uFE0F",
      tone: "#10b981",
      title: "Security deep scan completed",
      detail: "Security posture, code health scores and findings updated.",
      time: new Date(input.deepScanGeneratedAt * 1000).toLocaleString(),
    });
  }
  if (input.reportGeneratedAt) {
    events.push({
      id: `intel-${input.reportGeneratedAt}`,
      icon: "🧠",
      tone: "#10b981",
      title: "Code Intelligence scan completed",
      detail: "Statistics, findings and health scores updated.",
      time: new Date(input.reportGeneratedAt * 1000).toLocaleString(),
    });
  }
  if (input.pipelineTotal && input.pipelineTotal > 0) {
    const caps = input.pipelineCapabilities || {};
    const activeCaps = Object.entries(caps).filter(([, v]) => v).map(([k]) => k);
    events.push({
      id: "pipelines-detected",
      icon: "⚙️",
      tone: "#3b82f6",
      title: `${input.pipelineTotal} CI/CD pipeline(s) detected`,
      detail: activeCaps.length > 0 ? `Capabilities: ${activeCaps.join(", ")}` : "Configuration files detected in repository.",
    });
  }
  if (input.hasSecurityFindings) {
    events.push({
      id: "security-findings",
      icon: "🔒",
      tone: "#dc2626",
      title: "Security findings detected",
      detail: "Static analysis found potential security issues. Review in the Security section.",
    });
  }
  if (input.hasSecrets) {
    events.push({
      id: "secrets-detected",
      icon: "🔑",
      tone: "#dc2626",
      title: "Secrets detected in source code",
      detail: "Potential secrets found. Previews are masked for safety.",
    });
  }
  if (input.hasVulnerabilities) {
    events.push({
      id: "vulnerabilities-detected",
      icon: "⚠️",
      tone: "#ea580c",
      title: "Dependency vulnerabilities detected",
      detail: "Known vulnerabilities found in dependencies via OSV.dev.",
    });
  }
  for (const job of input.jobs.slice(0, 5)) {
    if (job.status === "completed") {
      events.push({
        id: `job-${job.id}`,
        icon: "⚙️",
        tone: "#059669",
        title: `Repository analysis (${job.branch})`,
        detail: job.message,
      });
    } else if (job.status === "failed") {
      events.push({
        id: `job-${job.id}`,
        icon: "⚠️",
        tone: "#dc2626",
        title: `Analysis failed (${job.branch})`,
        detail: job.message,
      });
    } else {
      events.push({
        id: `job-${job.id}`,
        icon: "⏳",
        tone: "#d97706",
        title: `Analysis ${job.status} (${job.branch})`,
        detail: job.message,
      });
    }
  }
  return events;
}

function ActivityFeed({ events }: { events: ActivityEvent[] }) {
  if (events.length === 0) {
    return (
      <p className="py-4 text-center text-xs" style={{ color: "var(--muted-foreground)" }}>
        No recent activity
      </p>
    );
  }
  return (
    <ul className="space-y-2">
      {events.map((e) => (
        <li key={e.id} className="flex items-start gap-2.5 py-1">
          <span
            className="mt-0.5 h-6 w-6 rounded-md flex items-center justify-center text-[11px] shrink-0"
            style={{ background: `color-mix(in srgb, ${e.tone} 12%, transparent)` }}
          >
            {e.icon}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium truncate">{e.title}</p>
            <p className="text-[11px] break-words" style={{ color: "var(--muted-foreground)" }}>{e.detail}</p>
          </div>
          {e.time && (
            <span className="text-[10px] shrink-0 hidden sm:block" style={{ color: "var(--muted-foreground)" }}>
              {e.time}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

/* ── Small helpers ── */

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-sm font-semibold mb-2.5">{children}</h2>;
}

function SkeletonBlock({ className }: { className?: string }) {
  return <div className={`rounded-xl animate-pulse ${className ?? ""}`} style={{ background: "var(--muted)" }} />;
}

function fmt(n: number): string {
  return n.toLocaleString();
}

function topLanguages(languages: Record<string, { files: number; lines: number }>, n: number): string {
  const entries = Object.entries(languages).sort((a, b) => b[1].lines - a[1].lines);
  if (entries.length === 0) return "";
  return entries.slice(0, n).map(([lang]) => lang).join(", ");
}
