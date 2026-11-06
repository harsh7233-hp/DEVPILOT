"use client";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  severityBadgeVariant,
  confidenceBadgeVariant,
  type SecurityFinding,
} from "@/features/security/shared";

const SEV_BORDER_COLORS: Record<string, string> = {
  CRITICAL: "#dc2626",
  HIGH: "#ea580c",
  MEDIUM: "#d97706",
  LOW: "#2563eb",
};

const STATUS_OPTIONS = [
  { value: "open", label: "Open" },
  { value: "false_positive", label: "False Positive" },
  { value: "accepted_risk", label: "Accepted Risk" },
  { value: "needs_review", label: "Needs Review" },
  { value: "resolved", label: "Resolved" },
] as const;

export function FindingDetailPanel({
  finding,
  onClose,
  onStatusChange,
  updating,
}: {
  finding: SecurityFinding;
  onClose: () => void;
  onStatusChange: (fingerprint: string, status: string, note: string) => void;
  updating: boolean;
}) {
  const status = finding.status || "open";
  const borderColor = SEV_BORDER_COLORS[finding.severity] || "#6b7280";
  return (
    <div
      className="rounded-xl border-l-4 p-5"
      style={{ borderColor, background: "var(--card)", border: `1px solid var(--border)`, borderLeftColor: borderColor }}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold">{finding.title}</h3>
          <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
            <Badge variant={severityBadgeVariant(finding.severity)}>{finding.severity}</Badge>
            <Badge variant={confidenceBadgeVariant(finding.confidence)}>{finding.confidence} confidence</Badge>
            <Badge variant="default">{finding.category}</Badge>
            {finding.manual_review_required && <Badge variant="warning">Manual Review Required</Badge>}
            {status !== "open" && (
              <Badge variant={status === "false_positive" ? "info" : status === "resolved" ? "success" : "warning"}>
                {STATUS_OPTIONS.find((s) => s.value === status)?.label || status}
              </Badge>
            )}
          </div>
        </div>
        <button onClick={onClose} className="text-lg shrink-0 opacity-50 hover:opacity-100" aria-label="Close">✕</button>
      </div>

      <div className="space-y-3 text-xs">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: "var(--muted-foreground)" }}>File</p>
            <p className="font-mono truncate">{finding.file}:{finding.line}</p>
          </div>
          {finding.symbol && (
            <div>
              <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: "var(--muted-foreground)" }}>Function/Class</p>
              <p className="font-mono truncate">{finding.symbol}</p>
            </div>
          )}
        </div>

        {finding.masked_preview && (
          <div>
            <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: "var(--muted-foreground)" }}>Masked Preview</p>
            <p className="font-mono text-sm" style={{ color: "#dc2626" }}>{finding.masked_preview}</p>
          </div>
        )}

        <div>
          <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: "var(--muted-foreground)" }}>Evidence</p>
          <pre className="mt-1 p-2 rounded-lg text-[11px] font-mono overflow-x-auto whitespace-pre-wrap" style={{ background: "var(--muted)", color: "var(--foreground)" }}>
            {finding.evidence}
          </pre>
        </div>

        <div>
          <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: "var(--muted-foreground)" }}>Why this matters</p>
          <p>{finding.why}</p>
        </div>

        <div>
          <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: "var(--muted-foreground)" }}>Recommendation</p>
          <p style={{ color: "#059669" }}>{finding.recommendation}</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: "var(--muted-foreground)" }}>Detection Method</p>
            <p>{finding.detection_method}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: "var(--muted-foreground)" }}>Rule ID</p>
            <p className="font-mono">{finding.rule_id}</p>
          </div>
        </div>

        {finding.standards && finding.standards.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: "var(--muted-foreground)" }}>Standards Mapping</p>
            <div className="space-y-1 mt-1">
              {finding.standards.map((s: { standard: string; id: string; name: string }, i: number) => (
                <div key={i} className="flex items-center gap-2 text-[11px]">
                  <Badge variant="default">{s.standard}</Badge>
                  <span className="font-mono">{s.id}</span>
                  <span style={{ color: "var(--muted-foreground)" }}>{s.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {finding.status_note && (
          <div className="rounded-lg p-2" style={{ background: "var(--muted)" }}>
            <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: "var(--muted-foreground)" }}>Review Note</p>
            <p className="text-[11px]">{finding.status_note}</p>
          </div>
        )}

        <div className="pt-2 border-t flex items-center gap-2 flex-wrap" style={{ borderColor: "var(--border)" }}>
          <p className="text-[10px] font-semibold mr-1" style={{ color: "var(--muted-foreground)" }}>Status:</p>
          {STATUS_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              size="sm"
              variant={status === opt.value ? "primary" : "secondary"}
              onClick={() => onStatusChange(finding.fingerprint, opt.value, "")}
              disabled={updating || status === opt.value}
              className="h-7 text-[10px]"
            >
              {opt.label}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}
