"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  type DeepScanJobStatus,
  type DeepScanReport,
  type SecurityFinding,
  type HealthCard,
  type SecretFinding,
} from "@/lib/api";

export type { SecurityFinding, HealthCard, SecretFinding };

export function useDeepScan(owner: string, repo: string) {
  const [report, setReport] = useState<DeepScanReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [job, setJob] = useState<DeepScanJobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const r = await api.security.report(owner, repo);
      setReport(r.available ? r : null);
    } catch {
      setReport(null);
    }
  }, [owner, repo]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => setLoading(true));
    api.security
      .report(owner, repo)
      .then((r) => {
        if (!cancelled) setReport(r.available ? r : null);
      })
      .catch(() => {
        if (!cancelled) setReport(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [owner, repo, stopPolling]);

  const startScan = useCallback(
    async (branch = "main", force = true) => {
      if (!owner || !repo || scanning) return;
      setError(null);
      try {
        const res = await api.security.startScan(owner, repo, branch, force);
        if (res.cached) {
          await refresh();
          return;
        }
        if (!res.job_id) return;
        setScanning(true);
        setJob({
          id: res.job_id, owner, repo, branch, status: "pending",
          progress: 0, stage: 0, message: "Starting deep scan...", stages: [], error: null,
        });
        stopPolling();
        pollRef.current = setInterval(async () => {
          try {
            const { job: j } = await api.security.scanStatus(owner, repo, res.job_id as string);
            setJob(j);
            if (j.status === "completed" || j.status === "failed") {
              stopPolling();
              setScanning(false);
              if (j.status === "failed") setError(j.error || "Scan failed");
              else await refresh();
            }
          } catch {
            /* keep polling */
          }
        }, 1500);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start scan");
      }
    },
    [owner, repo, scanning, refresh, stopPolling]
  );

  useEffect(() => () => stopPolling(), [stopPolling]);

  return { report, loading, scanning, job, error, startScan, refresh };
}

export function scoreColor(score: number): string {
  if (score >= 80) return "#059669";
  if (score >= 60) return "#d97706";
  return "#dc2626";
}

export const SEVERITY_STYLE: Record<string, { color: string; bg: string }> = {
  CRITICAL: { color: "#dc2626", bg: "rgba(220,38,38,0.12)" },
  HIGH: { color: "#ea580c", bg: "rgba(234,88,12,0.12)" },
  MEDIUM: { color: "#d97706", bg: "rgba(217,119,6,0.14)" },
  LOW: { color: "#2563eb", bg: "rgba(37,99,235,0.10)" },
};

export function severityBadgeVariant(sev: string): "error" | "warning" | "info" | "default" {
  if (sev === "CRITICAL" || sev === "HIGH") return "error";
  if (sev === "MEDIUM") return "warning";
  if (sev === "LOW") return "info";
  return "default";
}

export function confidenceBadgeVariant(c: string): "success" | "warning" | "info" | "default" {
  if (c === "HIGH") return "success";
  if (c === "MEDIUM") return "warning";
  return "info";
}

export function ScoreRing({ score, size = 110 }: { score: number | null; size?: number }) {
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score ?? 0));
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} stroke="var(--muted)" />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          strokeWidth={stroke} strokeLinecap="round"
          stroke={score != null ? scoreColor(pct) : "var(--muted)"}
          strokeDasharray={`${(pct / 100) * c} ${c}`}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl sm:text-2xl font-bold" style={{ color: score != null ? scoreColor(pct) : "var(--muted-foreground)" }}>
          {score != null ? Math.round(pct) : "—"}
        </span>
        <span className="text-[9px]" style={{ color: "var(--muted-foreground)" }}>/ 100</span>
      </div>
    </div>
  );
}
