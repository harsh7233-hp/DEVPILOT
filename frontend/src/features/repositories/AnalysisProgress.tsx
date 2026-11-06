"use client";

import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { AnalysisJob } from "@/lib/api";

interface AnalysisProgressProps { job: AnalysisJob; }

const statusConfig = {
  pending: { color: "bg-yellow-500", variant: "warning" as const, label: "Pending" },
  processing: { color: "bg-blue-500 animate-pulse", variant: "info" as const, label: "Processing" },
  completed: { color: "bg-emerald-500", variant: "success" as const, label: "Completed" },
  failed: { color: "bg-red-500", variant: "error" as const, label: "Failed" },
};

export function AnalysisProgress({ job }: AnalysisProgressProps) {
  const config = statusConfig[job.status];
  const progressPercent = Math.round(job.progress * 100);

  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`h-2.5 w-2.5 rounded-full ${config.color}`} />
          <h3 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>Analysis {config.label}</h3>
          <Badge variant={config.variant}>{config.label}</Badge>
        </div>
        <span className="text-xs font-mono" style={{ color: "var(--muted-foreground)" }}>{job.id.slice(0, 8)}</span>
      </div>

      <div>
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span style={{ color: "var(--muted-foreground)" }}>{job.message}</span>
          <span style={{ color: "var(--muted-foreground)" }}>{progressPercent}%</span>
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--muted)" }}>
          <div className={`h-full rounded-full transition-all duration-500 ${job.status === "failed" ? "bg-red-500" : "bg-emerald-500"}`}
            style={{ width: `${progressPercent}%` }} />
        </div>
      </div>

      {job.status === "completed" && (
        <div className="grid grid-cols-3 gap-2 sm:gap-4 text-xs">
          <div>
            <p style={{ color: "var(--muted-foreground)" }}>Total Files</p>
            <p className="font-medium mt-0.5" style={{ color: "var(--foreground)" }}>{job.total_files.toLocaleString()}</p>
          </div>
          <div>
            <p style={{ color: "var(--muted-foreground)" }}>Source Files</p>
            <p className="font-medium mt-0.5" style={{ color: "var(--foreground)" }}>{job.filtered_files.toLocaleString()}</p>
          </div>
          <div>
            <p style={{ color: "var(--muted-foreground)" }}>Languages</p>
            <p className="font-medium mt-0.5" style={{ color: "var(--foreground)" }}>{new Set(job.files.map((f) => f.language)).size}</p>
          </div>
        </div>
      )}

      {job.status === "completed" && job.files.length > 0 && (
        <div>
          <p className="text-xs mb-2" style={{ color: "var(--muted-foreground)" }}>Language Breakdown</p>
          <div className="flex flex-wrap gap-1.5">
            {getLanguageCounts(job.files).map(({ language, count }) => (
              <Badge key={language} variant="default">{language} ({count})</Badge>
            ))}
          </div>
        </div>
      )}

      {job.status === "failed" && job.error && (
        <div className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 rounded-lg px-3 py-2">
          {job.error}
        </div>
      )}
    </Card>
  );
}

function getLanguageCounts(files: { language: string }[]): { language: string; count: number }[] {
  const counts: Record<string, number> = {};
  for (const file of files) { counts[file.language] = (counts[file.language] || 0) + 1; }
  return Object.entries(counts).map(([language, count]) => ({ language, count })).sort((a, b) => b.count - a.count);
}
