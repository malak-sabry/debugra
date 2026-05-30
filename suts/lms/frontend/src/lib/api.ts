const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { token?: string }
): Promise<T> {
  const { token, ...rest } = init ?? {};
  const res = await fetch(`${BASE}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(rest.headers ?? {}),
    },
  });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

export const lmsApi = {
  auth: {
    register: (body: { email: string; password: string; name: string; role: string }) =>
      apiFetch<{ access_token: string; user: Record<string, string> }>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    login: (email: string, password: string) => {
      const form = new URLSearchParams({ username: email, password });
      return fetch(`${BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form.toString(),
      }).then((r) => r.json());
    },
  },
  courses: {
    list: (token: string) => apiFetch<Record<string, unknown>[]>("/api/courses", { token }),
    create: (token: string, body: { title: string; description: string }) =>
      apiFetch("/api/courses", { method: "POST", body: JSON.stringify(body), token }),
    enroll: (token: string, courseId: string) =>
      apiFetch(`/api/courses/${courseId}/enroll`, { method: "POST", token }),
  },
  assignments: {
    listByCourse: (token: string, courseId: string) =>
      apiFetch<Record<string, unknown>[]>(`/api/assignments/course/${courseId}`, { token }),
    create: (token: string, body: Record<string, unknown>) =>
      apiFetch("/api/assignments", { method: "POST", body: JSON.stringify(body), token }),
    submit: (token: string, assignmentId: string, textContent: string, file?: File) => {
      const form = new FormData();
      form.append("text_content", textContent);
      if (file) form.append("file", file);
      return fetch(`${BASE}/api/assignments/${assignmentId}/submit`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      }).then((r) => { if (!r.ok) throw new Error(`submit → ${r.status}`); return r.json(); });
    },
    grade: (token: string, assignmentId: string, submissionId: string, score: number, feedback: string) =>
      apiFetch(`/api/assignments/${assignmentId}/grade/${submissionId}?score=${score}&feedback=${encodeURIComponent(feedback)}`, {
        method: "POST",
        token,
      }),
  },
  submissions: {
    listMine: (token: string) =>
      apiFetch<Record<string, unknown>[]>("/api/submissions", { token }),
    listByAssignment: (token: string, assignmentId: string) =>
      apiFetch<Record<string, unknown>[]>(`/api/submissions/assignment/${assignmentId}`, { token }),
  },
  admin: {
    dashboard: (token: string) => apiFetch<Record<string, unknown>>("/api/admin/dashboard", { token }),
    users: (token: string) => apiFetch<Record<string, unknown>[]>("/api/admin/users", { token }),
  },
};
