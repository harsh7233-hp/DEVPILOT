"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  MarkerType,
  BackgroundVariant,
  NodeProps,
  Handle,
  Position,
  ReactFlowInstance,
} from "reactflow";
import "reactflow/dist/style.css";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { RepoSelector } from "@/components/ui/RepoSelector";
import { api } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/utils";
import { useTheme } from "@/lib/theme-context";
import type { GraphNode, GraphRelationship, GraphNodeDetail } from "@/lib/graph-types";

export const NODE_COLORS: Record<string, { bg: string; border: string; text: string; icon: string; bgLight: string; textLight: string }> = {
  File: { bg: "#1e3a5f", bgLight: "#dbeafe", border: "#3b82f6", text: "#93c5fd", textLight: "#1e40af", icon: "📄" },
  Class: { bg: "#3b1f4e", bgLight: "#f3e8ff", border: "#a855f7", text: "#c4b5fd", textLight: "#7e22ce", icon: "📦" },
  Function: { bg: "#1a3a2a", bgLight: "#dcfce7", border: "#22c55e", text: "#86efac", textLight: "#166534", icon: "fn" },
  Method: { bg: "#3a2a1a", bgLight: "#fef3c7", border: "#f59e0b", text: "#fcd34d", textLight: "#92400e", icon: "m" },
  ApiRoute: { bg: "#3a1a1a", bgLight: "#fee2e2", border: "#ef4444", text: "#fca5a5", textLight: "#991b1b", icon: "⚡" },
};

const REL_COLORS: Record<string, string> = {
  IMPORTS: "#6b7280",
  CALLS: "#22d3ee",
  EXTENDS: "#a855f7",
  IMPLEMENTS: "#f59e0b",
  USES: "#64748b",
  DEFINES: "#374151",
  CONTAINS: "#1f2937",
  HAS_METHOD: "#4b5563",
  DEPENDS_ON: "#6b7280",
};

const ALL_NODE_TYPES = ["File", "Class", "Function", "Method", "ApiRoute"];

/** Theme-aware chrome colors for the ReactFlow canvas. */
function useGraphChrome() {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  return {
    isDark,
    dotColor: isDark ? "#27272a" : "#d4d4d8",
    edgeLabelFill: isDark ? "#a1a1aa" : "#52525b",
    edgeLabelBg: isDark ? "#18181b" : "#ffffff",
    minimapMask: isDark ? "rgba(0,0,0,0.7)" : "rgba(255,255,255,0.75)",
  };
}

export function toNodeId(nodeId: string): string {
  return nodeId.replace(/[^a-zA-Z0-9_-]/g, "_");
}

function getShortPath(node: GraphNode): string {
  const p = node.file_path || node.path || "";
  const parts = p.split("/");
  return parts.length > 2 ? `.../${parts.slice(-2).join("/")}` : p;
}

export function CodeNode({ data }: { data: Record<string, unknown> }) {
  const colors = NODE_COLORS[data.nodeType as string] || NODE_COLORS.File;
  const isConnected = data.isConnected as boolean;
  const isSelected = data.isSelected as boolean;
  const hasFilters = data.hasFilters as boolean;
  const dimmed = hasFilters && !isConnected && !isSelected;
  const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");

  return (
    <div
      className="rounded-lg px-3 py-2 shadow-lg cursor-pointer transition-all duration-150"
      style={{
        background: isDark ? colors.bg : colors.bgLight,
        border: `1.5px solid ${isSelected ? (isDark ? "#fff" : "#000") : colors.border}`,
        opacity: dimmed ? 0.3 : 1,
        minWidth: 120,
        maxWidth: 220,
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: colors.border, width: 6, height: 6 }} />
      <div className="flex items-center gap-2">
        <span
          className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded"
          style={{ background: colors.border, color: isDark ? "#000" : "#fff" }}
        >
          {colors.icon}
        </span>
        <div className="min-w-0">
          <p className="text-[11px] font-semibold truncate" style={{ color: isDark ? colors.text : colors.textLight }}>
            {data.label as string}
          </p>
          {Boolean(data.sublabel) && (
            <p className="text-[9px] truncate" style={{ color: isDark ? colors.text : colors.textLight, opacity: 0.6 }}>
              {data.sublabel as string}
            </p>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: colors.border, width: 6, height: 6 }} />
    </div>
  );
}

export const nodeTypes = { codeNode: CodeNode };

export function ArchitectureView() {
  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState([]);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState("Loading dependency graph...");
  const [error, setError] = useState<string | null>(null);
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [relsData, setRelsData] = useState<GraphRelationship[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNodeDetail | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set(ALL_NODE_TYPES));
  const [selectedRepo, setSelectedRepo] = useState<{ owner: string; repo: string } | null>(null);
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [repoValue, setRepoValue] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const chrome = useGraphChrome();
  const rfInstance = useRef<ReactFlowInstance | null>(null);
  const mountedRef = useRef(true);

  const filteredNodeIds = useMemo(() => {
    const visible = new Set<string>();
    const hasFilters = activeFilters.size < ALL_NODE_TYPES.length;
    const hasSearch = searchQuery.length > 0;
    if (!hasFilters && !hasSearch) return null;
    for (const n of graphNodes) {
      const nodeType = (n.label as string) || "File";
      if (!activeFilters.has(nodeType)) continue;
      const name = (n.name as string) || (n.path as string) || "";
      if (hasSearch && !name.toLowerCase().includes(searchQuery.toLowerCase())) continue;
      visible.add(toNodeId(n.node_id));
    }
    return visible;
  }, [activeFilters, searchQuery, graphNodes]);

  const nodeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const n of graphNodes) {
      const t = (n.label as string) || "File";
      counts[t] = (counts[t] || 0) + 1;
    }
    return counts;
  }, [graphNodes]);

  const buildFlowGraph = useCallback(
    (nodes: GraphNode[], rels: GraphRelationship[]) => {
      const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");
      const edgeLabelFill = isDark ? "#a1a1aa" : "#52525b";
      const edgeLabelBg = isDark ? "#18181b" : "#ffffff";

      const rfNodes: Node[] = nodes.map((n, i) => ({
        id: toNodeId(n.node_id),
        type: "codeNode",
        position: { x: (i % 5) * 220, y: Math.floor(i / 5) * 100 },
        data: {
          label: (n.name as string) || (n.path as string) || "unknown",
          sublabel: getShortPath(n),
          nodeType: (n.label as string) || "File",
          nodeData: n,
          isConnected: true,
          isSelected: false,
          hasFilters: false,
        },
      }));

      const rfEdges: Edge[] = rels.map((r, i) => ({
        id: `e-${i}-${r.type}`,
        source: toNodeId(r.from_id),
        target: toNodeId(r.to_id),
        label: r.type,
        type: "smoothstep",
        animated: r.type === "CALLS",
        style: { stroke: REL_COLORS[r.type] || "#6b7280", strokeWidth: 1.5 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: REL_COLORS[r.type] || "#6b7280",
          width: 12,
          height: 12,
        },
        labelStyle: { fill: edgeLabelFill, fontSize: 9, fontWeight: 500 },
        labelBgStyle: { fill: edgeLabelBg, fillOpacity: 0.9 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 3,
      }));

      setFlowNodes(rfNodes);
      setFlowEdges(rfEdges);
    },
    [setFlowNodes, setFlowEdges]
  );

  const applyFilters = useCallback(() => {
    setFlowNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          hasFilters: filteredNodeIds !== null,
          isConnected: filteredNodeIds ? filteredNodeIds.has(n.id) : true,
        },
      }))
    );
  }, [filteredNodeIds, setFlowNodes]);

  useEffect(() => {
    applyFilters();
  }, [applyFilters]);

  const fetchGraph = useCallback(
    async (owner: string, repo: string, autoBuild = true) => {
      if (!mountedRef.current) return;
      setLoading(true);
      setError(null);
      setSelectedNode(null);
      try {
        const [nodesRes, relsRes] = await Promise.all([
          api.graph.getNodes(owner, repo),
          api.graph.getRelationships(owner, repo),
        ]);
        if (!mountedRef.current) return;

        const nodes = nodesRes.nodes as unknown as GraphNode[];
        const rels = relsRes.relationships;
        setRelsData(rels);

        if (nodes.length === 0 && autoBuild) {
          try {
            await api.graph.build(owner, repo);
            const [nodesRes2, relsRes2] = await Promise.all([
              api.graph.getNodes(owner, repo),
              api.graph.getRelationships(owner, repo),
            ]);
            if (!mountedRef.current) return;
            const nodes2 = nodesRes2.nodes as unknown as GraphNode[];
            const rels2 = relsRes2.relationships;
            setRelsData(rels2);
            setGraphNodes(nodes2);
            buildFlowGraph(nodes2, rels2);
          } catch (err) {
            setGraphNodes([]);
            setRelsData([]);
            buildFlowGraph([], []);
            const msg = friendlyErrorMessage(err, "Failed to build graph");
            setError(
              /no completed analysis/i.test(msg)
                ? "No completed analysis found for this repository. Click Try again to analyze it and build the graph."
                : msg
            );
          }
          return;
        }

        setGraphNodes(nodes);
        buildFlowGraph(nodes, rels);
      } catch (err) {
        if (!mountedRef.current) return;
        setError(err instanceof Error ? err.message : "Failed to load graph");
      } finally {
        if (mountedRef.current) setLoading(false);
      }
    },
    [buildFlowGraph]
  );

  // Re-style edges/canvas when the theme changes
  useEffect(() => {
    if (graphNodes.length > 0 || relsData.length > 0) {
      buildFlowGraph(graphNodes, relsData);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chrome.isDark]);

  const startAnalysisAndBuild = useCallback(async (owner: string, repo: string) => {
    setLoadingMessage("Preparing repository analysis...");
    let branch = "main";
    try {
      const info = await api.repositories.get(owner, repo);
      branch = info.repository.default_branch || branch;
    } catch {
      // fall back to main
    }

    const { job_id } = await api.analysis.start(owner, repo, branch);
    for (let attempt = 0; attempt < 240; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      if (!mountedRef.current) return;
      const { job } = await api.analysis.getStatus(job_id);
      if (job.status === "completed") {
        setLoadingMessage("Building dependency graph...");
        await api.graph.build(owner, repo);
        return;
      }
      if (job.status === "failed") {
        throw new Error(job.error || job.message || "Analysis failed");
      }
      setLoadingMessage(
        `Analyzing repository... ${Math.round((job.progress || 0) * 100)}%`
      );
    }
    throw new Error("Analysis timed out. Try again from the Repositories page.");
  }, []);

  const buildFromAnalysis = useCallback(
    async (owner: string, repo: string) => {
      setLoading(true);
      setError(null);
      setLoadingMessage("Building dependency graph...");
      try {
        try {
          await api.graph.build(owner, repo);
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Failed to build graph";
          if (!/no completed analysis/i.test(msg)) throw err;
          await startAnalysisAndBuild(owner, repo);
        }
        await fetchGraph(owner, repo, false);
      } catch (err) {
        if (mountedRef.current) {
          const msg = friendlyErrorMessage(err, "Failed to build graph");
          setError(
            /no completed analysis/i.test(msg)
              ? "No completed analysis found for this repository. Click Try again to analyze it and build the graph."
              : msg
          );
          setLoading(false);
        }
      }
    },
    [fetchGraph, startAnalysisAndBuild]
  );

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!mountedRef.current) return;
    (async () => {
      try {
        const dash = await api.dashboard.get();
        const analyzed = dash.repositories?.find(
          (r: { status: string }) => r.status === "analyzed"
        );
        if (analyzed && mountedRef.current) {
          setOwner(analyzed.owner);
          setRepo(analyzed.repo);
          setRepoValue(`${analyzed.owner}/${analyzed.repo}`);
          setSelectedRepo({ owner: analyzed.owner, repo: analyzed.repo });
          void fetchGraph(analyzed.owner, analyzed.repo);
        } else {
          if (mountedRef.current) setLoading(false);
        }
      } catch {
        if (mountedRef.current) setLoading(false);
      }
    })();
  }, []);

  const handleRepoSelect = (newOwner: string, newRepo: string) => {
    setOwner(newOwner);
    setRepo(newRepo);
    setRepoValue(`${newOwner}/${newRepo}`);
    setSelectedRepo({ owner: newOwner, repo: newRepo });
    void fetchGraph(newOwner, newRepo);
  };

  const handleLoadGraph = () => {
    if (!owner || !repo) return;
    setSelectedRepo({ owner, repo });
    void fetchGraph(owner, repo);
  };

  const handleRebuild = () => {
    if (!selectedRepo) return;
    void buildFromAnalysis(selectedRepo.owner, selectedRepo.repo);
  };

  const onNodeClick = useCallback(
    async (_: React.MouseEvent, node: Node) => {
      if (!selectedRepo) return;
      const nd = node.data.nodeData as GraphNode | undefined;
      if (!nd?.node_id) return;
      try {
        const detail = await api.graph.getNode(selectedRepo.owner, selectedRepo.repo, nd.node_id);
        if (mountedRef.current) setSelectedNode(detail);
      } catch {
        // node detail unavailable
      }
    },
    [selectedRepo]
  );

  const onPaneClick = useCallback(() => {
    if (mountedRef.current) setSelectedNode(null);
  }, []);

  const onInit = useCallback((instance: ReactFlowInstance) => {
    rfInstance.current = instance;
  }, []);

  const toggleFilter = (type: string) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="p-4 pb-3 border-b shrink-0" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="min-w-0">
            <h1 className="text-lg sm:text-xl font-bold tracking-tight truncate">Architecture Explorer</h1>
            <p className="text-xs mt-0.5 hidden sm:block" style={{ color: "var(--muted-foreground)" }}>Interactive dependency graph from code analysis</p>
          </div>
          {selectedRepo && (
            <Button variant="secondary" size="sm" onClick={handleRebuild} disabled={loading} className="shrink-0">
              {loading ? "Building..." : "Rebuild Graph"}
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <RepoSelector value={repoValue} onChange={handleRepoSelect} className="flex-1 min-w-0 sm:max-w-48" />
          <Button size="sm" onClick={handleLoadGraph} disabled={loading || !owner || !repo} className="shrink-0">
            Load Graph
          </Button>
          {/* Mobile filters toggle */}
          <button
            onClick={() => setFiltersOpen((v) => !v)}
            aria-label="Toggle filters"
            className={`md:hidden h-8 w-9 shrink-0 flex items-center justify-center rounded-lg border transition-colors ${filtersOpen ? "border-emerald-500 text-emerald-600 dark:text-emerald-400" : ""}`}
            style={!filtersOpen ? { borderColor: "var(--input-border)", color: "var(--muted-foreground)" } : undefined}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex flex-1 min-h-0 relative">
        {/* Mobile filters overlay */}
        {filtersOpen && (
          <>
            <div className="md:hidden fixed inset-0 z-30 bg-black/40" onClick={() => setFiltersOpen(false)} />
            <div className="md:hidden absolute inset-y-0 left-0 z-40 w-60 max-w-[80vw] border-r p-3 space-y-4 overflow-y-auto shadow-xl" style={{ borderColor: "var(--sidebar-border)", background: "var(--sidebar-bg)" }}>
              <FilterPanel
                activeFilters={activeFilters}
                nodeCounts={nodeCounts}
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
                toggleFilter={toggleFilter}
                onDone={() => setFiltersOpen(false)}
              />
            </div>
          </>
        )}

        {/* Desktop filter sidebar */}
        <div className="hidden md:block w-48 shrink-0 border-r p-3 space-y-4 overflow-y-auto" style={{ borderColor: "var(--border)" }}>
          <FilterPanel
            activeFilters={activeFilters}
            nodeCounts={nodeCounts}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            toggleFilter={toggleFilter}
          />
        </div>

        <div className="flex-1 relative min-w-0">
          {!selectedRepo ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <EmptyState
                icon="&#x1F310;"
                title="No graph loaded"
                description="Enter a repository as owner/repo and click Load Graph."
              />
            </div>
          ) : loading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <LoadingState message={loadingMessage} />
            </div>
          ) : error ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <ErrorState message={error} onRetry={handleRebuild} />
            </div>
          ) : flowNodes.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <EmptyState
                icon="&#x1F9E9;"
                title="Empty graph"
                description="No nodes found. Run a code analysis first, then build the graph."
                action={
                  <Button size="sm" onClick={handleRebuild}>
                    Build from Analysis
                  </Button>
                }
              />
            </div>
          ) : (
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              onInit={onInit}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.3 }}
              minZoom={0.1}
              maxZoom={4}
              snapToGrid
              snapGrid={[15, 15]}
              defaultEdgeOptions={{ type: "smoothstep" }}
            >
              <Background variant={BackgroundVariant.Dots} gap={20} size={1} color={chrome.dotColor} />
              <Controls
                className="!rounded-lg"
                showInteractive={false}
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              />
              <MiniMap
                className="!rounded-lg"
                nodeColor={(n) => NODE_COLORS[n.data.nodeType as string]?.border || "#666"}
                maskColor={chrome.minimapMask}
                pannable
                zoomable
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              />
            </ReactFlow>
          )}
        </div>

        {selectedNode && (
          <div
            className="fixed inset-x-0 bottom-0 z-40 max-h-[55dvh] rounded-t-xl border-t p-4 overflow-y-auto md:static md:z-auto md:max-h-none md:w-72 md:shrink-0 md:rounded-none md:border-t-0 md:border-l"
            style={{ borderColor: "var(--border)", background: "var(--card)" }}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold truncate" style={{ color: "var(--foreground)" }}>
                {(selectedNode.node.name as string) || "unknown"}
              </h3>
              <button
                onClick={() => setSelectedNode(null)}
                aria-label="Close details"
                className="h-8 w-8 -mr-1 flex items-center justify-center rounded-lg shrink-0 transition-colors active:bg-[var(--muted)]"
                style={{ color: "var(--muted-foreground)" }}
              >
                &#x2715;
              </button>
            </div>

            <div className="space-y-3">
              <Badge
                variant={
                  selectedNode.node.label === "Class"
                    ? "info"
                    : selectedNode.node.label === "Function"
                      ? "success"
                      : selectedNode.node.label === "ApiRoute"
                        ? "warning"
                        : "default"
                }
              >
                {selectedNode.node.label}
              </Badge>

              {selectedNode.node.file_path && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "var(--muted-foreground)" }}>File</p>
                  <p className="text-xs font-mono break-all" style={{ color: "var(--muted-foreground)" }}>{selectedNode.node.file_path}</p>
                </div>
              )}

              {selectedNode.node.start_line && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "var(--muted-foreground)" }}>Location</p>
                  <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
                    Line {String(selectedNode.node.start_line)}
                    {selectedNode.node.end_line && ` — ${String(selectedNode.node.end_line)}`}
                  </p>
                </div>
              )}

              {selectedNode.node.extends && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "var(--muted-foreground)" }}>Extends</p>
                  <p className="text-xs" style={{ color: "var(--foreground)" }}>{String(selectedNode.node.extends)}</p>
                </div>
              )}

              {selectedNode.outgoing.length > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: "var(--muted-foreground)" }}>
                    Outgoing ({selectedNode.outgoing.length})
                  </p>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {selectedNode.outgoing.map((r, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-[10px]">
                        <span style={{ color: "var(--muted-foreground)" }}>{r.rel_type}</span>
                        <span className="truncate" style={{ color: "var(--foreground)" }}>{r.target_name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedNode.incoming.length > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: "var(--muted-foreground)" }}>
                    Incoming ({selectedNode.incoming.length})
                  </p>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {selectedNode.incoming.map((r, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-[10px]">
                        <span style={{ color: "var(--muted-foreground)" }}>{r.rel_type}</span>
                        <span className="truncate" style={{ color: "var(--foreground)" }}>{r.source_name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function FilterPanel({
  activeFilters,
  nodeCounts,
  searchQuery,
  setSearchQuery,
  toggleFilter,
  onDone,
}: {
  activeFilters: Set<string>;
  nodeCounts: Record<string, number>;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  toggleFilter: (type: string) => void;
  onDone?: () => void;
}) {
  return (
    <>
      <div>
        <p className="text-[10px] uppercase tracking-wider mb-2 font-medium" style={{ color: "var(--muted-foreground)" }}>Filter</p>
        <div className="space-y-1">
          {ALL_NODE_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => toggleFilter(type)}
              className="flex items-center gap-2 w-full min-h-[36px] px-2 py-1.5 rounded text-xs transition-colors"
              style={activeFilters.has(type) ? { background: "var(--card)", color: "var(--foreground)" } : { color: "var(--muted-foreground)" }}
            >
              <div
                className="h-2 w-2 rounded-full shrink-0"
                style={{ background: NODE_COLORS[type]?.border || "#666" }}
              />
              <span className="truncate">{type}</span>
              <span className="ml-auto text-[10px]" style={{ color: "var(--muted-foreground)" }}>{nodeCounts[type] || 0}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="text-[10px] uppercase tracking-wider mb-2 font-medium" style={{ color: "var(--muted-foreground)" }}>Search</p>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter nodes..."
          className="w-full h-9 px-2.5 text-xs rounded border focus:outline-none"
          style={{ background: "var(--input-bg)", borderColor: "var(--input-border)", color: "var(--input-text)" }}
        />
      </div>

      <div>
        <p className="text-[10px] uppercase tracking-wider mb-2 font-medium" style={{ color: "var(--muted-foreground)" }}>Legend</p>
        <div className="space-y-1">
          {Object.entries(REL_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2 text-[10px]" style={{ color: "var(--muted-foreground)" }}>
              <div className="h-0.5 w-3 rounded shrink-0" style={{ background: color }} />
              {type}
            </div>
          ))}
        </div>
      </div>

      {onDone && (
        <Button size="sm" variant="secondary" className="w-full" onClick={onDone}>
          Done
        </Button>
      )}
    </>
  );
}
