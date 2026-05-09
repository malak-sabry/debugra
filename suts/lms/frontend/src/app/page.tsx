"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { lmsApi } from "@/lib/api";
import Nav from "@/components/nav";

export default function HomePage() {
  const [courses, setCourses] = useState<Record<string, unknown>[]>([]);
  const token = typeof window !== "undefined" ? localStorage.getItem("lms_token") : null;
  const user = typeof window !== "undefined" ? JSON.parse(localStorage.getItem("lms_user") ?? "null") : null;

  useEffect(() => {
    if (token) {
      lmsApi.courses.list(token).then(setCourses).catch(() => {});
    }
  }, [token]);

  if (!user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-6">
        <h1 className="text-3xl font-bold text-blue-700">School LMS</h1>
        <p className="text-gray-600">Learning Management System</p>
        <div className="flex gap-4">
          <Link
            href="/auth/login"
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            data-testid="login-link"
          >
            Sign In
          </Link>
          <Link
            href="/auth/register"
            className="px-6 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
            data-testid="register-link"
          >
            Register
          </Link>
        </div>
      </div>
    );
  }

  const role = user.role;

  const handleLogout = () => {
    localStorage.removeItem("lms_token");
    localStorage.removeItem("lms_user");
    window.location.href = "/";
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Nav user={user} onLogout={handleLogout} />

      <main className="max-w-5xl mx-auto px-6 py-8">
        <h2 className="text-xl font-semibold mb-4">Available Courses</h2>

        {role === "teacher" && (
          <Link
            href="/courses/create"
            className="mb-6 inline-block px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
            data-testid="create-course-link"
          >
            + Create Course
          </Link>
        )}

        {courses.length === 0 ? (
          <p className="text-gray-500" data-testid="no-courses">No courses available yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {courses.map((c) => (
              <Link
                key={c.id as string}
                href={`/courses/${c.id}`}
                className="block bg-white rounded-xl border p-5 hover:shadow-md transition-shadow"
                data-testid={`course-card-${c.id}`}
              >
                <h3 className="font-semibold text-gray-900" data-testid="course-title">{c.title as string}</h3>
                <p className="text-sm text-gray-500 mt-1">{c.description as string}</p>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
