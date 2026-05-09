"use client";

import { useEffect, useState } from "react";
import { lmsApi } from "@/lib/api";

export default function AdminPage() {
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [users, setUsers] = useState<Record<string, unknown>[]>([]);
  const token = typeof window !== "undefined" ? localStorage.getItem("lms_token") ?? "" : "";

  useEffect(() => {
    if (!token) return;
    Promise.all([
      lmsApi.admin.dashboard(token),
      lmsApi.admin.users(token),
    ]).then(([s, u]) => {
      setStats(s);
      setUsers(u);
    }).catch(() => {});
  }, [token]);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <span className="font-bold text-purple-700">Admin Dashboard</span>
        {/* DEBUGRA_BUG:LMS-06 — Stale timestamp, never updates */}
        <span className="text-xs text-gray-400" data-testid="last-updated">Last updated: Jan 1, 2025 00:00</span>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {stats && (
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Total Users" value={stats.users as number} />
            <StatCard label="Courses" value={stats.courses as number} />
            <StatCard label="Submissions" value={stats.submissions as number} />
          </div>
        )}

        <section>
          <h2 className="text-lg font-semibold mb-4">All Users</h2>
          <div className="bg-white rounded-xl border overflow-hidden">
            <table className="w-full text-sm" data-testid="users-table">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Role</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id as string} className="border-b last:border-0">
                    <td className="px-4 py-3">{u.name as string}</td>
                    <td className="px-4 py-3 text-gray-500">{u.email as string}</td>
                    <td className="px-4 py-3 capitalize">{u.role as string}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${u.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-xl border p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-3xl font-bold text-gray-900 mt-1">{value ?? 0}</p>
    </div>
  );
}
