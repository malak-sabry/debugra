"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PlusCircle, Activity, CheckCircle2, XCircle, Clock, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { formatDuration, statusColor } from "@/lib/utils";
import type { Run } from "@debugra/schemas";
import { NewRunModal } from "@/components/new-run-modal";

export default function HomePage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const fetchRuns = async () => {
    try {
      const data = await api.runs.list();
      setRuns(data);
    } catch {
      // orchestrator may not be running yet
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, []);

  const stats = {
    total: runs.length,
    complete: runs.filter((r) => r.status === "complete").length,
    running: runs.filter((r) => ["running", "planning", "detecting", "reporting"].includes(r.status)).length,
    failed: runs.filter((r) => r.status === "failed").length,
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
              <Zap className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-foreground">Debugra</h1>
              <p className="text-xs text-muted-foreground">Autonomous AI QA</p>
            </div>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
          >
            <PlusCircle className="w-4 h-4" />
            New Run
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={<Activity className="w-4 h-4" />} label="Total Runs" value={stats.total} color="text-foreground" />
          <StatCard icon={<CheckCircle2 className="w-4 h-4" />} label="Complete" value={stats.complete} color="text-emerald-400" />
          <StatCard icon={<Clock className="w-4 h-4" />} label="Running" value={stats.running} color="text-indigo-400" />
          <StatCard icon={<XCircle className="w-4 h-4" />} label="Failed" value={stats.failed} color="text-red-400" />
        </div>

        {/* Runs list */}
        <section>
          <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-4">
            Recent Runs
          </h2>

          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 rounded-lg bg-card/50 animate-pulse" />
              ))}
            </div>
          ) : runs.length === 0 ? (
            <EmptyState onNew={() => setShowModal(true)} />
          ) : (
            <div className="space-y-2">
              {runs.map((run) => (
                <RunRow key={run.id} run={run} />
              ))}
            </div>
          )}
        </section>
      </main>

      {showModal && (
        <NewRunModal
          onClose={() => setShowModal(false)}
          onCreated={(runId) => {
            setShowModal(false);
            window.location.href = `/runs/${runId}`;
          }}
        />
      )}
    </div>
  );
}

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number; color: string }) {
  return (
    <div className="rounded-xl border border-border/40 bg-card/30 p-4 space-y-2">
      <div className={`flex items-center gap-2 ${color}`}>
        {icon}
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
      </div>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function RunRow({ run }: { run: Run }) {
  const isLive = ["running", "planning", "detecting", "reporting"].includes(run.status);

  return (
    <Link href={`/runs/${run.id}`}>
      <div className="group flex items-center justify-between px-5 py-4 rounded-xl border border-border/40 bg-card/30 hover:bg-card/60 hover:border-indigo-500/30 transition-all cursor-pointer">
        <div className="flex items-center gap-4">
          {isLive && (
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          )}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm text-foreground uppercase">{run.sut}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColor(run.status)}`}>
                {run.status}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {run.id.slice(0, 8)} · {new Date(run.created_at).toLocaleString()}
            </p>
          </div>
        </div>
        <span className="text-xs text-muted-foreground">
          {formatDuration(run.started_at, run.ended_at)}
        </span>
      </div>
    </Link>
  );
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center space-y-4">
      <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
        <Zap className="w-8 h-8 text-indigo-400" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-foreground">No runs yet</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Start your first autonomous QA run.
        </p>
      </div>
      <button
        onClick={onNew}
        className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
      >
        Start First Run
      </button>
    </div>
  );
}
