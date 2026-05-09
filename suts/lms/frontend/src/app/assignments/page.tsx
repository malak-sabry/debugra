"use client";

// DEBUGRA_BUG:LMS-04 — Assignment titles rendered with dangerouslySetInnerHTML
// A teacher can inject arbitrary HTML/JS via the assignment title field.
// Oracle: console error (JS exception from injected onerror handler)

import { useState, useEffect } from "react";
import Link from "next/link";
import { lmsApi } from "@/lib/api";
import Nav from "@/components/nav";

interface Assignment {
  id: string;
  course_id: string;
  title: string;
  description: string;
  max_score: number;
  due_date: string | null;
}

export default function AssignmentsPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [courses, setCourses] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const token = typeof window !== "undefined" ? localStorage.getItem("lms_token") ?? "" : "";
  const user = typeof window !== "undefined" ? JSON.parse(localStorage.getItem("lms_user") ?? "null") : null;

  const handleLogout = () => {
    localStorage.removeItem("lms_token");
    localStorage.removeItem("lms_user");
    window.location.href = "/";
  };

  useEffect(() => {
    if (!token) { window.location.href = "/auth/login"; return; }

    async function load() {
      try {
        const courseList = await lmsApi.courses.list(token);
        setCourses(courseList);

        const all: Assignment[] = [];
        for (const course of courseList) {
          try {
            const list = await lmsApi.assignments.listByCourse(token, course.id as string);
            all.push(...(list as unknown as Assignment[]));
          } catch {
            // course may have no assignments
          }
        }
        setAssignments(all);
      } catch {
        setError("Failed to load assignments");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [token]);

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav user={user} onLogout={handleLogout} />

      <main className="max-w-4xl mx-auto px-6 py-8">
        <h2 className="text-xl font-semibold mb-6">All Assignments</h2>

        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-gray-200 rounded-xl animate-pulse" />
            ))}
          </div>
        )}

        {error && (
          <p className="text-red-500 text-sm" data-testid="error-message">{error}</p>
        )}

        {!loading && assignments.length === 0 && !error && (
          <p className="text-gray-500" data-testid="no-assignments">No assignments found.</p>
        )}

        <div className="space-y-4">
          {assignments.map((a) => {
            const course = courses.find((c) => c.id === a.course_id);
            return (
              <div
                key={a.id}
                className="bg-white rounded-xl border p-5"
                data-testid={`assignment-card-${a.id}`}
              >
                {/*
                  DEBUGRA_BUG:LMS-04 — XSS: title rendered via dangerouslySetInnerHTML.
                  A teacher who sets title = '<img src=x onerror=alert(1)>' will cause
                  a JS error in the browser console (oracle: console_error / js_exception).
                */}
                <h3
                  className="font-semibold text-gray-900"
                  data-testid="assignment-title"
                  dangerouslySetInnerHTML={{ __html: a.title }}
                />
                <p className="text-sm text-gray-500 mt-1">{a.description}</p>
                <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
                  <span>Max score: {a.max_score}</span>
                  {a.due_date && <span>Due: {new Date(a.due_date).toLocaleDateString()}</span>}
                  {course && (
                    <span>
                      Course:{" "}
                      <Link
                        href={`/courses/${a.course_id}`}
                        className="text-blue-600 hover:underline"
                        data-testid="course-link"
                      >
                        {course.title as string}
                      </Link>
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
