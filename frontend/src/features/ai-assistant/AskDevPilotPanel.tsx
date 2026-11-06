"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { AIDisclaimer } from "@/features/ai-assistant/AIDisclaimer";
import { api, type AskDevPilotResponse } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: AskDevPilotResponse["sources"];
  evidenceUsed?: boolean;
  lowConfidence?: boolean;
  error?: string | null;
  timestamp: number;
}

const EXAMPLE_QUESTIONS = [
  "What are the biggest security risks?",
  "Which files are most complex?",
  "What should I fix first?",
  "Explain the architecture.",
  "Where is authentication implemented?",
];

export function AskDevPilotPanel({ owner, repo }: { owner: string; repo: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const canSend = input.trim().length > 0 && !loading;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async (question?: string) => {
    const q = question || input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q, timestamp: Date.now() }]);
    setLoading(true);
    try {
      const res = await api.ai2.ask(owner, repo, q);
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: res.answer,
        sources: res.sources,
        evidenceUsed: res.evidence_used,
        lowConfidence: res.low_confidence,
        error: res.error,
        timestamp: Date.now(),
      }]);
    } catch (err) {
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        error: err instanceof Error ? err.message : "Unknown error",
        timestamp: Date.now(),
      }]);
    } finally {
      setLoading(false);
    }
  }, [owner, repo, input, loading]);

  return (
    <section aria-label="Ask DevPilot">
      <h2 className="text-sm font-semibold mb-2.5">Ask DevPilot</h2>
      <Card padding="none" className="overflow-hidden">
        {messages.length === 0 ? (
          <div className="p-4">
            <p className="text-xs mb-3" style={{ color: "var(--muted-foreground)" }}>Ask anything about your codebase...</p>
            <div className="flex flex-wrap gap-1.5">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="text-[11px] px-2.5 py-1.5 rounded-lg border transition-colors hover:bg-black/[0.03] dark:hover:bg-white/[0.03]"
                  style={{ borderColor: "var(--border)" }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-h-64 overflow-y-auto p-3 space-y-2.5">
            {messages.map((msg, i) => (
              <AskMessage key={i} msg={msg} />
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="rounded-lg px-3 py-2 text-xs" style={{ background: "var(--muted)" }}>
                  <LoadingState message="Thinking..." className="!py-0" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
        <div className="border-t p-2.5" style={{ borderColor: "var(--border)" }}>
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              placeholder="Ask about security, architecture, complexity..."
              disabled={loading}
              className="flex-1 min-w-0 h-9 px-3 text-xs rounded-lg focus:outline-none disabled:opacity-50"
              style={{ background: "var(--input-bg)", border: "1px solid var(--input-border)", color: "var(--input-text)" }}
            />
            <Button onClick={() => handleSend()} disabled={!canSend} size="sm" className="shrink-0 h-9">
              {loading ? "..." : "Ask"}
            </Button>
          </div>
          <AIDisclaimer className="mt-1.5" />
        </div>
      </Card>
    </section>
  );
}

function AskMessage({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[95%] rounded-lg px-3 py-2 text-xs leading-relaxed ${
          isUser
            ? "bg-emerald-600/15 border border-emerald-500/20"
            : msg.error
              ? "bg-red-500/10 border border-red-500/20"
              : "border"
        }`}
        style={!isUser && !msg.error ? { background: "var(--muted)", borderColor: "var(--border)" } : undefined}
      >
        <div className="whitespace-pre-wrap">{msg.content}</div>
        {msg.lowConfidence && (
          <p className="text-[9px] mt-1 italic" style={{ color: "var(--muted-foreground)" }}>
            Low confidence — limited evidence available
          </p>
        )}
        {!isUser && msg.sources && msg.sources.length > 0 && (
          <div className="mt-2 pt-1.5 border-t" style={{ borderColor: "var(--border)" }}>
            <p className="text-[9px] uppercase tracking-wider mb-0.5" style={{ color: "var(--muted-foreground)" }}>Sources</p>
            {msg.sources.slice(0, 3).map((s, i) => (
              <Link
                key={i}
                href={`/code-explorer`}
                className="text-[10px] font-mono block hover:underline"
                style={{ color: "var(--muted-foreground)" }}
              >
                {s.file}{s.line ? `:${s.line}` : ""}
              </Link>
            ))}
            {msg.sources.length > 3 && (
              <p className="text-[9px]" style={{ color: "var(--muted-foreground)" }}>+{msg.sources.length - 3} more</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
