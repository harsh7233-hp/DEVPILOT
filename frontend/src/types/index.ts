export interface Repository {
  id: string;
  name: string;
  fullName: string;
  description: string;
  language: string;
  stars: number;
  forks: number;
  lastAnalyzed: string | null;
  status: "analyzed" | "pending" | "error";
  entityCount: number;
  relationshipCount: number;
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

export interface AnalysisFile {
  path: string;
  size: number;
  sha: string;
  language: string;
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
  files: AnalysisFile[];
  error: string | null;
}

export interface CodeEntity {
  id: string;
  name: string;
  type: "function" | "class" | "interface" | "module" | "api_route" | "variable";
  filePath: string;
  startLine: number;
  endLine: number;
  dependencies: string[];
}

export interface ImpactResult {
  entity: CodeEntity;
  directImpacts: CodeEntity[];
  indirectImpacts: CodeEntity[];
  riskScore: number;
  riskLevel: "low" | "medium" | "high" | "critical";
  affectedFiles: string[];
  summary: string;
}

export interface ActivityItem {
  id: string;
  type: "analysis" | "impact" | "review";
  title: string;
  repository: string;
  timestamp: string;
  status: "completed" | "running" | "failed";
}

export interface NavItem {
  label: string;
  href: string;
  icon: string;
}
