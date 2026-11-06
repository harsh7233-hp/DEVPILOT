const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

import type { GraphNode, GraphNodeDetail, GraphRelationship } from "./graph-types";

export interface ImpactAnalysisRequest {
  owner: string;
  repo: string;
  node_id: string;
  max_depth?: number;
}

export interface ImpactNode {
  node_id: string;
  label: string;
  name: string;
  file_path?: string;
}

export interface AffectedNode {
  node: ImpactNode;
  depth: number;
  path: string[];
}

export interface ImpactResult {
  target: ImpactNode | null;
  risk: {
    level: "low" | "medium" | "high";
    score: number;
    reasons: string[];
  };
  metrics: {
    affected_files: number;
    affected_functions: number;
    affected_classes: number;
    affected_modules: number;
    affected_apis: number;
    direct_dependencies: number;
    indirect_dependencies: number;
    dependency_depth: number;
  };
  direct_impact: AffectedNode[];
  indirect_impact: AffectedNode[];
  dependency_paths: string[][];
}

interface FetchOptions extends RequestInit {
  params?: Record<string, string>;
}

/* ── Module 2: Deep Scan / Security types ── */

export interface HealthCard {
  title: string;
  score: number | null;
  formula: string | null;
  methodology: string;
  factors?: {
    name: string;
    score: number | null;
    weight: number;
    available: boolean;
    measurements: Record<string, unknown>;
    formula: string;
  }[];
  details?: Record<string, unknown>;
  measurements?: Record<string, unknown>;
  smells?: Record<string, unknown>;
  unavailable_reason?: string | null;
  is_proxy?: boolean;
  proxy_label?: string;
  analysis_kind?: string;
}

export interface SecurityPosture {
  score: number | null;
  executed_checks: number;
  passed_checks: number;
  failed_checks: number;
  open_findings: number;
  closed_findings: number;
  raw_deduction: number;
  applied_deduction: number;
  open_by_severity: Record<string, number>;
  formula: string;
  severity_points: Record<string, number>;
  confidence_factors: Record<string, number>;
  deduction_cap: number;
  note: string;
}

export interface SecurityFinding {
  rule_id: string;
  title: string;
  category: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  confidence: "HIGH" | "MEDIUM" | "LOW";
  file: string;
  line: number;
  symbol: string;
  evidence: string;
  why: string;
  recommendation: string;
  standards: { standard: string; id: string; name: string }[];
  detection_method: string;
  manual_review_required: boolean;
  source: string;
  category_label: string;
  fingerprint: string;
  status?: string;
  status_note?: string;
  masked_preview?: string;
}

export interface SecretFinding extends SecurityFinding {
  masked_preview: string;
}

export interface PerformanceFinding {
  rule_id: string;
  title: string;
  severity: string;
  confidence: string;
  file: string;
  line: number;
  symbol: string;
  evidence: string;
  why: string;
  recommendation: string;
  standards: never[];
  source: string;
  category_label: string;
  fingerprint: string;
  measured: boolean;
  note: string;
}

export interface DependencyVulnerability {
  package: string;
  installed_version: string;
  ecosystem: string;
  vulnerability_id: string;
  aliases: string[];
  summary: string;
  severity: string;
  affected_versions: string | null;
  recommended_version: string | null;
  fixed_version_available: boolean;
  source: string;
  manifest_source: string;
}

export interface DependencyReport {
  packages: { name: string; version: string | null; ecosystem: string; source: string }[];
  direct_dependencies: number;
  has_manifest: boolean;
  status: string;
  reason: string | null;
  vulnerabilities: DependencyVulnerability[];
  source: string | null;
}

export interface CoverageSection {
  state: "completed" | "partial" | "not_analyzed";
  detail: string;
  share?: number;
}

export interface SecurityCoverage {
  static_analysis: CoverageSection;
  dependency_analysis: CoverageSection;
  secret_detection: CoverageSection;
  configuration_analysis: CoverageSection;
  asvs_checks: CoverageSection;
  manual_review: CoverageSection;
}

export interface PriorityItem {
  fingerprint: string;
  kind: string;
  title: string;
  severity: string;
  confidence: string;
  priority_score: number;
  bucket: string;
  dependents: number;
  status: string;
  target: { file: string; line: number; symbol: string };
}

export interface DeepScanReport {
  available: boolean;
  owner: string;
  repo: string;
  branch: string;
  generated_at: number;
  analysis_kind: string;
  disclaimer: string;
  stats: {
    source_files: number;
    test_files: number;
    analyzed_files: number;
    code_files_in_tree: number;
  };
  posture: SecurityPosture | null;
  health_cards: {
    code_health: HealthCard;
    reliability: HealthCard;
    maintainability: HealthCard;
    security_posture: HealthCard;
    performance: HealthCard;
    test_coverage: HealthCard;
  };
  findings: SecurityFinding[];
  secrets: SecretFinding[];
  performance_issues: PerformanceFinding[];
  dependencies: DependencyReport;
  coverage: SecurityCoverage;
  priority_queue: PriorityItem[];
  status_overrides: Record<string, { status: string; note: string; updated_at: number }>;
  counts: {
    security: Record<string, number>;
    secrets: number;
    performance: Record<string, number>;
    total_findings: number;
  };
}

export interface DeepScanJobStatus {
  id: string;
  owner: string;
  repo: string;
  branch: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  stage: number;
  message: string;
  stages: string[];
  error: string | null;
}

export interface DevPilotInsight {
  id: string;
  kind: string;
  tone: string;
  title: string;
  detail: string;
  evidence: { label: string; file?: string; line?: number | null }[];
  href: string;
}

export interface AskDevPilotResponse {
  answer: string;
  sources: { file: string; line: string; traced?: boolean }[];
  dropped_citations?: string[];
  evidence_used: boolean;
  low_confidence?: boolean;
  error: string | null;
}

/* ── Module 3: Notification types ── */

export interface Notification {
  id: string;
  category: "security" | "performance" | "repository" | "pipeline" | "dependency" | "analysis" | "system";
  title: string;
  message: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  icon: string;
  href: string;
  entity_type: string;
  entity_id: string;
  owner: string;
  repo: string;
  read: boolean;
  created_at: number;
  meta: Record<string, unknown>;
}

export interface NotificationListResponse {
  notifications: Notification[];
  total: number;
  unread: number;
  offset: number;
  limit: number;
}

/* ── Module 3: Pipeline security types ── */

export interface PipelineSecurityIssue {
  severity: string;
  title: string;
  detail: string;
  file?: string;
  line?: number;
  recommendation?: string;
}

async function request<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { params, ...init } = options;

  let url = `${API_BASE}${path}`;
  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.set(key, value);
      }
    }
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  const res = await fetch(url, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export interface GitHubUser {
  id: number;
  login: string;
  name: string;
  avatar_url: string;
}

export interface GitHubRepo {
  id: number;
  name: string;
  full_name: string;
  description: string;
  language: string;
  default_branch: string;
  stars: number;
  forks: number;
  private: boolean;
  url: string;
  owner: {
    login: string;
    avatar_url: string;
  };
  updated_at: string;
}

export interface Branch {
  name: string;
  is_default: boolean;
}

export interface AnalysisJob {
  id: string;
  owner: string;
  repo: string;
  branch: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  message: string;
  total_files: number;
  filtered_files: number;
  files: { path: string; size: number; sha: string; language: string }[];
  error: string | null;
}

export const api = {
  auth: {
    getMe: () => request<{ user: GitHubUser }>("/api/auth/me"),
    logout: () => request<{ status: string }>("/api/auth/logout", { method: "POST" }),
    getGithubUrl: () => `${API_BASE}/api/auth/github`,
  },
  health: {
    aiStatus: () =>
      request<{ ai_configured: boolean; model: string | null; embeddings_configured: boolean }>(
        "/api/health/ai"
      ),
  },
  repositories: {
    list: (search?: string) =>
      request<{ repositories: GitHubRepo[] }>("/api/repositories", {
        params: search ? { search } : {},
      }),
    get: (owner: string, repo: string) =>
      request<{ repository: GitHubRepo }>(`/api/repositories/${owner}/${repo}`),
    getBranches: (owner: string, repo: string) =>
      request<{ branches: Branch[] }>(`/api/repositories/${owner}/${repo}/branches`),
  },
  analysis: {
    start: (owner: string, repo: string, branch: string) =>
      request<{ job_id: string; status: string }>("/api/analysis", {
        method: "POST",
        params: { owner, repo, branch },
      }),
    getStatus: (jobId: string) =>
      request<{ job: AnalysisJob }>(`/api/analysis/${jobId}`),
  },
  graph: {
    build: (owner: string, repo: string) =>
      request<{ status: string; repo_id: string; stats: Record<string, number> }>(
        `/api/repositories/${owner}/${repo}/graph/build`,
        { method: "POST" }
      ),
    getSummary: (owner: string, repo: string) =>
      request<{ repo_id: string; owner: string; name: string; nodes: Record<string, number>; relationships: Record<string, number> }>(
        `/api/repositories/${owner}/${repo}/graph`
      ),
    getNode: (owner: string, repo: string, nodeId: string) =>
      request<GraphNodeDetail>(
        `/api/repositories/${owner}/${repo}/graph/node/${encodeURIComponent(nodeId)}`
      ),
    getNodes: (owner: string, repo: string, label?: string) =>
      request<{ nodes: GraphNode[] }>(
        `/api/repositories/${owner}/${repo}/graph/nodes`,
        { params: label ? { label } : {} }
      ),
    getRelationships: (owner: string, repo: string) =>
      request<{ relationships: GraphRelationship[] }>(
        `/api/repositories/${owner}/${repo}/graph/relationships`
      ),
    delete: (owner: string, repo: string) =>
      request<{ deleted: boolean }>(
        `/api/repositories/${owner}/${repo}/graph`,
        { method: "DELETE" }
      ),
  },
  impact: {
    analyze: (body: ImpactAnalysisRequest) =>
      request<ImpactResult>("/api/impact/analyze", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  },
  ai: {
    chat: (owner: string, repo: string, question: string) =>
      request<{ answer: string; sources: { file: string; line: string; entity?: string }[]; error: string | null }>(
        "/api/ai/chat",
        { method: "POST", body: JSON.stringify({ owner, repo, question }) }
      ),
    clearHistory: (owner: string, repo: string) =>
      request<{ status: string }>(`/api/ai/${owner}/${repo}/history`, { method: "DELETE" }),
  },
  search: {
    semantic: (owner: string, repo: string, query: string, topK?: number) =>
      request<{
        results: { file: string; entity: string; kind: string; snippet: string; start_line: number; end_line: number; score: number }[];
        total_indexed: number;
        query: string;
      }>(
        "/api/search/semantic",
        { method: "POST", body: JSON.stringify({ owner, repo, query, top_k: topK || 10 }) }
      ),
    index: (owner: string, repo: string) =>
      request<{ status: string; chunks: number; repo_id: string }>(
        "/api/search/index",
        { method: "POST", body: JSON.stringify({ owner, repo }) }
      ),
  },
  dashboard: {
    get: (search?: string) =>
      request<{
        summary: {
          repositories: number;
          analyzed: number;
          total_files: number;
          total_functions: number;
          total_classes: number;
          total_nodes: number;
          total_relationships: number;
          ai_messages: number;
        };
        repositories: {
          owner: string;
          repo: string;
          status: string;
          language: string;
          stars: number;
          description: string;
          total_files: number;
          filtered_files: number;
          functions: number;
          classes: number;
          has_graph: boolean;
          nodes_count: number;
          rels_count: number;
          nodes_by_label: Record<string, number>;
          rels_by_type: Record<string, number>;
          ai_messages: number;
          analysis_jobs: {
            id: string;
            branch: string;
            status: string;
            progress: number;
            message: string;
            total_files: number;
            filtered_files: number;
          }[];
          latest_job_id: string | null;
          updated_at: string;
        }[];
      }>("/api/dashboard", { params: search ? { search } : {} }),
    getRepo: (owner: string, repo: string) =>
      request<{
        owner: string;
        repo: string;
        status: string;
        language: string;
        stars: number;
        description: string;
        total_files: number;
        filtered_files: number;
        functions: number;
        classes: number;
        has_graph: boolean;
        nodes_count: number;
        rels_count: number;
        nodes_by_label: Record<string, number>;
        rels_by_type: Record<string, number>;
        ai_messages: number;
        analysis_jobs: {
          id: string;
          branch: string;
          status: string;
          progress: number;
          message: string;
          total_files: number;
          filtered_files: number;
        }[];
        latest_job_id: string | null;
        updated_at: string;
      }>(`/api/dashboard/${owner}/${repo}`),
  },
  codeReview: {
    review: (body: { owner: string; repo: string; file_path: string; code: string; language?: string; entity_name?: string; diff?: string }) =>
      request<{
        issues: { severity: string; title: string; explanation: string; file?: string; line?: number; suggestion?: string; source: string }[];
        counts: Record<string, number>;
        total: number;
        static_count: number;
        ai_count: number;
        summary: string;
        file: string;
        language: string;
      }>(
        "/api/code-review/review",
        { method: "POST", body: JSON.stringify(body) }
      ),
    staticCheck: (code: string, language?: string, file_path?: string) =>
      request<{
        issues: { severity: string; title: string; explanation: string; file?: string; line?: number; suggestion?: string; source: string }[];
        total: number;
        file: string;
        language: string;
      }>(
        "/api/code-review/static",
        { method: "POST", body: JSON.stringify({ code, language, file_path }) }
      ),
  },
  intelligence: {
    startScan: (owner: string, repo: string, force = false, branch?: string) =>
      request<{ cached: boolean; job_id: string | null }>(
        `/api/intelligence/${owner}/${repo}/scan`,
        { method: "POST", params: { force: String(force), ...(branch ? { branch } : {}) } }
      ),
    scanStatus: (owner: string, repo: string, jobId: string) =>
      request<{ job: IntelligenceJobStatus }>(
        `/api/intelligence/${owner}/${repo}/scan/${jobId}`
      ),
    report: (owner: string, repo: string) =>
      request<IntelligenceReport>(`/api/intelligence/${owner}/${repo}/report`),
    pipelines: (owner: string, repo: string) =>
      request<PipelinesReport>(`/api/intelligence/${owner}/${repo}/pipelines`),
    riskMap: (owner: string, repo: string) =>
      request<RiskMapReport>(`/api/intelligence/${owner}/${repo}/risk-map`),
    suggestedChange: (body: SuggestedChangeRequest) =>
      request<SuggestedChangeResponse>("/api/intelligence/suggested-change", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  },
  security: {
    startScan: (owner: string, repo: string, branch = "main", force = true) =>
      request<{ cached: boolean; job_id: string | null }>(
        `/api/security/${owner}/${repo}/scan`,
        { method: "POST", params: { branch, force: String(force) } }
      ),
    scanStatus: (owner: string, repo: string, jobId: string) =>
      request<{ job: DeepScanJobStatus }>(
        `/api/security/${owner}/${repo}/scan/${jobId}`
      ),
    report: (owner: string, repo: string) =>
      request<DeepScanReport>(`/api/security/${owner}/${repo}/report`),
    coverage: (owner: string, repo: string) =>
      request<{ available: boolean; coverage: SecurityCoverage; generated_at: number }>(
        `/api/security/${owner}/${repo}/coverage`
      ),
    updateFindingStatus: (owner: string, repo: string, fingerprint: string, status: string, note = "") =>
      request<{
        status: string;
        finding_status: Record<string, unknown>;
        status_label: string;
        posture: SecurityPosture | null;
      }>(
        `/api/security/${owner}/${repo}/findings/status`,
        { method: "PATCH", body: JSON.stringify({ fingerprint, status, note }) }
      ),
  },
  ai2: {
    ask: (owner: string, repo: string, question: string) =>
      request<AskDevPilotResponse>(
        "/api/ai/ask",
        { method: "POST", body: JSON.stringify({ owner, repo, question }) }
      ),
    insights: (owner: string, repo: string) =>
      request<{ insights: DevPilotInsight[]; generated_by: string; note: string }>(
        `/api/ai/${owner}/${repo}/insights`
      ),
  },
  notifications: {
    list: (params?: { category?: string; unread_only?: boolean; limit?: number; offset?: number }) =>
      request<NotificationListResponse>("/api/notifications", { params: params as Record<string, string> }),
    count: () => request<{ unread: number }>("/api/notifications/count"),
    markRead: (id: string) =>
      request<{ status: string; unread: number }>(`/api/notifications/${id}/read`, { method: "PATCH" }),
    markAllRead: () =>
      request<{ status: string; marked_read: number; unread: number }>("/api/notifications/read-all", { method: "POST" }),
    delete: (id: string) =>
      request<{ status: string; unread: number }>(`/api/notifications/${id}`, { method: "DELETE" }),
  },
};

/* ── Intelligence types ── */

export interface IntelligenceJobStatus {
  id: string;
  owner: string;
  repo: string;
  branch: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  stage: number;
  message: string;
  stages: string[];
  error: string | null;
}

export interface IntelligenceFinding {
  id: string;
  category: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  file: string;
  symbol: string;
  line: number;
  problem: string;
  evidence: string;
  explanation: string;
  recommendation: string;
  source: string;
}

export interface Recommendation {
  id: string;
  file: string;
  symbol: string;
  current_problem: string;
  why_it_matters: string;
  recommended_solution: string;
  priority: "P1" | "P2" | "P3";
  expected_benefit: string;
  category: string;
  severity: string;
  source: string;
}

export interface PipelineInfo {
  name: string;
  platform: string;
  files: string[];
  trigger: string[];
  jobs: string[];
  job_count: number;
  capabilities: Record<string, boolean>;
  source: string;
}

export interface PipelinesReport {
  available: boolean;
  total: number;
  by_platform: Record<string, number>;
  overall_capabilities: Record<string, boolean>;
  pipelines: PipelineInfo[];
  note: string;
}

export interface RiskHotspot {
  node_id: string;
  name: string;
  label: string;
  file_path: string;
  risk: "high" | "medium" | "low";
  score: number;
  metrics: { fan_in: number; fan_out: number; total_degree: number; span_lines: number };
  reasons: string[];
}

export interface RiskMapReport {
  has_graph: boolean;
  available?: boolean;
  hotspots: RiskHotspot[];
  cycles: { files: string[]; size: number }[];
  summary: Record<string, number>;
  methodology?: string;
}

export const EMPTY_RISK_MAP: RiskMapReport = {
  has_graph: false,
  available: false,
  hotspots: [],
  cycles: [],
  summary: {},
  methodology: "",
};

export interface SuggestedChangeRequest {
  file: string;
  symbol?: string;
  problem: string;
  evidence?: string;
  explanation?: string;
  recommendation?: string;
  language?: string;
}

export interface SuggestedChangeResponse {
  file: string;
  symbol: string;
  diff: string;
  source: string;
  disclaimer: string;
  model: string;
}

export interface IntelligenceReport {
  available: boolean;
  owner: string;
  repo: string;
  branch: string;
  generated_at: number;
  stats: {
    total_files: number;
    filtered_files: number;
    analyzed_files: number;
    source_files: number;
    test_files: number;
    lines_of_code: number;
    languages: Record<string, { files: number; lines: number }>;
    language_count: number;
    classes: number;
    functions: number;
    methods: number;
    external_dependencies: number;
    unique_external_imports: string[];
    internal_imports: number;
    contributors: number | null;
    commits: number | null;
    has_lockfile: boolean;
    long_files: number;
    long_functions: number;
    avg_complexity: number;
  };
  health: {
    overall: number;
    categories: Record<string, number>;
    counts: {
      critical: number;
      high: number;
      medium: number;
      low: number;
      security_findings: number;
      performance_findings: number;
    };
    methodology: string;
  };
  issues: IntelligenceFinding[];
  performance_issues: IntelligenceFinding[];
  recommendations: Recommendation[];
  history: { ts: number; overall: number }[];
}
