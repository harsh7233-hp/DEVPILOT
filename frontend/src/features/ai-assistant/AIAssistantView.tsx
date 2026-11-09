"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { RepoSelector } from "@/components/ui/RepoSelector";
import { LoadingState } from "@/components/ui/LoadingState";
import { AIDisclaimer } from "@/features/ai-assistant/AIDisclaimer";
import { api } from "@/lib/api";

interface Source { file: string; line: string; entity?: string; }

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  error?: string | null;
  timestamp: number;
}

const WELCOME: ChatMessage = {
  role: "assistant",
  content: "Hello! I'm the DevPilot AI assistant. I can help you understand your codebase, explain dependencies, and analyze the impact of changes.\n\nSelect a repository above, then ask a question.",
  timestamp: Date.now(),
};

export function AIAssistantView() {
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [repoValue, setRepoValue] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const graphReadyRef = useRef<Set<string>>(new Set());

  const canSend = owner.trim().length > 0 && repo.trim().length > 0 && input.trim().length > 0 && !loading;

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const handleRepoSelect = (o: string, r: string) => {
    setOwner(o);
    setRepo(r);
    setRepoValue(`${o}/${r}`);
  };

  const handleSend = useCallback(async () => {
    if (!canSend) return;
    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question, timestamp: Date.now() }]);
    setLoading(true);
    try {
      const key = `${owner.trim()}/${repo.trim()}`;
      if (!graphReadyRef.current.has(key)) {
        const existing = await api.graph.getNodes(owner.trim(), repo.trim());
        if (existing.nodes.length === 0) {
          await api.graph.build(owner.trim(), repo.trim());
        }
        graphReadyRef.current.add(key);
      }
      const res = await api.ai.chat(owner.trim(), repo.trim(), question);
      setMessages((prev) => [...prev, { role: "assistant", content: res.answer, sources: res.sources, error: res.error, timestamp: Date.now() }]);
    } catch (err) {
      const raw = err instanceof Error ? err.message : "Unknown error";
      const message = /no completed analysis|graph not found/i.test(raw)
        ? "This repository has no analysis graph yet. Open Repositories, run Analyze, wait for it to complete, then ask again."
        : raw;
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${message}`, error: message, timestamp: Date.now() }]);
    } finally { setLoading(false); }
  }, [canSend, input, owner, repo]);

  const handleClear = useCallback(async () => {
    if (owner.trim() && repo.trim()) {
      try { await api.ai.clearHistory(owner.trim(), repo.trim()); } catch { /* ignore */ }
    }
    setMessages([WELCOME]);
  }, [owner, repo]);

  return (
    <div className="flex flex-col h-full">
      <div className="border-b px-3 sm:px-6 py-3" style={{ borderColor: "var(--border)" }}>
        <div className="max-w-3xl mx-auto flex items-center gap-2 sm:gap-3">
          <RepoSelector value={repoValue} onChange={handleRepoSelect} className="flex-1 min-w-0" />
          <Button variant="ghost" size="sm" onClick={handleClear} className="shrink-0">Clear</Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 sm:p-6 overscroll-contain">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}
          {loading && (
            <div className="flex justify-start">
              <div className="rounded-xl px-4 py-3" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                <LoadingState message="Thinking..." className="!py-0" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="border-t p-3 sm:p-4" style={{ borderColor: "var(--border)" }}>
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              placeholder={!owner.trim() || !repo.trim() ? "Select a repository above first..." : "Ask about your codebase..."}
              disabled={loading}
              enterKeyHint="send"
              className="flex-1 min-w-0 h-11 sm:h-10 px-4 text-sm rounded-lg focus:outline-none focus:border-zinc-500 disabled:opacity-50"
              style={{ background: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--input-text)" }}
            />
            <Button onClick={handleSend} disabled={!canSend} className="shrink-0">{loading ? "..." : "Send"}</Button>
          </div>
          <AIDisclaimer className="mt-2" />
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[92%] sm:max-w-[85%] rounded-xl px-3.5 sm:px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-emerald-600/20 text-emerald-900 dark:text-emerald-100 border border-emerald-500/20"
            : msg.error
              ? "bg-red-500/10 text-red-600 dark:text-red-300 border border-red-500/20"
              : "border"
        }`}
        style={!isUser && !msg.error ? { background: "var(--card)", borderColor: "var(--border)", color: "var(--foreground)" } : undefined}
      >
        <div className="whitespace-pre-wrap">{msg.content}</div>
        {!isUser && msg.sources && msg.sources.length > 0 && <SourcesList sources={msg.sources} />}
      </div>
    </div>
  );
}

function SourcesList({ sources }: { sources: Source[] }) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? sources : sources.slice(0, 3);
  return (
    <div className="mt-3 pt-2" style={{ borderTop: "1px solid var(--border)" }}>
      <p className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "var(--muted-foreground)" }}>Sources</p>
      <div className="space-y-1">
        {shown.map((s, i) => (
          <div key={i} className="flex items-center gap-1.5 text-[11px] font-mono" style={{ color: "var(--muted-foreground)" }}>
            <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <span>{s.file}</span>
            {s.line && <span className="text-zinc-500">:{s.line}</span>}
            {s.entity && <span className="text-zinc-500">({s.entity})</span>}
          </div>
        ))}
      </div>
      {sources.length > 3 && (
        <button onClick={() => setExpanded(!expanded)} className="text-[10px] mt-1 transition-colors" style={{ color: "var(--muted-foreground)" }}>
          {expanded ? "Show less" : `+${sources.length - 3} more`}
        </button>
      )}
    </div>
  );
}
