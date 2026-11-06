"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { RepoSelector } from "@/components/ui/RepoSelector";
import { api } from "@/lib/api";
import type { PipelinesReport, PipelineInfo, PipelineSecurityIssue } from "@/lib/api";
import { StageProgress } from "@/features/intelligence/CodeIntelligenceView";
import { useIntelligence } from "@/features/intelligence/shared";
import { useSelectedRepo } from "@/lib/repo-context";

const PLATFORM_ICONS: Record<string, string> = {
  "GitHub Actions": "🐙",
  Jenkins: "🤵",
  "GitLab CI": "🦊",
  CircleCI: "⭕",
  "Travis CI": "🔺",
  Docker: "🐳",
  "Docker Compose": "🐙",
  Kubernetes: "☸️",
  Terraform: "🏗️",
};

const CAPABILITIES = ["build", "test", "lint", "security", "deploy"] as const;

function analyzePipelineSecurity(pipeline: PipelineInfo): PipelineSecurityIssue[] {
  const issues: PipelineSecurityIssue[] = [];
  const caps = pipeline.capabilities || {};

  if (pipeline.platform === "GitHub Actions") {
    if (!caps.security) {
      issues.push({
        severity: "MEDIUM",
        title: "No security scanning detected",
        detail: `Workflow "${pipeline.name}" does not appear to include security scanning steps (CodeQL, Trivy, Snyk, etc.).`,
        recommendation: "Add a security scanning job to catch vulnerabilities early in the CI pipeline.",
      });
    }
    if (!caps.test) {
      issues.push({
        severity: "LOW",
        title: "No test step detected",
        detail: `Workflow "${pipeline.name}" does not appear to include automated tests.`,
        recommendation: "Add test execution to prevent regressions from being merged.",
      });
    }
    if (pipeline.trigger.includes("pull request") || pipeline.trigger.includes("push")) {
      if (!caps.lint) {
        issues.push({
          severity: "LOW",
          title: "No linting detected",
          detail: `Workflow "${pipeline.name}" triggers on PRs/pushes but does not include linting.`,
          recommendation: "Add a lint step to enforce code quality standards on every change.",
        });
      }
    }
  }

  if (pipeline.platform === "Docker") {
    issues.push({
      severity: "INFO",
      title: "Docker configuration detected",
      detail: "Ensure the Dockerfile follows security best practices: use non-root user, minimize layers, scan images.",
      recommendation: "Use multi-stage builds, run as non-root, and scan with tools like Trivy.",
    });
  }

  if (pipeline.platform === "Terraform") {
    issues.push({
      severity: "INFO",
      title: "Infrastructure as Code detected",
      detail: "Terraform configurations manage infrastructure. Ensure state is stored securely and plans are reviewed.",
      recommendation: "Use remote state with encryption, enable plan reviews, and run tfsec for security checks.",
    });
  }

  if (pipeline.platform === "Kubernetes") {
    issues.push({
      severity: "INFO",
      title: "Kubernetes manifests detected",
      detail: "Ensure manifests include resource limits, security contexts, and network policies.",
      recommendation: "Add resource limits, run as non-root, and apply network policies.",
    });
  }

  return issues;
}

export function PipelinesView() {
  const { repo: globalRepo } = useSelectedRepo();
  const [repoValue, setRepoValue] = useState("");
  const [owner = "", repo = ""] = repoValue.split("/");
  const [report, setReport] = useState<PipelinesReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { scanning, job } = useIntelligence(owner, repo);

  // Use global repo if available
  useEffect(() => {
    if (globalRepo && !repoValue) {
      setRepoValue(globalRepo.fullName);
    }
  }, [globalRepo, repoValue]);

  useEffect(() => {
    if (!owner || !repo) {
      queueMicrotask(() => setLoading(false));
      return;
    }
    let cancelled = false;
    queueMicrotask(() => {
      setLoading(true);
      setError(null);
    });
    api.intelligence
      .pipelines(owner, repo)
      .then((r) => !cancelled && setReport(r))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Failed to detect pipelines"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [owner, repo]);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 pb-3 border-b shrink-0" style={{ borderColor: "var(--border)" }}>
        <div className="mb-3">
          <h1 className="text-lg sm:text-xl font-bold tracking-tight">Pipelines</h1>
          <p className="text-xs mt-0.5 hidden sm:block" style={{ color: "var(--muted-foreground)" }}>
            CI/CD configuration detected in the repository — DevPilot reads config files only and never triggers pipelines
          </p>
        </div>
        <RepoSelector value={repoValue} onChange={(o, r) => setRepoValue(`${o}/${r}`)} className="w-full sm:max-w-56" />
      </div>

      {scanning && job && <StageProgress job={job} />}
      {error && <ErrorState message={error} onRetry={() => owner && repo && api.intelligence.pipelines(owner, repo).then(setReport)} />}

      {!owner || !repo ? (
        <div className="flex-1 flex items-center justify-center p-4">
          <EmptyState icon="⚙️" title="Select a repository" description="Choose a repository to detect its CI/CD pipelines." />
        </div>
      ) : loading ? (
        <LoadingState message="Detecting pipelines..." />
      ) : !report || !report.available ? (
        <div className="flex-1 flex items-center justify-center p-4">
          <EmptyState
            icon="🔍"
            title="No pipelines detected"
            description={
              report?.note ||
              "No CI/CD configuration files were found (GitHub Actions, Jenkins, GitLab CI, CircleCI, Travis, Dockerfile, docker-compose, Kubernetes or Terraform)."
            }
          />
        </div>
      ) : (
        <PipelinesContent report={report} owner={owner} repo={repo} />
      )}
    </div>
  );
}

function PipelinesContent({ report, owner, repo }: { report: PipelinesReport; owner: string; repo: string }) {
  const caps = report.overall_capabilities || {};
  const activeCaps = CAPABILITIES.filter((c) => caps[c]);

  // Analyze security across all pipelines
  const allSecurityIssues = report.pipelines.flatMap(analyzePipelineSecurity);
  const criticalIssues = allSecurityIssues.filter((i) => i.severity === "CRITICAL" || i.severity === "HIGH");

  return (
    <div className="flex-1 overflow-y-auto overscroll-contain p-4 space-y-5 max-w-5xl">
      {/* Overview */}
      <Card padding="md">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="col-span-2 sm:col-span-1">
            <p className="text-[10px] uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>Total detected</p>
            <p className="text-3xl font-bold mt-0.5">{report.total}</p>
          </div>
          <div className="col-span-2 sm:col-span-3">
            <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: "var(--muted-foreground)" }}>Overall capabilities (from actual config)</p>
            <div className="flex flex-wrap gap-1.5">
              {CAPABILITIES.map((c) =>
                caps[c] ? (
                  <Badge key={c} variant="success">{c}</Badge>
                ) : (
                  <span key={c} className="text-[11px] px-2 py-0.5 rounded-full border opacity-50" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>
                    {c}
                  </span>
                )
              )}
              {activeCaps.length === 0 && (
                <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>None recognized</span>
              )}
            </div>
          </div>
        </div>
        {Object.keys(report.by_platform).length > 0 && (
          <div className="mt-4 pt-3 border-t flex flex-wrap gap-1.5" style={{ borderColor: "var(--border)" }}>
            {Object.entries(report.by_platform).map(([platform, count]) => (
              <span key={platform} className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md" style={{ background: "var(--muted)", color: "var(--foreground)" }}>
                {PLATFORM_ICONS[platform] || "⚙️"} {platform}: {count}
              </span>
            ))}
          </div>
        )}
      </Card>

      {/* Pipeline security summary */}
      {allSecurityIssues.length > 0 && (
        <section aria-label="Pipeline security">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold">Pipeline Security Analysis</h2>
            <Badge variant={criticalIssues.length > 0 ? "warning" : "info"}>{allSecurityIssues.length} issue(s)</Badge>
          </div>
          <Card padding="md">
            <div className="space-y-3">
              {allSecurityIssues.slice(0, 10).map((issue, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span
                    className="h-2 w-2 rounded-full shrink-0 mt-1.5"
                    style={{ background: issue.severity === "CRITICAL" || issue.severity === "HIGH" ? "#dc2626" : issue.severity === "MEDIUM" ? "#d97706" : "#3b82f6" }}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-medium">{issue.title}</p>
                      <Badge variant={issue.severity === "CRITICAL" || issue.severity === "HIGH" ? "error" : issue.severity === "MEDIUM" ? "warning" : "info"} className="text-[9px]">
                        {issue.severity}
                      </Badge>
                    </div>
                    <p className="text-[10px] mt-0.5" style={{ color: "var(--muted-foreground)" }}>{issue.detail}</p>
                    {issue.recommendation && (
                      <p className="text-[10px] mt-0.5 text-emerald-600 dark:text-emerald-400">{issue.recommendation}</p>
                    )}
                  </div>
                </div>
              ))}
              {allSecurityIssues.length > 10 && (
                <p className="text-[10px] text-center" style={{ color: "var(--muted-foreground)" }}>
                  +{allSecurityIssues.length - 10} more issues
                </p>
              )}
            </div>
          </Card>
          <p className="text-[10px] mt-1.5" style={{ color: "var(--muted-foreground)" }}>
            Static analysis of CI/CD configuration files. Findings are based on detected capabilities and standard security practices.
          </p>
        </section>
      )}

      {/* Pipeline list */}
      <section>
        <h2 className="text-sm font-semibold mb-2">Detected Configurations</h2>
        <div className="space-y-2">
          {report.pipelines.map((p, i) => (
            <PipelineCard key={`${p.name}-${i}`} pipeline={p} owner={owner} repo={repo} />
          ))}
        </div>
      </section>

      <p className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
        Detection is based on repository file paths and config file contents fetched via the GitHub API.
        Capabilities are inferred from keywords in the configuration — verify critical workflows before relying on this summary.
      </p>
    </div>
  );
}

function PipelineCard({ pipeline, owner, repo }: { pipeline: PipelineInfo; owner: string; repo: string }) {
  const caps = pipeline.capabilities || {};
  const securityIssues = analyzePipelineSecurity(pipeline);

  return (
    <Card padding="sm">
      <div className="flex items-start gap-3">
        <span className="text-xl shrink-0" aria-hidden>{PLATFORM_ICONS[pipeline.platform] || "⚙️"}</span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold truncate">{pipeline.name}</p>
            <Badge variant="default">{pipeline.platform}</Badge>
            {securityIssues.length > 0 && (
              <Badge variant={securityIssues.some((i) => i.severity === "HIGH") ? "warning" : "info"} className="text-[9px]">
                {securityIssues.length} security note(s)
              </Badge>
            )}
          </div>

          <p className="text-[11px] font-mono truncate mt-1" style={{ color: "var(--muted-foreground)" }}>
            {pipeline.files.join(", ")}
          </p>

          {(pipeline.trigger.length > 0 || pipeline.job_count > 0) && (
            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[11px]" style={{ color: "var(--muted-foreground)" }}>
              {pipeline.trigger.length > 0 && (
                <span>Triggers: <span style={{ color: "var(--foreground)" }}>{pipeline.trigger.join(", ")}</span></span>
              )}
              {pipeline.job_count > 0 && (
                <span>Jobs: <span style={{ color: "var(--foreground)" }}>{pipeline.job_count}</span>
                  {pipeline.jobs.length > 0 && ` (${pipeline.jobs.slice(0, 5).join(", ")}${pipeline.jobs.length > 5 ? "…" : ""})`}
                </span>
              )}
            </div>
          )}

          <div className="flex flex-wrap gap-1.5 mt-2">
            {CAPABILITIES.map((c) =>
              caps[c] ? <Badge key={c} variant="info">{c}</Badge> : null
            )}
          </div>

          {/* Security issues for this pipeline */}
          {securityIssues.length > 0 && (
            <div className="mt-2 pt-2 border-t space-y-1.5" style={{ borderColor: "var(--border)" }}>
              {securityIssues.map((issue, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-[9px] mt-0.5" style={{ color: issue.severity === "HIGH" ? "#dc2626" : issue.severity === "MEDIUM" ? "#d97706" : "#3b82f6" }}>
                    {issue.severity === "HIGH" ? "⚠" : issue.severity === "MEDIUM" ? "●" : "ℹ"}
                  </span>
                  <p className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>{issue.title}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
