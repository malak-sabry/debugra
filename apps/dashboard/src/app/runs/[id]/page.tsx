"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, Bug, Play, RefreshCw, ExternalLink,
  ChevronRight, AlertTriangle, Info, Zap, Activity, FileDown,
} from "lucide-react";
import { api } from "@/lib/api";
import { RunEventStream } from "@/lib/ws";
import { cn, formatDuration, severityColor, statusColor } from "@/lib/utils";
import type { Run, Finding, Agent, RunEvent } from "@debugra/schemas";

type LogLine = { ts: string; text: string; source: string };

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<Run | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [latestScreenshots, setLatestScreenshots] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<"live" | "findings" | "logs" | "replay">("live");
  const [loading, setLoading] = useState(true);

  const streamRef = useRef<RunEventStream | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  const fetchRun = async () => {
    try {
      const [runData, agentsData, findingsData] = await Promise.all([
        api.runs.get(id),
        api.runs.agents(id),
        api.runs.findings(id),
      ]);
      setRun(runData);
      setAgents(agentsData);
      setFindings(findingsData);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRun();

    const stream = new RunEventStream(id).connect();
    streamRef.current = stream;

    stream.on("*", (event: RunEvent) => {
      const { type, payload, ts } = event;

      if (type === "log_line") {
        setLogs((prev) => [
          ...prev.slice(-499),
          { ts, text: payload.line as string, source: payload.source as string },
        ]);
      }

      if (type === "agent_screenshot") {
        const role = payload.role as string;
        const path = payload.path as string;
        setLatestScreenshots((prev) => ({ ...prev, [role]: path }));
      }

      if (type === "finding_detected") {
        setFindings((prev) => [...prev, payload as unknown as Finding]);
      }

      if (["run_complete", "run_failed", "planning_complete"].includes(type)) {
        fetchRun();
      }
    });

    const pollInterval = setInterval(fetchRun, 10_000);

    return () => {
      stream.disconnect();
      clearInterval(pollInterval);
    };
  }, [id]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-muted-foreground text-sm animate-pulse">Loading run…</div>
      </div>
    );
  }

  const isLive = run && ["running", "planning", "detecting", "reporting"].includes(run.status);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link href="/" className="p-1.5 rounded-lg hover:bg-accent transition-colors">
            <ArrowLeft className="w-4 h-4 text-muted-foreground" />
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
              <Zap className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-foreground uppercase">
                  {run?.sut ?? "Run"}
                </span>
                {run && (
                  <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", statusColor(run.status))}>
                    {run.status}
                  </span>
                )}
                {isLive && <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />}
              </div>
              <p className="text-xs text-muted-foreground font-mono">
                {id.slice(0, 8)} · {run ? formatDuration(run.started_at, run.ended_at) : "—"}
              </p>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {run?.status === "complete" && (
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/runs/${id}/report.pdf`}
                download
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border/40 text-xs text-muted-foreground hover:text-foreground hover:border-border transition-colors"
              >
                <FileDown className="w-3.5 h-3.5" />
                PDF Report
              </a>
            )}
            <button
              onClick={fetchRun}
              className="p-1.5 rounded-lg hover:bg-accent transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-6 flex gap-1 -mb-px">
          {(["live", "findings", "logs", "replay"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors capitalize",
                activeTab === tab
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {tab}
              {tab === "findings" && findings.length > 0 && (
                <span className="ml-1.5 text-xs bg-orange-500/20 text-orange-400 px-1.5 py-0.5 rounded-full">
                  {findings.length}
                </span>
              )}
            </button>
          ))}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {activeTab === "live" && (
          <LiveTab agents={agents} latestScreenshots={latestScreenshots} run={run} />
        )}
        {activeTab === "findings" && (
          <FindingsTab findings={findings} />
        )}
        {activeTab === "logs" && (
          <LogsTab logs={logs} logEndRef={logEndRef} />
        )}
        {activeTab === "replay" && (
          <ReplayTab agents={agents} runId={id} />
        )}
      </main>
    </div>
  );
}

// ─── Live Tab ─────────────────────────────────────────────────────────────────

function LiveTab({
  agents,
  latestScreenshots,
  run,
}: {
  agents: Agent[];
  latestScreenshots: Record<string, string>;
  run: Run | null;
}) {
  if (agents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center space-y-3">
        <Activity className="w-10 h-10 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">
          {run?.status === "planning" ? "AI is reading documentation and planning test flows…" : "Waiting for agents to spawn…"}
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {agents.map((agent) => (
        <AgentTile
          key={agent.id}
          agent={agent}
          screenshotPath={latestScreenshots[agent.role]}
        />
      ))}
    </div>
  );
}

function AgentTile({ agent, screenshotPath }: { agent: Agent; screenshotPath?: string }) {
  const isLive = agent.status === "running";

  return (
    <div
      className={cn(
        "rounded-xl border bg-card/30 overflow-hidden transition-all",
        isLive ? "border-indigo-500/40 live-ring" : "border-border/40"
      )}
    >
      {/* Screenshot */}
      <div className="relative aspect-video bg-background/50 flex items-center justify-center">
        {screenshotPath ? (
          <img
            src={`/api/artifacts/${encodeURIComponent(screenshotPath)}`}
            alt={`${agent.role} screenshot`}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="text-muted-foreground/30 text-xs">No screenshot yet</div>
        )}
        {isLive && (
          <span className="absolute top-2 right-2 text-xs px-2 py-0.5 bg-indigo-600/80 text-white rounded-full font-medium backdrop-blur-sm">
            LIVE
          </span>
        )}
      </div>
      {/* Info */}
      <div className="px-4 py-3 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground capitalize">{agent.role}</span>
            <span className={cn("text-xs px-1.5 py-0.5 rounded-full", statusColor(agent.status))}>
              {agent.status}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Step {agent.step_count}
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Findings Tab ──────────────────────────────────────────────────────────────

function FindingsTab({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <Bug className="w-10 h-10 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">No findings yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {findings.map((f) => (
        <FindingCard key={f.id} finding={f} />
      ))}
    </div>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-xl border border-border/40 bg-card/30 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full px-5 py-4 flex items-center gap-4 text-left hover:bg-card/50 transition-colors"
      >
        <span className={cn("text-xs px-2 py-0.5 rounded border font-medium shrink-0", severityColor(finding.severity))}>
          {finding.severity}
        </span>
        <span className="text-sm font-medium text-foreground flex-1">{finding.title}</span>
        <span className="text-xs text-muted-foreground shrink-0">{finding.oracle_type}</span>
        <ChevronRight className={cn("w-4 h-4 text-muted-foreground transition-transform shrink-0", open && "rotate-90")} />
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4 border-t border-border/30">
          <p className="text-sm text-muted-foreground pt-4">{finding.description}</p>

          {finding.repro_steps.length > 0 && (
            <div>
              <p className="text-xs font-medium text-foreground mb-2">Reproduction Steps</p>
              <ol className="space-y-1">
                {finding.repro_steps.map((step, i) => (
                  <li key={i} className="text-xs text-muted-foreground flex gap-2">
                    <span className="text-indigo-400 shrink-0">{i + 1}.</span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {finding.evidence_paths.length > 0 && (
            <div>
              <p className="text-xs font-medium text-foreground mb-2">Evidence</p>
              <div className="grid grid-cols-2 gap-2">
                {finding.evidence_paths.map((p, i) => (
                  <img
                    key={i}
                    src={`/api/artifacts/${encodeURIComponent(p)}`}
                    alt={`Evidence ${i + 1}`}
                    className="rounded-lg border border-border/40 w-full aspect-video object-cover bg-background"
                  />
                ))}
              </div>
            </div>
          )}

          {finding.ground_truth_bug_id && (
            <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-400/10 rounded-lg px-3 py-2">
              <Info className="w-3.5 h-3.5 shrink-0" />
              Matches seeded bug: <span className="font-mono font-medium">{finding.ground_truth_bug_id}</span>
            </div>
          )}

          {finding.oracle_type === "llm_unverified" && (
            <div className="flex items-center gap-2 text-xs text-yellow-400 bg-yellow-400/10 rounded-lg px-3 py-2">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              Unverified — requires human confirmation
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Logs Tab ──────────────────────────────────────────────────────────────────

function LogsTab({
  logs,
  logEndRef,
}: {
  logs: LogLine[];
  logEndRef: React.RefObject<HTMLDivElement | null>;
}) {
  return (
    <div className="rounded-xl border border-border/40 bg-black/30 h-[600px] overflow-y-auto p-4 font-mono text-xs space-y-1">
      {logs.length === 0 ? (
        <p className="text-muted-foreground/50">Waiting for logs…</p>
      ) : (
        logs.map((log, i) => (
          <div key={i} className="flex gap-3 items-start">
            <span className="text-muted-foreground/40 shrink-0 select-none">
              {log.ts.slice(11, 19)}
            </span>
            <span
              className={cn(
                log.text.includes("error") || log.text.includes("ERROR")
                  ? "text-red-400"
                  : log.text.includes("WARN")
                  ? "text-yellow-400"
                  : "text-slate-300"
              )}
            >
              {log.text}
            </span>
          </div>
        ))
      )}
      <div ref={logEndRef} />
    </div>
  );
}

// ─── Replay Tab ────────────────────────────────────────────────────────────────

function ReplayTab({ agents, runId }: { agents: Agent[]; runId: string }) {
  const agentsWithTrace = agents.filter((a) => a.trace_path);

  if (agentsWithTrace.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <Play className="w-10 h-10 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">No traces available yet</p>
        <p className="text-xs text-muted-foreground/60">Traces are saved when agents complete</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        Open a trace in Playwright Trace Viewer. Run{" "}
        <code className="bg-card px-1.5 py-0.5 rounded text-indigo-300">
          npx playwright show-trace &lt;path&gt;
        </code>{" "}
        to view locally.
      </p>
      {agentsWithTrace.map((a) => (
        <div
          key={a.id}
          className="flex items-center justify-between px-5 py-4 rounded-xl border border-border/40 bg-card/30"
        >
          <div>
            <p className="text-sm font-medium text-foreground capitalize">{a.role}</p>
            <p className="text-xs text-muted-foreground font-mono mt-0.5">{a.trace_path}</p>
          </div>
          <a
            href={`/api/artifacts/${encodeURIComponent(a.trace_path ?? "")}`}
            download
            className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Download
          </a>
        </div>
      ))}
    </div>
  );
}
