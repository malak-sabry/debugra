import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(startedAt: string | null, endedAt: string | null): string {
  if (!startedAt) return "—";
  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : Date.now();
  const ms = end - start;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}m ${remaining}s`;
}

export function severityColor(severity: string): string {
  switch (severity) {
    case "critical": return "text-red-400 bg-red-400/10 border-red-400/20";
    case "high": return "text-orange-400 bg-orange-400/10 border-orange-400/20";
    case "medium": return "text-yellow-400 bg-yellow-400/10 border-yellow-400/20";
    case "low": return "text-blue-400 bg-blue-400/10 border-blue-400/20";
    default: return "text-slate-400 bg-slate-400/10 border-slate-400/20";
  }
}

export function statusColor(status: string): string {
  switch (status) {
    case "complete": return "text-emerald-400 bg-emerald-400/10";
    case "running": return "text-indigo-400 bg-indigo-400/10";
    case "planning": return "text-purple-400 bg-purple-400/10";
    case "detecting": return "text-cyan-400 bg-cyan-400/10";
    case "reporting": return "text-teal-400 bg-teal-400/10";
    case "failed": return "text-red-400 bg-red-400/10";
    case "pending": return "text-slate-400 bg-slate-400/10";
    default: return "text-slate-400 bg-slate-400/10";
  }
}
