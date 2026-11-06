"use client";

import { useMemo } from "react";
import ReactFlow, { Background, Controls, MiniMap, Node, Edge, MarkerType, BackgroundVariant, NodeProps, Handle, Position } from "reactflow";
import "reactflow/dist/style.css";
import type { AffectedNode, ImpactNode } from "@/lib/api";

const COLORS: Record<string, { bg: string; border: string; text: string }> = {
  File: { bg: "#dbeafe", border: "#3b82f6", text: "#1e40af" },
  Class: { bg: "#f3e8ff", border: "#a855f7", text: "#7e22ce" },
  Function: { bg: "#dcfce7", border: "#22c55e", text: "#166534" },
  Method: { bg: "#fef3c7", border: "#f59e0b", text: "#92400e" },
  ApiRoute: { bg: "#fee2e2", border: "#ef4444", text: "#991b1b" },
};

const TARGET_COLOR = { bg: "#fee2e2", border: "#ef4444", text: "#991b1b" };

interface Props { target: ImpactNode; directImpact: AffectedNode[]; indirectImpact: AffectedNode[]; dependencyPaths: string[][]; }

function ImpactNodeComponent({ data }: NodeProps) {
  const isTarget = data.isTarget as boolean;
  const depth = data.depth as number;
  const colors = isTarget ? TARGET_COLOR : COLORS[data.nodeType as string] || COLORS.File;
  return (
    <div className="rounded-lg px-3 py-2 shadow-lg transition-all duration-150"
      style={{ background: colors.bg, border: `1.5px solid ${colors.border}`, minWidth: 100, maxWidth: 200 }}>
      <Handle type="target" position={Position.Top} style={{ background: colors.border, width: 6, height: 6 }} />
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] font-medium" style={{ color: colors.text }}>{data.label as string}</span>
        {!isTarget && depth > 0 && <span className="text-[9px] opacity-60" style={{ color: colors.text }}>d{depth}</span>}
      </div>
      <p className="text-xs font-mono truncate mt-0.5" style={{ color: colors.text }} title={data.name as string}>{data.name as string}</p>
      <Handle type="source" position={Position.Bottom} style={{ background: colors.border, width: 6, height: 6 }} />
    </div>
  );
}

const nodeTypes = { impactNode: ImpactNodeComponent };
function toSafeId(id: string): string { return id.replace(/[^a-zA-Z0-9_-]/g, "_"); }

export function ImpactGraph({ target, directImpact, indirectImpact, dependencyPaths }: Props) {
  const { nodes, edges } = useMemo(() => {
    const nodeMap = new Map<string, { node: ImpactNode; depth: number }>();
    nodeMap.set(target.node_id, { node: target, depth: 0 });
    for (const d of directImpact) { if (!nodeMap.has(d.node.node_id)) nodeMap.set(d.node.node_id, { node: d.node, depth: d.depth }); }
    for (const i of indirectImpact) { if (!nodeMap.has(i.node.node_id)) nodeMap.set(i.node.node_id, { node: i.node, depth: i.depth }); }
    const allNodes = Array.from(nodeMap.values());
    const cols = Math.ceil(Math.sqrt(allNodes.length));
    const flowNodes: Node[] = allNodes.map((entry, idx) => ({
      id: toSafeId(entry.node.node_id), type: "impactNode",
      position: { x: (idx % cols) * 200, y: Math.floor(idx / cols) * 120 },
      data: { name: entry.node.name, label: entry.node.label, nodeType: entry.node.label, isTarget: entry.node.node_id === target.node_id, depth: entry.depth },
    }));
    const edgeSet = new Set<string>();
    const flowEdges: Edge[] = [];
    for (const path of dependencyPaths) {
      for (let i = 0; i < path.length - 1; i++) {
        const srcId = toSafeId(path[i]), tgtId = toSafeId(path[i + 1]), key = `${srcId}->${tgtId}`;
        if (!edgeSet.has(key)) { edgeSet.add(key); flowEdges.push({ id: key, source: srcId, target: tgtId, type: "smoothstep", animated: true, style: { stroke: "#64748b", strokeWidth: 1.5 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#64748b", width: 12, height: 12 } }); }
      }
    }
    return { nodes: flowNodes, edges: flowEdges };
  }, [target, directImpact, indirectImpact, dependencyPaths]);

  return (
    <div className="h-[400px] w-full rounded-lg border" style={{ borderColor: "var(--border)", background: "var(--background)" }}>
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView proOptions={{ hideAttribution: true }}>
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--border)" />
        <Controls className="!rounded-lg" style={{ background: "var(--card)", borderColor: "var(--border)" }} />
        <MiniMap nodeColor={(node) => { if (node.data?.isTarget) return TARGET_COLOR.border; const c = COLORS[node.data?.nodeType as string]; return c?.border || "#64748b"; }}
          maskColor="rgba(0,0,0,0.1)" className="!rounded-lg" style={{ background: "var(--muted)", borderColor: "var(--border)" }} />
      </ReactFlow>
    </div>
  );
}
