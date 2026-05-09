import type { Run, Finding, Agent } from "@debugra/schemas";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  runs: {
    list: () => apiFetch<Run[]>("/api/runs"),
    get: (id: string) => apiFetch<Run>(`/api/runs/${id}`),
    create: (body: { sut: string; readme: string; config?: Record<string, unknown> }) =>
      apiFetch<{ run_id: string; status: string }>("/api/runs", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    findings: (id: string) => apiFetch<Finding[]>(`/api/runs/${id}/findings`),
    agents: (id: string) => apiFetch<Agent[]>(`/api/runs/${id}/agents`),
  },
};
