"use client";

import { useState, useCallback } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { RepoSelector } from "@/components/ui/RepoSelector";
import { api } from "@/lib/api";

type SearchMode = "browse" | "semantic";

interface SearchResult {
  file: string;
  entity: string;
  kind: string;
  snippet: string;
  start_line: number;
  end_line: number;
  score: number;
}

const mockFiles: Record<string, string> = {
  "src/services/auth.ts": `import { TokenRepository } from '../repositories/token';
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
}`,
  "src/middleware/auth.ts": `import { validateToken } from '../services/auth';
import { Request, Response, NextFunction } from 'express';

export async function AuthMiddleware(
  req: Request,
  res: Response,
  next: NextFunction
) {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }

  const isValid = await validateToken(token);
  if (!isValid) {
    return res.status(401).json({ error: 'Invalid token' });
  }

  next();
}`,
  "src/repositories/token.ts": `interface TokenPayload {
  userId: string;
  iat: number;
  exp: number;
}

export const TokenRepository = {
  decode(token: string): TokenPayload | null {
    try {
      return JSON.parse(Buffer.from(token.split('.')[1], 'base64').toString());
    } catch {
      return null;
    }
  },

  isValid(payload: TokenPayload): boolean {
    return payload.exp > Date.now() / 1000;
  },

  generate(userId: string): string {
    const payload: TokenPayload = {
      userId,
      iat: Date.now() / 1000,
      exp: Date.now() / 1000 + 3600,
    };
    return Buffer.from(JSON.stringify(payload)).toString('base64');
  },
};`,
  "src/repositories/user.ts": `export interface User {
  id: string;
  email: string;
  name: string;
  status: 'active' | 'inactive';
  createdAt: Date;
}

const users: User[] = [
  { id: '1', email: 'john@example.com', name: 'John Doe', status: 'active', createdAt: new Date() },
];

export const UserRepository = {
  async findById(id: string): Promise<User | undefined> {
    return users.find(u => u.id === id);
  },

  async findByEmail(email: string): Promise<User | undefined> {
    return users.find(u => u.email === email);
  },
};`,
};

const fileTree = [
  {
    name: "src",
    children: [
      { name: "api", children: [{ name: "auth.ts" }, { name: "user.ts" }] },
      { name: "middleware", children: [{ name: "auth.ts" }] },
      { name: "repositories", children: [{ name: "token.ts" }, { name: "user.ts" }] },
      { name: "services", children: [{ name: "auth.ts" }] },
    ],
  },
];

export function CodeExplorerView() {
  const [mode, setMode] = useState<SearchMode>("browse");
  const [selectedFile, setSelectedFile] = useState("src/services/auth.ts");
  const [treeOpen, setTreeOpen] = useState(false);
  const content = mockFiles[selectedFile] ?? "// Select a file from the tree";

  return (
    <div className="flex h-full relative">
      {/* Mobile tree overlay */}
      {treeOpen && (
        <>
          <div className="lg:hidden fixed inset-0 z-30 bg-black/40" onClick={() => setTreeOpen(false)} />
          <div className="lg:hidden absolute inset-y-0 left-0 z-40 w-64 max-w-[80vw] border-r border-[var(--sidebar-border)] bg-[var(--sidebar-bg)] overflow-y-auto shadow-xl">
            <MobileSidebarContent
              mode={mode}
              setMode={setMode}
              selectedFile={selectedFile}
              setSelectedFile={(f) => {
                setSelectedFile(f);
                setTreeOpen(false);
              }}
            />
          </div>
        </>
      )}

      {/* Left sidebar (desktop) */}
      <div className="hidden lg:block w-56 border-r border-[var(--sidebar-border)] bg-[var(--sidebar-bg)] overflow-y-auto shrink-0">
        <SidebarContent
          mode={mode}
          setMode={setMode}
          selectedFile={selectedFile}
          setSelectedFile={setSelectedFile}
        />
      </div>

      {/* Code panel */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="h-11 sm:h-10 border-b border-[var(--border)] flex items-center gap-2 px-2 sm:px-4 bg-[var(--card)] shrink-0">
          {/* Mobile files toggle */}
          <button
            onClick={() => setTreeOpen(true)}
            aria-label="Open file browser"
            className="lg:hidden h-8 w-9 shrink-0 flex items-center justify-center rounded-lg transition-colors active:bg-[var(--muted)]"
            style={{ color: "var(--muted-foreground)" }}
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.6} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
            </svg>
          </button>
          <span className="text-xs font-mono text-[var(--muted-foreground)] truncate">{selectedFile}</span>
        </div>
        <div className="flex-1 overflow-auto bg-[var(--background)]">
          <pre className="p-3 sm:p-4 text-xs sm:text-sm font-mono text-[var(--foreground)] leading-6 whitespace-pre">
            {content}
          </pre>
        </div>
      </div>

      {/* Right sidebar */}
      <div className="w-64 border-l border-[var(--sidebar-border)] p-4 overflow-y-auto shrink-0 hidden xl:block">
        <p className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-3">
          File Info
        </p>
        <Card padding="sm" className="space-y-3">
          <div>
            <p className="text-xs text-[var(--muted-foreground)]">Path</p>
            <p className="text-xs text-[var(--foreground)] font-mono mt-0.5 break-all">{selectedFile}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--muted-foreground)]">Language</p>
            <p className="text-xs text-[var(--foreground)] mt-0.5">TypeScript</p>
          </div>
          <div>
            <p className="text-xs text-[var(--muted-foreground)]">Lines</p>
            <p className="text-xs text-[var(--foreground)] mt-0.5">{content.split("\n").length}</p>
          </div>
        </Card>
      </div>
    </div>
  );
}

function SidebarContent({
  mode,
  setMode,
  selectedFile,
  setSelectedFile,
}: {
  mode: SearchMode;
  setMode: (m: SearchMode) => void;
  selectedFile: string;
  setSelectedFile: (f: string) => void;
}) {
  return (
    <>
      {/* Mode tabs */}
      <div className="flex border-b border-[var(--sidebar-border)]">
        <button
          onClick={() => setMode("browse")}
          className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
            mode === "browse"
              ? "text-[var(--foreground)] border-b-2 border-emerald-500"
              : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
          }`}
        >
          Browse
        </button>
        <button
          onClick={() => setMode("semantic")}
          className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
            mode === "semantic"
              ? "text-[var(--foreground)] border-b-2 border-emerald-500"
              : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
          }`}
        >
          Semantic
        </button>
      </div>

      {mode === "browse" ? (
        <div className="p-3">
          <p className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-3 px-2">
            Files
          </p>
          <FileTree items={fileTree} onSelect={setSelectedFile} selected={selectedFile} />
        </div>
      ) : (
        <SemanticSearchPanel onSelectFile={setSelectedFile} />
      )}
    </>
  );
}

function MobileSidebarContent(props: Parameters<typeof SidebarContent>[0]) {
  return (
    <div className="flex flex-col h-full">
      <SidebarContent {...props} />
    </div>
  );
}

function SemanticSearchPanel({ onSelectFile }: { onSelectFile: (file: string) => void }) {
  const [repoValue, setRepoValue] = useState("");
  const [owner = "", repo = ""] = repoValue.split("/");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [totalIndexed, setTotalIndexed] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const canSearch = owner.trim().length > 0 && repo.trim().length > 0 && query.trim().length > 0 && !loading;

  const handleSearch = async () => {
    if (!canSearch) return;
    setLoading(true);
    setError(null);
    setSearched(true);

    try {
      const res = await api.search.semantic(owner.trim(), repo.trim(), query.trim());
      setResults(res.results);
      setTotalIndexed(res.total_indexed);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Search failed";
      setError(msg);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenResult = useCallback(
    (result: SearchResult) => {
      onSelectFile(result.file);
    },
    [onSelectFile]
  );

  return (
    <div className="p-3 space-y-3">
      {/* Repo selector */}
      <RepoSelector
        value={repoValue}
        onChange={(nextOwner, nextRepo) => setRepoValue(`${nextOwner}/${nextRepo}`)}
        className="[&>button]:h-8 [&>button]:text-xs"
      />

      {/* Search input */}
      <div className="flex gap-1.5">
        <input
          type="text"
          placeholder="Search by meaning..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="flex-1 h-8 px-2.5 text-xs rounded-lg bg-[var(--input-bg)] border border-[var(--input-border)] text-[var(--input-text)] placeholder-[var(--input-placeholder)] focus:outline-none focus:border-[var(--accent-text)]"
        />
        <Button size="sm" onClick={handleSearch} disabled={!canSearch} className="!px-2.5 !h-8 !text-xs">
          {loading ? "..." : "Go"}
        </Button>
      </div>

      {/* Loading */}
      {loading && <LoadingState message="Searching..." className="!py-6" />}

      {/* Error */}
      {error && (
        <p className="text-xs text-red-400 bg-red-500/10 rounded-lg px-3 py-2">{error}</p>
      )}

      {/* Results */}
      {!loading && !error && searched && results.length === 0 && (
        <p className="text-xs text-[var(--muted-foreground)] py-4 text-center">No results found</p>
      )}

      {results.length > 0 && (
        <div className="space-y-1">
          <p className="text-[10px] text-[var(--muted-foreground)] uppercase tracking-wider">
            {results.length} results ({totalIndexed} indexed)
          </p>
          {results.map((r, i) => (
            <button
              key={i}
              onClick={() => handleOpenResult(r)}
              className="w-full text-left p-2 rounded-lg bg-[var(--muted)] hover:bg-[var(--input-bg)] border border-[var(--border)] hover:border-[var(--input-border)] transition-colors"
            >
              <div className="flex items-center gap-1.5 mb-1">
                <KindBadge kind={r.kind} />
                <span className="text-[10px] font-mono text-[var(--foreground)] truncate">{r.entity}</span>
                <span className="ml-auto text-[10px] text-[var(--muted-foreground)]">{Math.round(r.score * 100)}%</span>
              </div>
              <p className="text-[10px] font-mono text-[var(--muted-foreground)] truncate">{r.file}:{r.start_line}</p>
              <pre className="text-[10px] text-[var(--muted-foreground)] font-mono mt-1 max-h-16 overflow-hidden leading-relaxed">
                {r.snippet.slice(0, 200)}
              </pre>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function KindBadge({ kind }: { kind: string }) {
  const colors: Record<string, string> = {
    function: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    class: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    method: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    imports: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
    file: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  };
  return (
    <span className={`text-[9px] px-1 py-0.5 rounded border font-medium ${colors[kind] || colors.file}`}>
      {kind}
    </span>
  );
}

function FileTree({
  items,
  onSelect,
  selected,
  parentPath = "",
  depth = 0,
}: {
  items: { name: string; children?: { name: string }[] }[];
  onSelect: (path: string) => void;
  selected: string;
  parentPath?: string;
  depth?: number;
}) {
  return (
    <div>
      {items.map((item) => {
        const currentPath = parentPath ? `${parentPath}/${item.name}` : item.name;
        return (
          <div key={item.name}>
            {item.children ? (
              <>
                <p
                  className="text-xs text-[var(--foreground)] font-medium px-2 py-1"
                  style={{ paddingLeft: `${depth * 12 + 8}px` }}
                >
                  {item.name}
                </p>
                <FileTree
                  items={item.children}
                  onSelect={onSelect}
                  selected={selected}
                  parentPath={currentPath}
                  depth={depth + 1}
                />
              </>
            ) : (
              <button
                onClick={() => onSelect(`src/${currentPath}`)}
                className={`w-full text-left text-xs px-2 py-1 rounded transition-colors ${
                  selected.includes(item.name)
                    ? "bg-[var(--muted)] text-[var(--foreground)]"
                    : "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--muted)]"
                }`}
                style={{ paddingLeft: `${depth * 12 + 8}px` }}
              >
                {item.name}
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
