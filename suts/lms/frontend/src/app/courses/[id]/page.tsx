"use client";

import { useEffect, useState, useRef } from "react";
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

interface Submission {
  id: string;
  student_id: string;
  student_name: string;
  score: number | null;
  feedback: string | null;
  text_content: string | null;
  submitted_at: string;
  graded_at: string | null;
}

interface Course {
  id: string;
  title: string;
  description: string;
  teacher_id: string;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export default function CourseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const courseId = params.id as string;

  const [course, setCourse] = useState<Course | null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [submissions, setSubmissions] = useState<Record<string, Submission[]>>({});
  const [mySubmissions, setMySubmissions] = useState<Record<string, Submission>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [enrolled, setEnrolled] = useState(false);
  const [enrolling, setEnrolling] = useState(false);

  const [newAssignment, setNewAssignment] = useState({ title: "", description: "", max_score: 100 });
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);

  const [expandedAssignment, setExpandedAssignment] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("lms_token");
    if (!token) { router.push("/auth/login"); return; }

    async function load() {
      try {
        const [courses, asgns] = await Promise.all([
          lmsApi.courses.list(token!),
          lmsApi.assignments.listByCourse(token!, courseId),
        ]);
        const found = (courses as unknown as Course[]).find((c) => c.id === courseId);
        if (!found) { setError("Course not found"); setLoading(false); return; }
        setCourse(found);
        setAssignments(asgns as unknown as Assignment[]);
      } catch (e: unknown) {
        setError(errorMessage(e));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [courseId, router]);

  const user = typeof window !== "undefined"
    ? JSON.parse(localStorage.getItem("lms_user") ?? "{}")
    : {};
  const token = typeof window !== "undefined" ? localStorage.getItem("lms_token") ?? "" : "";
  const isTeacherOrAdmin = user.role === "teacher" || user.role === "admin";

  useEffect(() => {
    if (!token || !course) return;
    if (isTeacherOrAdmin) {
      assignments.forEach((a) => {
        lmsApi.submissions.listByAssignment(token, a.id)
          .then((list) => setSubmissions((prev) => ({ ...prev, [a.id]: list as unknown as Submission[] })))
          .catch(() => {});
      });
    } else {
      lmsApi.submissions.listMine(token)
        .then((list) => {
          const map: Record<string, Submission> = {};
          for (const s of list as unknown as Submission[]) {
            map[s.student_id] = s;
          }
          setMySubmissions(map);
        })
        .catch(() => {});
    }
  }, [token, course, assignments, isTeacherOrAdmin]);

  async function handleEnroll() {
    if (!token) return;
    setEnrolling(true);
    try {
      await lmsApi.courses.enroll(token, courseId);
      setEnrolled(true);
    } catch (e: unknown) {
      alert(errorMessage(e));
    } finally {
      setEnrolling(false);
    }
  }

  async function handleCreateAssignment(e: React.FormEvent) {
    e.preventDefault();
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
    } catch (e: unknown) {
      alert(errorMessage(e));
    } finally {
      setCreating(false);
    }
  }

  if (loading) return <div className="flex items-center justify-center min-h-screen text-gray-500">Loading…</div>;
  if (error) return <div className="flex items-center justify-center min-h-screen text-red-500">{error}</div>;
  if (!course) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <Link href="/" className="text-blue-600 font-semibold text-lg">← LMS</Link>
        <span className="text-sm text-gray-500">{user.email}</span>
      </nav>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow p-6 mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">{course.title}</h1>
          <p className="text-gray-600 mb-4">{course.description}</p>
          {user.role === "student" && (
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
                <li key={a.id}>
                  <AssignmentCard
                    assignment={a}
                    user={user}
                    token={token}
                    isTeacherOrAdmin={isTeacherOrAdmin}
                    submissions={submissions[a.id] ?? []}
                    mySubmission={mySubmissions[a.id]}
                    expanded={expandedAssignment === a.id}
                    onToggle={() => setExpandedAssignment(expandedAssignment === a.id ? null : a.id)}
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}

function AssignmentCard({
  assignment,
  user,
  token,
  isTeacherOrAdmin,
  submissions,
  mySubmission,
  expanded,
  onToggle,
}: {
  assignment: Assignment;
  user: Record<string, string>;
  token: string;
  isTeacherOrAdmin: boolean;
  submissions: Submission[];
  mySubmission?: Submission;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="py-4">
      <button onClick={onToggle} className="w-full text-left">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-medium text-gray-800">{assignment.title}</h3>
            <p className="text-sm text-gray-500 mt-1">{assignment.description}</p>
            {assignment.due_date && (
              <p className="text-xs text-orange-500 mt-1">
                Due: {new Date(assignment.due_date).toLocaleDateString()}
              </p>
            )}
          </div>
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full ml-4 shrink-0">
            {assignment.max_score} pts
          </span>
        </div>
      </button>

      {expanded && (
        <div className="mt-3 pl-4 border-l-2 border-blue-200 space-y-3">
          {isTeacherOrAdmin ? (
            <TeacherAssignmentView
              assignment={assignment}
              token={token}
              submissions={submissions}
            />
          ) : (
            <StudentAssignmentView
              assignment={assignment}
              token={token}
              mySubmission={mySubmission}
            />
          )}
        </div>
      )}
    </div>
  );
}

function StudentAssignmentView({
  assignment,
  token,
  mySubmission,
}: {
  assignment: Assignment;
  token: string;
  mySubmission?: Submission;
}) {
  const [textContent, setTextContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(!!mySubmission);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!textContent.trim() && !file) return;
    setSubmitting(true);
    try {
      await lmsApi.assignments.submit(token, assignment.id, textContent, file ?? undefined);
      setSubmitted(true);
    } catch (e: unknown) {
      alert(errorMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted || mySubmission) {
    const s = mySubmission;
    return (
      <div className="bg-green-50 rounded-lg p-4 text-sm space-y-2">
        <p className="text-green-700 font-medium">✓ Submitted</p>
        {s && (
          <>
            {s.score !== null && (
              <p className="text-gray-700">
                Score: <span className="font-semibold">{s.score}</span> / {assignment.max_score}
              </p>
            )}
            {s.feedback && <p className="text-gray-600">Feedback: {s.feedback}</p>}
            <p className="text-xs text-gray-400">
              Submitted: {new Date(s.submitted_at).toLocaleString()}
            </p>
            {s.graded_at && (
              <p className="text-xs text-gray-400">
                Graded: {new Date(s.graded_at).toLocaleString()}
              </p>
            )}
          </>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="bg-gray-50 rounded-lg p-4 space-y-3">
      <textarea
        className="w-full border rounded-lg px-3 py-2 text-sm"
        placeholder="Write your submission…"
        rows={4}
        value={textContent}
        onChange={(e) => setTextContent(e.target.value)}
      />
      <input
        type="file"
        className="text-sm text-gray-600"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting || (!textContent.trim() && !file)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {submitting ? "Submitting…" : "Submit Assignment"}
        </button>
      </div>
    </form>
  );
}

function TeacherAssignmentView({
  assignment,
  token,
  submissions,
}: {
  assignment: Assignment;
  token: string;
  submissions: Submission[];
}) {
  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-gray-700">
        Submissions ({submissions.length})
      </p>
      {submissions.length === 0 ? (
        <p className="text-sm text-gray-400">No submissions yet.</p>
      ) : (
        submissions.map((s) => (
          <TeacherSubmissionRow
            key={s.id}
            submission={s}
            assignment={assignment}
            token={token}
          />
        ))
      )}
    </div>
  );
}

function TeacherSubmissionRow({
  submission,
  assignment,
  token,
}: {
  submission: Submission;
  assignment: Assignment;
  token: string;
}) {
  const [score, setScore] = useState(submission.score ?? assignment.max_score);
  const [feedback, setFeedback] = useState(submission.feedback ?? "");
  const [grading, setGrading] = useState(false);
  const [graded, setGraded] = useState(!!submission.graded_at);

  async function handleGrade(e: React.FormEvent) {
    e.preventDefault();
    setGrading(true);
    try {
      await lmsApi.assignments.grade(token, assignment.id, submission.id, score, feedback);
      setGraded(true);
    } catch (e: unknown) {
      alert(errorMessage(e));
    } finally {
      setGrading(false);
    }
  }

  return (
    <div className="bg-gray-50 rounded-lg p-4 space-y-2 border border-gray-200">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-800">{submission.student_name}</p>
        {graded && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Graded</span>}
      </div>
      {submission.text_content && (
        <p className="text-sm text-gray-600 bg-white rounded p-2 border">{submission.text_content}</p>
      )}
      <p className="text-xs text-gray-400">
        Submitted: {new Date(submission.submitted_at).toLocaleString()}
      </p>
      {!graded ? (
        <form onSubmit={handleGrade} className="flex items-start gap-3 pt-1">
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-600">Score:</label>
            <input
              type="number"
              className="w-20 border rounded px-2 py-1 text-sm"
              value={score}
              onChange={(e) => setScore(Number(e.target.value))}
              min={0}
              max={assignment.max_score}
            />
            <span className="text-xs text-gray-400">/ {assignment.max_score}</span>
          </div>
          <input
            className="flex-1 border rounded px-2 py-1 text-sm"
            placeholder="Feedback…"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
          />
          <button
            type="submit"
            disabled={grading}
            className="px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-xs"
          >
            {grading ? "Grading…" : "Grade"}
          </button>
        </form>
      ) : (
        <div className="text-sm text-gray-600 space-y-1">
          <p>Score: <span className="font-semibold">{submission.score}</span> / {assignment.max_score}</p>
          {submission.feedback && <p>Feedback: {submission.feedback}</p>}
        </div>
      )}
    </div>
  );
}
