"use client";

import { useState, useCallback } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { RepoSelector } from "@/components/ui/RepoSelector";
import { ImpactGraph } from "./ImpactGraph";
import { api, type ImpactResult } from "@/lib/api";
import { riskColor, classNames } from "@/lib/utils";

type ViewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "empty"; target: string }
  | { status: "success"; result: ImpactResult };

export function ImpactAnalysisView() {
  const [targetInput, setTargetInput] = useState("");
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [repoValue, setRepoValue] = useState("");
  const [state, setState] = useState<ViewState>({ status: "idle" });

  const isValidTarget = targetInput.trim().length > 0 && owner.trim().length > 0 && repo.trim().length > 0;

  const handleRepoSelect = useCallback((newOwner: string, newRepo: string) => {
    setOwner(newOwner);
    setRepo(newRepo);
    setRepoValue(`${newOwner}/${newRepo}`);
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!isValidTarget) return;
    setState({ status: "loading" });
    try {
      const result = await api.impact.analyze({ owner: owner.trim(), repo: repo.trim(), node_id: targetInput.trim() });
      if (result.direct_impact.length === 0 && result.indirect_impact.length === 0) {
        setState({ status: "empty", target: targetInput.trim() });
        return;
      }
      setState({ status: "success", result });
    } catch (err) {
      setState({ status: "error", message: err instanceof Error ? err.message : "Unknown error" });
    }
  }, [owner, repo, targetInput, isValidTarget]);

  const handleReset = useCallback(() => {
    setState({ status: "idle" });
    setTargetInput("");
  }, []);

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight">Change Impact</h1>
        <p className="text-sm mt-1" style={{ color: "var(--muted-foreground)" }}>Understand what changes before you ship</p>
      </div>

      <Card>
        <div className="space-y-3">
          <div>
            <label className="text-xs mb-1 block" style={{ color: "var(--muted-foreground)" }}>Repository</label>
            <RepoSelector value={repoValue} onChange={handleRepoSelect} className="w-full" />
          </div>
          <div>
            <label className="text-xs mb-1 block" style={{ color: "var(--muted-foreground)" }}>Target component</label>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                placeholder="e.g. UserService.getUser, src/services/auth.ts"
                value={targetInput}
                onChange={(e) => setTargetInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
                className="flex-1 min-w-0 h-11 sm:h-9 px-3 text-sm rounded-lg focus:outline-none focus:border-zinc-500"
              />
              <Button onClick={handleAnalyze} disabled={!isValidTarget || state.status === "loading"} className="shrink-0 h-11 sm:h-9">
                {state.status === "loading" ? "Analyzing..." : "Analyze Impact"}
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {state.status === "loading" && <LoadingState message="Analyzing impact graph..." />}
      {state.status === "error" && <ErrorState title="Analysis failed" message={state.message} onRetry={handleAnalyze} />}
      {state.status === "empty" && (
        <EmptyState icon="✅" title="No impact found" description={`The target "${state.target}" has no incoming dependencies in the graph.`}
          action={<Button variant="secondary" onClick={handleReset}>Try another target</Button>} />
      )}
      {state.status === "idle" && (
        <EmptyState icon="🔍" title="Analyze change impact"
          description="Select a repository and enter a target component to see which parts of the codebase will be affected." />
      )}
      {state.status === "success" && <Results result={state.result} />}
    </div>
  );
}

function Results({ result }: { result: ImpactResult }) {
  const { risk, metrics, direct_impact, indirect_impact, dependency_paths, target } = result;
  return (
    <div className="space-y-6">
      <div className="grid lg:grid-cols-3 gap-4">
        <Card>
          <p className="text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Target</p>
          <div className="mt-2">
            {target && (
              <>
                <Badge variant="default" className="text-xs mb-1">{target.label}</Badge>
                <p className="text-sm font-mono mt-1" style={{ color: "var(--foreground)" }}>{target.name}</p>
                {target.file_path && <p className="text-xs font-mono mt-0.5" style={{ color: "var(--muted-foreground)" }}>{target.file_path}</p>}
              </>
            )}
          </div>
        </Card>
        <Card>
          <p className="text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Risk</p>
          <div className="mt-2">
            <Badge variant="warning" className={classNames("text-sm px-3 py-1 uppercase", riskColor(risk.level))}>{risk.level}</Badge>
            <p className="text-xs mt-2" style={{ color: "var(--muted-foreground)" }}>Score: {risk.score}</p>
            {risk.reasons.length > 0 && (
              <ul className="mt-2 space-y-0.5">
                {risk.reasons.map((r, i) => <li key={i} className="text-xs" style={{ color: "var(--muted-foreground)" }}>• {r}</li>)}
              </ul>
            )}
          </div>
        </Card>
        <Card>
          <p className="text-xs uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Impact Summary</p>
          <div className="mt-2 grid grid-cols-2 gap-3">
            <Metric label="Files" value={metrics.affected_files} />
            <Metric label="Functions" value={metrics.affected_functions} />
            <Metric label="Classes" value={metrics.affected_classes} />
            <Metric label="APIs" value={metrics.affected_apis} />
            <Metric label="Direct" value={metrics.direct_dependencies} />
            <Metric label="Indirect" value={metrics.indirect_dependencies} />
          </div>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--foreground)" }}>
            Direct Impact <span className="ml-2 text-xs font-normal" style={{ color: "var(--muted-foreground)" }}>{direct_impact.length}</span>
          </h2>
          <div className="space-y-2 max-h-[300px] overflow-y-auto">
            {direct_impact.map((item) => <AffectedRow key={item.node.node_id} item={item} />)}
          </div>
        </Card>
        <Card>
          <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--foreground)" }}>
            Indirect Impact <span className="ml-2 text-xs font-normal" style={{ color: "var(--muted-foreground)" }}>{indirect_impact.length}</span>
          </h2>
          <div className="space-y-2 max-h-[300px] overflow-y-auto">
            {indirect_impact.length === 0 ? (
              <p className="text-xs py-4 text-center" style={{ color: "var(--muted-foreground)" }}>No indirect dependencies</p>
            ) : (
              indirect_impact.map((item) => <AffectedRow key={item.node.node_id} item={item} />)
            )}
          </div>
        </Card>
      </div>

      <Card padding="none" className="overflow-hidden">
        <div className="px-5 py-3 border-b" style={{ borderColor: "var(--border)" }}>
          <h2 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>Dependency Graph</h2>
          <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>{dependency_paths.length} path(s) from target</p>
        </div>
        <ImpactGraph target={target!} directImpact={direct_impact} indirectImpact={indirect_impact} dependencyPaths={dependency_paths} />
      </Card>

      {dependency_paths.length > 0 && (
        <Card>
          <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--foreground)" }}>Dependency Paths</h2>
          <div className="space-y-2 max-h-[200px] overflow-y-auto">
            {dependency_paths.map((path, idx) => (
              <div key={idx} className="flex items-center gap-1 text-xs font-mono flex-wrap" style={{ color: "var(--muted-foreground)" }}>
                {path.map((nodeId, i) => (
                  <span key={i} className="flex items-center gap-1">
                    <span style={{ color: "var(--foreground)" }}>{nodeId.split(":").pop()}</span>
                    {i < path.length - 1 && <span className="text-zinc-400">→</span>}
                  </span>
                ))}
              </div>
            ))}
          </div>
        </Card>
      )}

      {metrics.affected_modules > 0 && (
        <Card>
          <h2 className="text-sm font-semibold mb-3" style={{ color: "var(--foreground)" }}>
            Affected Files <span className="ml-2 text-xs font-normal" style={{ color: "var(--muted-foreground)" }}>{metrics.affected_modules}</span>
          </h2>
          <div className="space-y-1">
            {[...new Set([
              ...direct_impact.map((d) => d.node.file_path).filter(Boolean),
              ...indirect_impact.map((i) => i.node.file_path).filter(Boolean),
            ])].map((fp) => (
              <div key={fp} className="flex items-center gap-2 py-1.5 group">
                <svg className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--muted-foreground)" }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
                <span className="text-xs font-mono" style={{ color: "var(--muted-foreground)" }}>{fp}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>{label}</p>
      <p className="text-lg font-bold" style={{ color: "var(--foreground)" }}>{value}</p>
    </div>
  );
}

function AffectedRow({ item }: { item: import("@/lib/api").AffectedNode }) {
  const { node, depth } = item;
  const isDirect = depth === 1;
  return (
    <div className="flex items-center gap-3 py-2 last:border-0" style={{ borderBottom: "1px solid var(--border)" }}>
      <div className={classNames("h-7 w-7 rounded flex items-center justify-center text-xs font-mono", isDirect ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400")}>
        {node.label ? node.label[0].toUpperCase() : "?"}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>{node.name}</p>
        <p className="text-xs font-mono" style={{ color: "var(--muted-foreground)" }}>{node.file_path || node.label}</p>
      </div>
      <span className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>d{depth}</span>
    </div>
  );
}
