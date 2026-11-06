"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { LoadingState } from "@/components/ui/LoadingState";
import { EmptyState } from "@/components/ui/EmptyState";
import { RepoSelector } from "@/components/ui/RepoSelector";
import { api } from "@/lib/api";

type ReviewMode = "full" | "static";

interface ReviewIssue {
  severity: string;
  title: string;
  explanation: string;
  file?: string;
  line?: number;
  suggestion?: string;
  source: string;
}

interface ReviewResult {
  issues: ReviewIssue[];
  counts: Record<string, number>;
  total: number;
  static_count: number;
  ai_count: number;
  summary: string;
  file: string;
  language: string;
}

type ViewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; result: ReviewResult };

const SAMPLE_CODE = `import { TokenRepository } from '../repositories/token';
import { UserRepository } from '../repositories/user';

export async function validateToken(token: string): Promise<boolean> {
  const decoded = TokenRepository.decode(token);
  if (!decoded) return false;

  const user = await UserRepository.findById(decoded.userId);
  if (!user || user.status !== 'active') return false;

  return TokenRepository.isValid(decoded);
}

export async function refreshToken(oldToken: string): Promise<string | null> {
  const isValid = await validateToken(oldToken);
  if (!isValid) return null;
  
  const decoded = TokenRepository.decode(oldToken);
  if (!decoded) return null;

  return TokenRepository.generate(decoded.userId);
}`;

const SEVERITY_CONFIG: Record<string, { color: string; bg: string; border: string }> = {
  CRITICAL: { color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20" },
  HIGH: { color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20" },
  MEDIUM: { color: "text-yellow-400", bg: "bg-yellow-500/10", border: "border-yellow-500/20" },
  LOW: { color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
};

export function CodeReviewView() {
  const [mode, setMode] = useState<ReviewMode>("full");
  const [repoValue, setRepoValue] = useState("");
  const [owner = "", repo = ""] = repoValue.split("/");
  const [filePath, setFilePath] = useState("src/services/auth.ts");
  const [code, setCode] = useState(SAMPLE_CODE);
  const [language, setLanguage] = useState("TypeScript");
  const [diff, setDiff] = useState("");
  const [state, setState] = useState<ViewState>({ status: "idle" });

  const canReview = code.trim().length > 0 && !(
    mode === "full" && (owner.trim().length === 0 || repo.trim().length === 0)
  ) && state.status !== "loading";

  const handleReview = async () => {
    if (!canReview) return;
    setState({ status: "loading" });

    try {
      let result: ReviewResult;
      if (mode === "full") {
        result = await api.codeReview.review({
          owner: owner.trim(),
          repo: repo.trim(),
          file_path: filePath.trim(),
          code,
          language,
          diff: diff.trim() || undefined,
        });
      } else {
        const res = await api.codeReview.staticCheck(code, language, filePath.trim());
        result = {
          issues: res.issues,
          counts: {},
          total: res.total,
          static_count: res.total,
          ai_count: 0,
          summary: res.total > 0
            ? `Found ${res.total} static analysis issues.`
            : "No static analysis issues found.",
          file: res.file,
          language: res.language,
        };
      }
      setState({ status: "success", result });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setState({ status: "error", message });
    }
  };

  return (
    <div className="flex flex-col lg:flex-row min-h-full lg:h-full">
      {/* Left: Input panel */}
      <div
        className="w-full lg:w-[420px] border-b lg:border-b-0 lg:border-r flex flex-col shrink-0"
        style={{ background: "var(--card)", color: "var(--foreground)", borderColor: "var(--border)" }}
      >
        {/* Header */}
        <div className="p-4 border-b" style={{ borderColor: "var(--border)" }}>
          <h1 className="text-lg font-bold tracking-tight">Code Review</h1>
          <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>
            AI-powered code review with static analysis
          </p>
        </div>

        {/* Mode tabs */}
        <div className="flex border-b" style={{ borderColor: "var(--border)" }}>
          <button
            onClick={() => setMode("full")}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
              mode === "full" ? "border-b-2 border-emerald-500" : ""
            }`}
            style={mode === "full" ? { color: "var(--foreground)" } : { color: "var(--muted-foreground)" }}
          >
            Full Review
          </button>
          <button
            onClick={() => setMode("static")}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
              mode === "static" ? "border-b-2 border-emerald-500" : ""
            }`}
            style={mode === "static" ? { color: "var(--foreground)" } : { color: "var(--muted-foreground)" }}
          >
            Static Only
          </button>
        </div>

        {/* Inputs */}
        <div className="p-4 space-y-4 lg:flex-1 lg:overflow-y-auto">
          {mode === "full" && (
            <div>
              <label className="text-xs mb-1 block" style={{ color: "var(--muted-foreground)" }}>Repository</label>
              <RepoSelector
                value={repoValue}
                onChange={(nextOwner, nextRepo) => setRepoValue(`${nextOwner}/${nextRepo}`)}
                className="[&>button]:h-8 [&>button]:text-xs"
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs mb-1 block" style={{ color: "var(--muted-foreground)" }}>File path</label>
              <input
                type="text"
                placeholder="src/auth.ts"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
                className="w-full h-8 px-2.5 text-xs rounded-lg border focus:outline-none focus:border-zinc-500"
                style={{
                  background: "var(--input-bg)",
                  borderColor: "var(--input-border)",
                  color: "var(--input-text)",
                }}
              />
            </div>
            <div>
              <label className="text-xs mb-1 block" style={{ color: "var(--muted-foreground)" }}>Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full h-8 px-2.5 text-xs rounded-lg border focus:outline-none focus:border-zinc-500"
                style={{
                  background: "var(--input-bg)",
                  borderColor: "var(--input-border)",
                  color: "var(--input-text)",
                }}
              >
                <option>TypeScript</option>
                <option>JavaScript</option>
                <option>Python</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs mb-1 block" style={{ color: "var(--muted-foreground)" }}>Code to review</label>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-48 px-3 py-2 text-xs font-mono rounded-lg border focus:outline-none focus:border-zinc-500 resize-none leading-relaxed"
              style={{
                background: "var(--input-bg)",
                borderColor: "var(--input-border)",
                color: "var(--input-text)",
              }}
              placeholder="Paste your code here..."
            />
          </div>

          <div>
            <label className="text-xs mb-1 block" style={{ color: "var(--muted-foreground)" }}>
              Diff (optional)
            </label>
            <textarea
              value={diff}
              onChange={(e) => setDiff(e.target.value)}
              className="w-full h-20 px-3 py-2 text-xs font-mono rounded-lg border focus:outline-none focus:border-zinc-500 resize-none leading-relaxed"
              style={{
                background: "var(--input-bg)",
                borderColor: "var(--input-border)",
                color: "var(--input-text)",
              }}
              placeholder="+ added line&#10;- removed line"
            />
          </div>
        </div>

        {/* Action */}
        <div className="p-4 border-t" style={{ borderColor: "var(--border)" }}>
          <Button onClick={handleReview} disabled={!canReview} className="w-full">
            {state.status === "loading" ? "Reviewing..." : "Review Code"}
          </Button>
        </div>
      </div>

      {/* Right: Results panel */}
      <div className="flex-1 lg:overflow-y-auto min-w-0">
        {state.status === "idle" && (
          <EmptyState
            icon="🔍"
            title="Ready to review"
            description="Enter your code and click Review Code to get AI-powered feedback with static analysis."
          />
        )}

        {state.status === "loading" && <LoadingState message="Reviewing code..." />}

        {state.status === "error" && (
          <div className="p-6">
            <Card className="border-red-500/20 bg-red-500/5">
              <p className="text-sm font-medium text-red-500">Review failed</p>
              <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>{state.message}</p>
              <Button variant="secondary" size="sm" onClick={handleReview} className="mt-3">
                Retry
              </Button>
            </Card>
          </div>
        )}

        {state.status === "success" && <ReviewResults result={state.result} />}
      </div>
    </div>
  );
}

function ReviewResults({ result }: { result: ReviewResult }) {
  const { issues, counts, total, static_count, ai_count, summary } = result;

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Summary header */}
      <div>
        <h2 className="text-lg font-bold tracking-tight">Review Results</h2>
        <p className="text-sm mt-1" style={{ color: "var(--muted-foreground)" }}>{summary}</p>
      </div>

      {/* Severity counts */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((sev) => (
          <Card key={sev} padding="sm">
            <p className="text-[10px] sm:text-xs uppercase tracking-wider truncate" style={{ color: "var(--muted-foreground)" }}>{sev}</p>
            <p className={`text-xl sm:text-2xl font-bold mt-1 ${SEVERITY_CONFIG[sev].color}`}>
              {counts[sev] || 0}
            </p>
          </Card>
        ))}
      </div>

      {/* Source breakdown */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs" style={{ color: "var(--muted-foreground)" }}>
        <span>
          <span className="font-medium" style={{ color: "var(--foreground)" }}>{static_count}</span> static findings
        </span>
        <span>
          <span className="font-medium" style={{ color: "var(--foreground)" }}>{ai_count}</span> AI suggestions
        </span>
        <span>
          <span className="font-medium" style={{ color: "var(--foreground)" }}>{total}</span> total
        </span>
      </div>

      {/* Issues list */}
      {total === 0 ? (
        <Card>
          <EmptyState
            icon="✅"
            title="No issues found"
            description="Code looks clean. No static analysis issues or AI suggestions."
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {issues.map((issue, idx) => (
            <IssueCard key={idx} issue={issue} />
          ))}
        </div>
      )}
    </div>
  );
}

function IssueCard({ issue }: { issue: ReviewIssue }) {
  const config = SEVERITY_CONFIG[issue.severity] || SEVERITY_CONFIG.LOW;

  return (
    <Card padding="none" className={`border ${config.border} ${config.bg}/30`}>
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          <Badge className={`${config.color} ${config.bg} ${config.border} text-[10px] shrink-0`}>
            {issue.severity}
          </Badge>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-medium" style={{ color: "var(--foreground)" }}>{issue.title}</h3>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded ${
                  issue.source === "static" ? "" : "bg-emerald-500/10 text-emerald-500"
                }`}
                style={issue.source === "static" ? { background: "var(--muted)", color: "var(--muted-foreground)" } : undefined}
              >
                {issue.source === "static" ? "static" : "AI"}
              </span>
            </div>
          </div>
          {issue.line && (
            <span className="text-xs font-mono shrink-0" style={{ color: "var(--muted-foreground)" }}>
              L{issue.line}
            </span>
          )}
        </div>

        {/* Explanation */}
        <p className="text-xs mt-2 leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
          {issue.explanation}
        </p>

        {/* Suggestion */}
        {issue.suggestion && (
          <div className="mt-3 p-2.5 rounded-lg border" style={{ background: "var(--muted)", borderColor: "var(--border)" }}>
            <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "var(--muted-foreground)" }}>Suggestion</p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--foreground)" }}>{issue.suggestion}</p>
          </div>
        )}

        {/* File */}
        {issue.file && (
          <div className="mt-2 flex items-center gap-1.5 text-[10px] text-zinc-500">
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <span className="font-mono">{issue.file}{issue.line ? `:${issue.line}` : ""}</span>
          </div>
        )}
      </div>
    </Card>
  );
}
