"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { useAuth } from "@/lib/auth-context";
import { api, type GitHubRepo, type Branch, type AnalysisJob } from "@/lib/api";
import { languageColor } from "@/lib/utils";
import { AnalysisProgress } from "./AnalysisProgress";

export function RepositoriesView() {
  const { user } = useAuth();
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepo | null>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selectedBranch, setSelectedBranch] = useState<string>("");
  const [branchesLoading, setBranchesLoading] = useState(false);
  const [activeJob, setActiveJob] = useState<AnalysisJob | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const mountedRef = useRef(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    if (user) {
      const load = async () => {
        try {
          setLoading(true);
          setError(null);
          const data = await api.repositories.list();
          if (mountedRef.current) setRepos(data.repositories);
        } catch (err) {
          if (mountedRef.current) {
            setError(err instanceof Error ? err.message : "Failed to load repositories");
          }
        } finally {
          if (mountedRef.current) setLoading(false);
        }
      };
      void load();
    }
    return () => { mountedRef.current = false; };
  }, [user]);

  const fetchRepos = useCallback(async (query?: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.repositories.list(query || undefined);
      if (mountedRef.current) setRepos(data.repositories);
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : "Failed to load repositories");
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  const handleSearch = (value: string) => {
    setSearch(value);
    void fetchRepos(value || undefined);
  };

  const handleSelectRepo = async (repo: GitHubRepo) => {
    setSelectedRepo(repo);
    setSelectedBranch(repo.default_branch);
    setBranchesLoading(true);
    setActiveJob(null);
    try {
      const [owner, repoName] = repo.full_name.split("/");
      const data = await api.repositories.getBranches(owner, repoName);
      if (mountedRef.current) setBranches(data.branches);
    } catch {
      if (mountedRef.current) setBranches([]);
    } finally {
      if (mountedRef.current) setBranchesLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!selectedRepo) return;
    const [owner, repoName] = selectedRepo.full_name.split("/");
    setAnalyzing(true);
    setActiveJob(null);
    try {
      const data = await api.analysis.start(owner, repoName, selectedBranch);
      const jobId = data.job_id;

      const poll = setInterval(async () => {
        try {
          const status = await api.analysis.getStatus(jobId);
          if (mountedRef.current) setActiveJob(status.job);
          if (status.job.status === "completed" || status.job.status === "failed") {
            clearInterval(poll);
            if (mountedRef.current) setAnalyzing(false);
            if (status.job.status === "completed") {
              void api.graph.build(owner, repoName).catch(() => {});
            }
          }
        } catch {
          clearInterval(poll);
          if (mountedRef.current) setAnalyzing(false);
        }
      }, 800);

      pollRef.current = poll;
    } catch (err) {
      if (mountedRef.current) {
        setActiveJob({
          id: "error",
          owner: "",
          repo: "",
          branch: "",
          status: "failed",
          progress: 0,
          message: "Failed to start analysis",
          total_files: 0,
          filtered_files: 0,
          files: [],
          error: err instanceof Error ? err.message : "Unknown error",
        });
        setAnalyzing(false);
      }
    }
  };

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  if (!user) {
    return (
      <div className="p-4 sm:p-6 max-w-7xl">
        <EmptyState
          icon="&#x2728;"
          title="Connect your GitHub account"
          description="Link your GitHub account to browse and analyze your repositories."
          action={
            <a
              href={api.auth.getGithubUrl()}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 transition-colors"
            >
              Connect GitHub
            </a>
          }
        />
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight">Repositories</h1>
        <p className="text-sm mt-1" style={{ color: "var(--muted-foreground)" }}>
          Select a repository to analyze
        </p>
      </div>

      <div className="flex gap-2 sm:gap-3">
        <div className="relative flex-1 max-w-md min-w-0">
          <input
            type="text"
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search repositories..."
            className="w-full h-10 pl-9 pr-3 text-sm rounded-lg border focus:outline-none focus:border-[var(--border-hover)] transition-colors"
            style={{ background: "var(--input-bg)", borderColor: "var(--input-border)", color: "var(--input-text)" }}
          />
          <svg className="absolute left-2.5 top-2.5 h-4 w-4" style={{ color: "var(--muted-foreground)" }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
        </div>
        <Button variant="secondary" size="sm" onClick={() => void fetchRepos(search || undefined)} className="h-10 shrink-0">
          Refresh
        </Button>
      </div>

      {loading ? (
        <LoadingState message="Loading repositories..." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void fetchRepos()} />
      ) : repos.length === 0 ? (
        <EmptyState
          icon="&#x2630;"
          title="No repositories found"
          description={search ? "No repositories match your search." : "No repositories found in your GitHub account."}
        />
      ) : (
        <div className="space-y-3">
          {repos.map((repo) => (
            <Card
              key={repo.id}
              padding="sm"
              className={selectedRepo?.id === repo.id ? "border-emerald-500/50 bg-emerald-500/5" : ""}
              onClick={() => void handleSelectRepo(repo)}
            >
              <div className="flex items-start gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2.5">
                    <h3 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>{repo.name}</h3>
                    {repo.private && (
                      <Badge variant="default">Private</Badge>
                    )}
                  </div>
                  <p className="text-xs mt-1" style={{ color: "var(--muted-foreground)" }}>{repo.full_name}</p>
                  {repo.description && (
                    <p className="text-xs mt-1.5 line-clamp-1" style={{ color: "var(--muted-foreground)" }}>{repo.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 sm:gap-4 shrink-0 text-xs flex-wrap justify-end" style={{ color: "var(--muted-foreground)" }}>
                  <div className="flex items-center gap-1.5">
                    <div className={`h-2.5 w-2.5 rounded-full ${languageColor(repo.language)}`} />
                    {repo.language}
                  </div>
                  <span>&#x2605; {repo.stars.toLocaleString()}</span>
                  <span>{repo.forks} forks</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {selectedRepo && (
        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>{selectedRepo.full_name}</h2>
              <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>{selectedRepo.description}</p>
            </div>
            {selectedRepo.owner.avatar_url && (
              <Image
                src={selectedRepo.owner.avatar_url}
                alt={selectedRepo.owner.login}
                width={32}
                height={32}
                className="rounded-full"
                unoptimized
              />
            )}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div>
              <p style={{ color: "var(--muted-foreground)" }}>Language</p>
              <p className="mt-0.5" style={{ color: "var(--foreground)" }}>{selectedRepo.language}</p>
            </div>
            <div>
              <p style={{ color: "var(--muted-foreground)" }}>Stars</p>
              <p className="mt-0.5" style={{ color: "var(--foreground)" }}>{selectedRepo.stars.toLocaleString()}</p>
            </div>
            <div>
              <p style={{ color: "var(--muted-foreground)" }}>Forks</p>
              <p className="mt-0.5" style={{ color: "var(--foreground)" }}>{selectedRepo.forks}</p>
            </div>
            <div>
              <p style={{ color: "var(--muted-foreground)" }}>Visibility</p>
              <p className="mt-0.5" style={{ color: "var(--foreground)" }}>{selectedRepo.private ? "Private" : "Public"}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2 border-t" style={{ borderColor: "var(--border)" }}>
            <div className="flex-1">
              <label className="text-xs mb-1 block" style={{ color: "var(--muted-foreground)" }}>Branch</label>
              {branchesLoading ? (
                <div className="h-9 rounded-lg animate-pulse" style={{ background: "var(--muted)" }} />
              ) : (
                <select
                  value={selectedBranch}
                  onChange={(e) => setSelectedBranch(e.target.value)}
                  disabled={analyzing}
                  className="w-full h-9 px-3 text-sm rounded-lg border focus:outline-none focus:border-[var(--border-hover)] disabled:opacity-50"
                  style={{ background: "var(--input-bg)", borderColor: "var(--input-border)", color: "var(--input-text)" }}
                >
                  {branches.map((b) => (
                    <option key={b.name} value={b.name}>
                      {b.name} {b.is_default ? "(default)" : ""}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="pt-5">
              <Button onClick={() => void handleAnalyze()} disabled={analyzing}>
                {analyzing ? "Analyzing..." : "Analyze Repository"}
              </Button>
            </div>
          </div>
        </Card>
      )}

      {activeJob && <AnalysisProgress job={activeJob} />}
    </div>
  );
}
