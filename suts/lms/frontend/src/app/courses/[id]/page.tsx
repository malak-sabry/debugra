"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { lmsApi } from "@/lib/api";

interface Assignment {
  id: string;
  title: string;
  description: string;
  due_date: string | null;
  max_score: number;
}

interface Course {
  id: string;
  title: string;
  description: string;
  teacher_id: string;
}

export default function CourseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const courseId = params.id as string;

  const [course, setCourse] = useState<Course | null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [enrolled, setEnrolled] = useState(false);
  const [enrolling, setEnrolling] = useState(false);

  const [newAssignment, setNewAssignment] = useState({ title: "", description: "", max_score: 100 });
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("lms_token");
    if (!token) { router.push("/auth/login"); return; }

    async function load() {
      try {
        const [courses, asgns] = await Promise.all([
          lmsApi.courses.list(token!),
          lmsApi.assignments.listByCourse(token!, courseId),
        ]);
        const found = courses.find((c: any) => c.id === courseId) as Course | undefined;
        if (!found) { setError("Course not found"); setLoading(false); return; }
        setCourse(found as Course);
        setAssignments(asgns as unknown as Assignment[]);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [courseId, router]);

  async function handleEnroll() {
    const token = localStorage.getItem("lms_token");
    if (!token) return;
    setEnrolling(true);
    try {
      await lmsApi.courses.enroll(token, courseId);
      setEnrolled(true);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setEnrolling(false);
    }
  }

  async function handleCreateAssignment(e: React.FormEvent) {
    e.preventDefault();
    const token = localStorage.getItem("lms_token");
    if (!token) return;
    setCreating(true);
    try {
      const created = await lmsApi.assignments.create(token, {
        course_id: courseId,
        ...newAssignment,
      });
      setAssignments((prev) => [...prev, created as Assignment]);
      setNewAssignment({ title: "", description: "", max_score: 100 });
      setShowCreate(false);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <div className="flex items-center justify-center min-h-screen text-gray-500">Loading…</div>;
  if (error) return <div className="flex items-center justify-center min-h-screen text-red-500">{error}</div>;
  if (!course) return null;

  const user = JSON.parse(localStorage.getItem("lms_user") ?? "{}");
  const isTeacherOrAdmin = user.role === "teacher" || user.role === "admin";

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <Link href="/" className="text-blue-600 font-semibold text-lg">← LMS</Link>
        <span className="text-sm text-gray-500">{user.email}</span>
      </nav>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">{course.title}</h1>
          <p className="text-gray-600 mb-4">{course.description}</p>
          {!isTeacherOrAdmin && (
            <button
              onClick={handleEnroll}
              disabled={enrolling || enrolled}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {enrolled ? "Enrolled ✓" : enrolling ? "Enrolling…" : "Enroll in Course"}
            </button>
          )}
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800">Assignments</h2>
            {isTeacherOrAdmin && (
              <button
                onClick={() => setShowCreate((v) => !v)}
                className="px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700"
              >
                {showCreate ? "Cancel" : "+ New Assignment"}
              </button>
            )}
          </div>

          {showCreate && (
            <form onSubmit={handleCreateAssignment} className="mb-6 bg-gray-50 rounded-lg p-4 space-y-3">
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Assignment title"
                value={newAssignment.title}
                onChange={(e) => setNewAssignment((a) => ({ ...a, title: e.target.value }))}
                required
              />
              <textarea
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Description"
                rows={3}
                value={newAssignment.description}
                onChange={(e) => setNewAssignment((a) => ({ ...a, description: e.target.value }))}
              />
              <div className="flex items-center gap-3">
                <label className="text-sm text-gray-600">Max score:</label>
                <input
                  type="number"
                  className="w-24 border rounded-lg px-3 py-2 text-sm"
                  value={newAssignment.max_score}
                  onChange={(e) => setNewAssignment((a) => ({ ...a, max_score: Number(e.target.value) }))}
                  min={1}
                />
              </div>
              <button
                type="submit"
                disabled={creating}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
              >
                {creating ? "Creating…" : "Create Assignment"}
              </button>
            </form>
          )}

          {assignments.length === 0 ? (
            <p className="text-gray-400 text-sm">No assignments yet.</p>
          ) : (
            <ul className="divide-y">
              {assignments.map((a) => (
                <li key={a.id} className="py-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-medium text-gray-800">{a.title}</h3>
                      <p className="text-sm text-gray-500 mt-1">{a.description}</p>
                      {a.due_date && (
                        <p className="text-xs text-orange-500 mt-1">Due: {new Date(a.due_date).toLocaleDateString()}</p>
                      )}
                    </div>
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full ml-4 shrink-0">
                      {a.max_score} pts
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
