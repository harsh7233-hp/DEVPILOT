"use client";

import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Edge,
  MarkerType,
  MiniMap,
  Node as FlowNode,
  NodeProps,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { RepoSelector } from "@/components/ui/RepoSelector";
import { api } from "@/lib/api";
import type {
  IntelligenceFinding,
  IntelligenceReport,
  Recommendation,
  RiskHotspot,
} from "@/lib/api";
import type {
  GraphNode,
  GraphNodeDetail,
  GraphRelationship,
} from "@/lib/graph-types";
import { SEVERITY_STYLE, ScoreRing, scoreColor, useIntelligence } from "./shared";
import { NODE_COLORS, CodeNode, toNodeId } from "../architecture/ArchitectureView";

const TABS = [
  "Code Health & Reliability",
  "Performance Analysis",
  "Recommended Changes",
  "Architecture Risk Map",
] as const;
type Tab = (typeof TABS)[number];

export function CodeIntelligenceView() {
  const [repoValue, setRepoValue] = useState("");
  const [owner = "", repo = ""] = repoValue.split("/");
  const [tab, setTab] = useState<Tab>(TABS[0]);
  const { report, loading, scanning, job, error, startScan } = useIntelligence(owner, repo);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 pb-3 border-b shrink-0" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="min-w-0">
            <h1 className="text-lg sm:text-xl font-bold tracking-tight truncate">Code Intelligence</h1>
            <p className="text-xs mt-0.5 hidden sm:block" style={{ color: "var(--muted-foreground)" }}>
              Health, performance and architecture insights from static analysis + AI
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <RepoSelector value={repoValue} onChange={(o, r) => setRepoValue(`${o}/${r}`)} className="flex-1 min-w-0 sm:max-w-56" />
          <Button size="sm" onClick={() => startScan(true)} disabled={!owner || scanning} className="shrink-0 whitespace-nowrap">
            {scanning ? "Scanning..." : report ? "Run New Analysis" : "Analyze Repository"}
          </Button>
        </div>
      </div>

      {scanning && job && <StageProgress job={job} />}
      {error && <ErrorState message={error} onRetry={() => startScan(true)} />}

      {!owner || !repo ? (
        <div className="flex-1 flex items-center justify-center p-4">
          <EmptyState icon="🧠" title="Select a repository" description="Choose a repository to run Code Intelligence." />
        </div>
      ) : loading ? (
        <LoadingState message="Loading intelligence report..." />
      ) : !report ? (
        <div className="flex-1 flex items-center justify-center p-4">
          <EmptyState
            icon="🔬"
            title="No analysis yet"
            description="Run a Code Intelligence scan to compute health scores, find issues and map architectural risk."
            action={<Button onClick={() => startScan(false)}>{scanning ? "Scanning..." : "Analyze Repository"}</Button>}
          />
        </div>
      ) : (
        <>
          <div className="px-4 pt-3 border-b shrink-0 overflow-x-auto" style={{ borderColor: "var(--border)" }}>
            <div className="flex gap-1 min-w-max">
              {TABS.map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-3 py-2 text-xs font-medium rounded-t-lg transition-colors border-b-2 ${
                    tab === t ? "border-emerald-500" : "border-transparent"
                  }`}
                  style={tab === t ? { color: "var(--foreground)" } : { color: "var(--muted-foreground)" }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto overscroll-contain p-4">
            {tab === "Code Health & Reliability" && <HealthTab report={report} />}
            {tab === "Performance Analysis" && <PerformanceTab findings={report.performance_issues} />}
            {tab === "Recommended Changes" && (
              <RecommendationsTab recommendations={report.recommendations} language={primaryLanguage(report)} />
            )}
            {tab === "Architecture Risk Map" && <RiskMapTab owner={owner} repo={repo} />}
          </div>
        </>
      )}
    </div>
  );
}

function primaryLanguage(report: IntelligenceReport): string {
  const langs = Object.entries(report.stats.languages);
  if (langs.length === 0) return "TypeScript";
  langs.sort((a, b) => b[1].lines - a[1].lines);
  return langs[0][0];
}

/* ── Scan stage progress ── */

export function StageProgress({
  job,
}: {
  job: { stages: string[]; stage: number; status: string; message: string; progress: number };
}) {
  const stages = job.stages.length
    ? job.stages
    : [
        "Scanning Repository",
        "Analyzing Files",
        "Detecting Functions & Classes",
        "Analyzing Dependencies",
        "Checking Pipelines",
        "Checking Performance",
        "Calculating Code Health",
        "Generating Recommendations",
      ];
  return (
    <Card padding="sm" className="mx-4 mt-3 shrink-0">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold">{job.message}</p>
        <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
          {Math.round(job.progress * 100)}%
        </span>
      </div>
      <div className="h-1.5 rounded-full mb-3 overflow-hidden" style={{ background: "var(--muted)" }}>
        <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${job.progress * 100}%` }} />
      </div>
      <ol className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-1 list-none m-0 p-0">
        {stages.map((s, i) => (
          <li key={s} className="flex items-center gap-1.5 text-[11px] min-w-0">
            <span
              className="w-3.5 h-3.5 rounded-full flex items-center justify-center shrink-0"
              style={{
                background: i < job.stage ? "#059669" : i === job.stage ? "rgba(16,185,129,0.25)" : "var(--muted)",
                color: i <= job.stage ? "#fff" : "var(--muted-foreground)",
                fontSize: 8,
              }}
            >
              {i < job.stage ? "✓" : i + 1}
            </span>
            <span className="truncate" style={{ color: i <= job.stage ? "var(--foreground)" : "var(--muted-foreground)" }}>
              {s}
            </span>
          </li>
        ))}
      </ol>
    </Card>
  );
}

/* ── Tab 1: Health ── */

function HealthTab({ report }: { report: IntelligenceReport }) {
  const { health } = report;
  const counts = health.counts;

  return (
    <div className="space-y-5 max-w-5xl">
      <Card padding="md">
        <div className="flex flex-col sm:flex-row items-center gap-6">
          <ScoreRing score={health.overall} />
          <div className="min-w-0 flex-1 w-full">
            <p className="text-sm font-semibold">Repository Code Health</p>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>{health.methodology}</p>
            <div className="flex flex-wrap gap-2 mt-3">
              <SeverityChip label="Critical" value={counts.critical} />
              <SeverityChip label="High" value={counts.high} />
              <SeverityChip label="Medium" value={counts.medium} />
              <SeverityChip label="Low" value={counts.low} />
              <SeverityChip label="Security" value={counts.security_findings} />
              <SeverityChip label="Perf" value={counts.performance_findings} />
            </div>
          </div>
          <CategoryBars categories={health.categories} />
        </div>
      </Card>

      <IssuesList issues={report.issues} emptyTitle="No health issues found" />
    </div>
  );
}

function SeverityChip({ label, value }: { label: string; value: number }) {
  const style = SEVERITY_STYLE[label.toUpperCase()] || SEVERITY_STYLE.LOW;
  if (!style) return null;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium" style={{ background: style.bg, color: style.color }}>
      {label}: {value}
    </span>
  );
}

function CategoryBars({ categories }: { categories: Record<string, number> }) {
  return (
    <div className="w-full sm:w-64 shrink-0 space-y-1.5">
      {Object.entries(categories).map(([name, v]) => (
        <div key={name}>
          <div className="flex justify-between text-[10px] mb-0.5">
            <span style={{ color: "var(--muted-foreground)" }}>{name}</span>
            <span className="font-medium" style={{ color: scoreColor(v) }}>{v}</span>
          </div>
          <div className="h-1.5 rounded-full" style={{ background: "var(--muted)" }}>
            <div className="h-full rounded-full transition-all duration-700" style={{ width: `${v}%`, background: scoreColor(v) }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Issues list ── */

export function IssuesList({ issues, emptyTitle }: { issues: IntelligenceFinding[]; emptyTitle: string }) {
  const [openId, setOpenId] = useState<string | null>(null);

  if (issues.length === 0) {
    return <EmptyState icon="✅" title={emptyTitle} description="Static analysis found no matching patterns in this scan." />;
  }

  return (
    <div className="space-y-2">
      {issues.map((iss) => {
        const style = SEVERITY_STYLE[iss.severity] || SEVERITY_STYLE.LOW;
        const open = openId === iss.id;
        return (
          <Card key={iss.id} padding="sm">
            <button onClick={() => setOpenId(open ? null : iss.id)} className="w-full text-left">
              <div className="flex items-start gap-2.5">
                <span className="text-[9px] font-bold px-1.5 py-1 rounded shrink-0 mt-0.5" style={{ background: style.bg, color: style.color }}>
                  {iss.severity}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs sm:text-sm font-semibold leading-snug">{iss.problem}</p>
                  <p className="text-[11px] truncate mt-0.5 font-mono" style={{ color: "var(--muted-foreground)" }}>
                    {iss.file}
                    {iss.line ? `:${iss.line}` : ""}
                    {iss.symbol ? ` · ${iss.symbol}` : ""}
                  </p>
                </div>
                <span className="shrink-0 text-[10px]" style={{ color: "var(--muted-foreground)" }}>{open ? "▲" : "▼"}</span>
              </div>
            </button>
            {open && (
              <div className="mt-3 pt-3 space-y-3 border-t" style={{ borderColor: "var(--border)" }}>
                {iss.evidence && (
                  <div>
                    <p className="text-[10px] uppercase tracking-wider font-semibold mb-1" style={{ color: "var(--muted-foreground)" }}>Evidence</p>
                    <pre className="text-[11px] font-mono p-2.5 rounded-lg overflow-x-auto whitespace-pre" style={{ background: "var(--muted)", color: "var(--foreground)" }}>
                      {iss.evidence}
                    </pre>
                  </div>
                )}
                <FindingField label="Explanation" text={iss.explanation} />
                <FindingField label="Recommended solution" text={iss.recommendation} accent />
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

function FindingField({ label, text, accent }: { label: string; text: string; accent?: boolean }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider font-semibold mb-1" style={{ color: "var(--muted-foreground)" }}>{label}</p>
      <p className="text-xs leading-relaxed" style={{ color: accent ? "#059669" : "var(--foreground)" }}>{text}</p>
    </div>
  );
}

/* ── Tab 2: Performance ── */

function PerformanceTab({ findings }: { findings: IntelligenceFinding[] }) {
  return (
    <div className="space-y-4 max-w-5xl">
      <div
        className="rounded-xl border px-4 py-3 text-xs leading-relaxed"
        style={{
          background: "color-mix(in srgb, #f59e0b 8%, var(--card))",
          borderColor: "color-mix(in srgb, #f59e0b 35%, var(--border))",
          color: "var(--foreground)",
        }}
      >
        <strong>Potential Performance Issues</strong> — detected via static code-pattern analysis only.
        No runtime profiling or benchmarking has been performed; items are candidates worth measuring, not proven bottlenecks.
      </div>
      <IssuesList issues={findings} emptyTitle="No potential performance issues detected" />
    </div>
  );
}

/* ── Tab 3: Recommended Changes ── */

function RecommendationsTab({ recommendations, language }: { recommendations: Recommendation[]; language: string }) {
  const [active, setActive] = useState<Recommendation | null>(null);

  if (recommendations.length === 0) {
    return <EmptyState icon="🎉" title="No recommendations" description="Static analysis found nothing that needs attention right now." />;
  }

  return (
    <div className="space-y-2 max-w-5xl">
      {recommendations.map((rec) => {
        const priorityStyle =
          rec.priority === "P1" ? SEVERITY_STYLE.CRITICAL : rec.priority === "P2" ? SEVERITY_STYLE.MEDIUM : SEVERITY_STYLE.LOW;
        return (
          <Card key={rec.id} padding="sm">
            <div className="flex items-start gap-2.5">
              <span className="text-[9px] font-bold px-1.5 py-1 rounded shrink-0 mt-0.5" style={{ background: priorityStyle.bg, color: priorityStyle.color }}>
                {rec.priority}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs sm:text-sm font-semibold leading-snug">{rec.current_problem}</p>
                <p className="text-[11px] truncate mt-0.5 font-mono" style={{ color: "var(--muted-foreground)" }}>
                  {rec.file} · {rec.symbol}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  <Button size="sm" variant="secondary" onClick={() => setActive(rec)}>
                    View Suggested Change
                  </Button>
                  <Badge variant={rec.category === "security" ? "error" : rec.priority === "P1" ? "warning" : "default"}>
                    {rec.source}
                  </Badge>
                </div>
              </div>
            </div>

            <div className="mt-3 pt-3 space-y-2 border-t" style={{ borderColor: "var(--border)" }}>
              <FindingField label="Why it matters" text={rec.why_it_matters} />
              <FindingField label="Recommended solution" text={rec.recommended_solution} accent />
              <FindingField label="Expected benefit" text={rec.expected_benefit} />
            </div>
          </Card>
        );
      })}
      {active && <DiffModal rec={active} language={language} onClose={() => setActive(null)} />}
    </div>
  );
}

function DiffModal({ rec, language, onClose }: { rec: Recommendation; language: string; onClose: () => void }) {
  const [state, setState] = useState<{ status: "loading" | "done" | "error"; diff?: string; model?: string; message?: string }>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    api.intelligence
      .suggestedChange({
        file: rec.file,
        symbol: rec.symbol,
        problem: rec.current_problem,
        explanation: rec.why_it_matters,
        recommendation: rec.recommended_solution,
        language,
      })
      .then((res) => !cancelled && setState({ status: "done", diff: res.diff, model: res.model }))
      .catch((err) => !cancelled && setState({ status: "error", message: err instanceof Error ? err.message : "AI request failed" }));
    return () => {
      cancelled = true;
    };
  }, [rec, language]);

  return (
    <div className="fixed inset-0 z-[60] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-[2px] p-0 sm:p-6" onClick={onClose}>
      <div
        className="bg-[var(--card)] border w-full sm:max-w-3xl max-h-[85dvh] sm:max-h-[80dvh] rounded-t-xl sm:rounded-xl flex flex-col"
        style={{ borderColor: "var(--border)", color: "var(--foreground)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b shrink-0" style={{ borderColor: "var(--border)" }}>
          <div className="min-w-0">
            <p className="text-sm font-semibold truncate">Suggested Change — {rec.symbol || rec.file}</p>
            <p className="text-[11px] truncate font-mono" style={{ color: "var(--muted-foreground)" }}>{rec.file}</p>
          </div>
          <button onClick={onClose} aria-label="Close" className="h-9 w-9 flex items-center justify-center rounded-lg shrink-0" style={{ color: "var(--muted-foreground)" }}>✕</button>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {state.status === "loading" && <LoadingState message="Generating suggested change with AI..." />}
          {state.status === "error" && <ErrorState message={state.message || "Failed"} />}
          {state.status === "done" && (
            <pre className="text-[11px] sm:text-xs font-mono whitespace-pre overflow-x-auto p-3 rounded-lg leading-relaxed" style={{ background: "var(--muted)", color: "var(--foreground)" }}>
              {state.diff}
            </pre>
          )}
        </div>

        <div className="p-3 border-t text-[11px] shrink-0" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>
          ⚠︎ AI-generated suggestion{state.status === "done" && state.model ? ` (${state.model})` : ""} based on static-analysis findings.
          Review before applying manually — DevPilot never modifies your repository automatically.
        </div>
      </div>
    </div>
  );
}

/* ── Tab 4: Architecture Risk Map ── */

function RiskMapTab({ owner, repo }: { owner: string; repo: string }) {
  return (
    <ReactFlowProvider>
      <RiskMapInner owner={owner} repo={repo} />
    </ReactFlowProvider>
  );
}

/** Highlights hotspot nodes with a colored ring around the existing CodeNode visuals */
function RiskNode({ data }: NodeProps) {
  const riskColor = data.risk === "high" ? "#dc2626" : data.risk === "medium" ? "#d97706" : undefined;
  if (!riskColor) return <CodeNode data={data} />;
  return (
    <div style={{ outline: `2px solid ${riskColor}`, outlineOffset: 2, borderRadius: 12 }}>
      <CodeNode data={data} />
    </div>
  );
}

const riskNodeTypes = { codeNode: RiskNode };

function RiskMapInner({ owner, repo }: { owner: string; repo: string }) {
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [rels, setRels] = useState<GraphRelationship[]>([]);
  const [detail, setDetail] = useState<GraphNodeDetail | null>(null);
  const [hotspots, setHotspots] = useState<RiskHotspot[]>([]);
  const [cycles, setCycles] = useState<{ files: string[]; size: number }[]>([]);
  const [methodology, setMethodology] = useState("");
  const [reload, setReload] = useState(0);
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const [errMsg, setErrMsg] = useState("");
  const [showCycles, setShowCycles] = useState(false);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => setState("loading"));
    Promise.all([
      api.graph.getNodes(owner, repo),
      api.graph.getRelationships(owner, repo),
      api.intelligence.riskMap(owner, repo).catch(() => null),
    ])
      .then(([n, r, risk]) => {
        if (cancelled) return;
        setGraphNodes(n.nodes);
        setRels(r.relationships);
        if (risk) {
          setHotspots(risk.hotspots || []);
          setCycles(risk.cycles || []);
          setMethodology(risk.methodology || "");
        }
        setState(n.nodes.length === 0 ? "empty" : "ready");
      })
      .catch((err) => {
        if (!cancelled) {
          setErrMsg(err instanceof Error ? err.message : "Failed to load graph");
          setState("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [owner, repo, reload]);

  const hotspotById = useMemo(() => {
    const m = new Map<string, RiskHotspot>();
    for (const h of hotspots) m.set(h.node_id, h);
    return m;
  }, [hotspots]);

  const layout = useMemo(() => {
    const COLS = 7;
    const SPACING_X = 210;
    const SPACING_Y = 110;
    const flowNodes: FlowNode[] = graphNodes.slice(0, 120).map((n, i) => {
      const row = Math.floor(i / COLS);
      const col = i % COLS;
      const offset = row % 2 === 1 ? SPACING_X / 2 : 0;
      const nid = n.node_id || "";
      const h = hotspotById.get(nid);
      return {
        id: toNodeId(nid),
        type: "codeNode",
        position: { x: col * SPACING_X + offset, y: row * SPACING_Y },
        data: {
          label: n.name || nid,
          sublabel: n.label,
          nodeType: n.label,
          risk: h?.risk,
          isSelected: detail?.node.node_id === nid,
        },
      };
    });

    const nodeIdSet = new Set(flowNodes.map((f) => f.id));
    const flowEdges: Edge[] = rels
      .filter((r) => nodeIdSet.has(toNodeId(r.from_id)) && nodeIdSet.has(toNodeId(r.to_id)))
      .slice(0, 400)
      .map((r, i) => ({
        id: `e${i}`,
        source: toNodeId(r.from_id),
        target: toNodeId(r.to_id),
        style: { stroke: "#94a3b866", strokeWidth: 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b866", width: 14, height: 14 },
      }));

    return { flowNodes, flowEdges };
    // detail intentionally excluded: selection is applied via setFlowNodes below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphNodes, rels, hotspotById]);

  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState([]);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    setFlowNodes(layout.flowNodes);
    setFlowEdges(layout.flowEdges);
  }, [layout, setFlowNodes, setFlowEdges]);

  const handleNodeClick = async (_: unknown, node: FlowNode) => {
    const original = graphNodes.find((n) => toNodeId(n.node_id || "") === node.id);
    if (!original) return;
    try {
      const d = await api.graph.getNode(owner, repo, original.node_id || "");
      setDetail(d);
      setFlowNodes((prev) => prev.map((f) => ({ ...f, data: { ...f.data, isSelected: f.id === node.id } })));
    } catch {
      /* ignore */
    }
  };

  if (state === "loading") return <LoadingState message="Loading architecture graph..." />;
  if (state === "error") return <ErrorState message={errMsg} onRetry={() => setReload((r) => r + 1)} />;
  if (state === "empty")
    return (
      <EmptyState
        icon="🕸️"
        title="No graph built yet"
        description="Build the dependency graph for this repository first (Architecture page → Build Graph), then revisit the Risk Map."
      />
    );

  const highCount = hotspots.filter((h) => h.risk === "high").length;
  const mediumCount = hotspots.filter((h) => h.risk === "medium").length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium" style={{ background: "rgba(220,38,38,0.12)", color: "#dc2626" }}>
          ● High-risk modules: {highCount}
        </span>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium" style={{ background: "rgba(217,119,6,0.14)", color: "#d97706" }}>
          ● Medium-risk: {mediumCount}
        </span>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium" style={{ background: "var(--muted)", color: "var(--foreground)" }}>
          Circular dependency groups: {cycles.length}
        </span>
        <span className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
          Ringed nodes = architectural hotspots (static structural analysis)
        </span>
      </div>

      {methodology && (
        <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>{methodology}</p>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
        <div className="xl:col-span-3 h-[380px] sm:h-[420px] rounded-xl border overflow-hidden relative" style={{ borderColor: "var(--border)" }}>
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            nodeTypes={riskNodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.05}
            maxZoom={2.5}
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#8888aa55" />
            <Controls showInteractive={false} position="bottom-right" />
            <MiniMap
              pannable
              zoomable
              style={{ width: 100, height: 70 }}
              nodeColor={(n) => NODE_COLORS[(n.data as { nodeType?: string }).nodeType as string]?.border || "#666"}
              maskColor="rgba(128,128,128,0.35)"
            />
          </ReactFlow>
        </div>

        <Card padding="sm" className="max-h-[420px] overflow-y-auto">
          <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--muted-foreground)" }}>Top Hotspots</p>
          <div className="space-y-1.5">
            {hotspots.length === 0 && (
              <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>No significant hotspots found.</p>
            )}
            {hotspots.slice(0, 12).map((h) => {
              const c = h.risk === "high" ? "#dc2626" : "#d97706";
              const selected = detail?.node.node_id === h.node_id;
              return (
                <button
                  key={h.node_id}
                  onClick={async () => {
                    try {
                      setDetail(await api.graph.getNode(owner, repo, h.node_id));
                      setFlowNodes((prev) =>
                        prev.map((f) => ({ ...f, data: { ...f.data, isSelected: f.id === toNodeId(h.node_id) } }))
                      );
                    } catch {
                      /* ignore */
                    }
                  }}
                  className="w-full text-left p-2 rounded-lg border transition-colors hover:brightness-95"
                  style={{
                    borderColor: selected ? c : "var(--border)",
                    background: selected ? "color-mix(in srgb, currentColor 5%, var(--muted))" : "transparent",
                  }}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full shrink-0" style={{ background: c }} />
                    <span className="text-xs font-medium truncate flex-1">{h.name}</span>
                    <span className="text-[10px] shrink-0" style={{ color: c }}>{h.score}</span>
                  </div>
                  <p className="text-[10px] truncate mt-0.5 pl-3.5 font-mono" style={{ color: "var(--muted-foreground)" }}>{h.file_path}</p>
                </button>
              );
            })}
          </div>

          {cycles.length > 0 && (
            <div className="pt-2 mt-2 border-t" style={{ borderColor: "var(--border)" }}>
              <button
                onClick={() => setShowCycles(!showCycles)}
                className="text-xs font-medium underline"
                style={{ color: "var(--muted-foreground)" }}
              >
                {showCycles ? "Hide" : "Show"} circular dependencies ({cycles.length})
              </button>
              {showCycles && (
                <ul className="mt-1.5 space-y-1">
                  {cycles.map((c, i) => (
                    <li key={i} className="text-[10px] font-mono p-1.5 rounded break-all" style={{ background: "var(--muted)", color: "var(--foreground)" }}>
                      ⟳ {c.files.join(" ↔ ")}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </Card>
      </div>

      {detail && (
        <Card padding="sm">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold truncate">
              {String(detail.node.name || "")}{" "}
              <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>({String(detail.node.label || "")})</span>
            </p>
            <button onClick={() => setDetail(null)} aria-label="Close details" className="h-8 w-8 rounded-lg" style={{ color: "var(--muted-foreground)" }}>✕</button>
          </div>
          <p className="text-xs font-mono mb-3 break-all" style={{ color: "var(--muted-foreground)" }}>
            {String(detail.node.file_path || "")}
            {detail.node.start_line ? `:${detail.node.start_line}` : ""}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <p className="text-[10px] uppercase tracking-wider font-semibold mb-1" style={{ color: "var(--muted-foreground)" }}>
                Outgoing dependencies ({detail.outgoing.length})
              </p>
              <ul className="space-y-0.5 max-h-36 overflow-y-auto">
                {detail.outgoing.slice(0, 30).map((o, i) => (
                  <li key={i} className="text-xs truncate">
                    ↳ <span className="font-mono">{o.target_name}</span>{" "}
                    <span style={{ color: "var(--muted-foreground)" }}>({o.rel_type.toLowerCase()})</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider font-semibold mb-1" style={{ color: "var(--muted-foreground)" }}>
                Incoming dependents ({detail.incoming.length})
              </p>
              <ul className="space-y-0.5 max-h-36 overflow-y-auto">
                {detail.incoming.slice(0, 30).map((o, i) => (
                  <li key={i} className="text-xs truncate">
                    ↰ <span className="font-mono">{o.source_name}</span>{" "}
                    <span style={{ color: "var(--muted-foreground)" }}>({o.rel_type.toLowerCase()})</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
