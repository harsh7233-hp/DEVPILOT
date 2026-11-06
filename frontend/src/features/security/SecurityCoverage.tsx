"use client";

import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { SecurityCoverage as CoverageType } from "@/lib/api";

const SECTION_LABELS: Record<string, string> = {
  static_analysis: "Static Analysis",
  dependency_analysis: "Dependency Analysis",
  secret_detection: "Secret Detection",
  configuration_analysis: "Configuration Analysis",
  asvs_checks: "OWASP ASVS Checks",
  manual_review: "Manual Review",
};

const STATE_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  completed: { color: "#059669", bg: "rgba(5,150,105,0.10)", label: "Completed" },
  partial: { color: "#d97706", bg: "rgba(217,119,6,0.10)", label: "Partial Analysis" },
  not_analyzed: { color: "#6b7280", bg: "rgba(107,114,128,0.10)", label: "Not Analyzed" },
};

export function SecurityCoverage({ coverage }: { coverage: CoverageType }) {
  const sections = Object.entries(coverage);
  const completedCount = sections.filter(([, v]) => v.state === "completed").length;

  return (
    <section aria-label="Security coverage">
      <div className="flex items-center justify-between mb-2.5">
        <h2 className="text-sm font-semibold">Security Coverage</h2>
        <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
          {completedCount}/{sections.length} sections completed
        </span>
      </div>
      <Card padding="sm">
        <div className="space-y-3">
          {sections.map(([key, section]) => {
            const style = STATE_STYLES[section.state] || STATE_STYLES.not_analyzed;
            const label = SECTION_LABELS[key] || key;
            return (
              <div key={key} className="flex items-start gap-3">
                <div className="shrink-0 mt-0.5">
                  <span className="inline-block h-2 w-2 rounded-full" style={{ background: style.color }} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-xs font-medium">{label}</p>
                    <Badge
                      variant={section.state === "completed" ? "success" : section.state === "partial" ? "warning" : "default"}
                      className="text-[9px]"
                    >
                      {style.label}
                    </Badge>
                  </div>
                  <p className="text-[10px] mt-0.5" style={{ color: "var(--muted-foreground)" }}>{section.detail}</p>
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </section>
  );
}
