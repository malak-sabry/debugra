"use client";

// DEBUGRA_BUG:LMS-10 — No responsive breakpoints; nav overflows at 375px viewport width
// Missing: hamburger menu / collapsible nav for mobile

import Link from "next/link";

interface NavProps {
  user: { name: string; role: string } | null;
  onLogout: () => void;
}

export default function Nav({ user, onLogout }: NavProps) {
  if (!user) return null;

  return (
    <nav
      className="bg-white border-b px-6 py-3 flex items-center gap-6"
      data-testid="main-nav"
      /* DEBUGRA_BUG:LMS-10 — flex with no flex-wrap; items spill off-screen on 375px */
    >
      <span className="font-bold text-blue-700 text-lg whitespace-nowrap">School LMS</span>

      {/* Nav links — no min-width constraint, overflow at narrow viewports */}
      <div className="flex items-center gap-4">
        <Link href="/" className="text-sm text-gray-600 hover:text-blue-700 whitespace-nowrap" data-testid="nav-home">
          Courses
        </Link>
        <Link href="/assignments" className="text-sm text-gray-600 hover:text-blue-700 whitespace-nowrap" data-testid="nav-assignments">
          Assignments
        </Link>
        {user.role === "teacher" && (
          <Link href="/courses/create" className="text-sm text-gray-600 hover:text-blue-700 whitespace-nowrap" data-testid="nav-create-course">
            Create Course
          </Link>
        )}
        {user.role === "admin" && (
          <Link href="/admin" className="text-sm text-purple-600 hover:underline whitespace-nowrap" data-testid="nav-admin">
            Admin
          </Link>
        )}
      </div>

      <div className="ml-auto flex items-center gap-4">
        <span className="text-sm text-gray-600 whitespace-nowrap" data-testid="user-name">
          {user.name} <span className="text-xs text-gray-400 capitalize">({user.role})</span>
        </span>
        <button
          onClick={onLogout}
          className="text-sm text-red-500 hover:underline whitespace-nowrap"
          data-testid="logout-button"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
