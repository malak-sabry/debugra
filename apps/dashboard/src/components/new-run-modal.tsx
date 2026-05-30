"use client";

import { useState } from "react";
import { X, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

const LMS_README = `# School LMS
A learning management system with three roles: teacher, student, admin.

## Pages & Navigation
- Home (/) — Lists available courses. Shows "Sign In" / "Register" when logged out.
- /auth/login — Login form with email + password fields. data-testid: login-form, email-input, password-input, submit-button
- /auth/register — Registration form with name + email + password + role dropdown. data-testid: register-form, name-input, email-input, password-input, role-select, submit-button
- Nav bar (shown after login) — Links: Courses (/), Assignments (/assignments), Create Course (/courses/create, teacher only), Admin (/admin, admin only). data-testid: main-nav, nav-home, nav-assignments, nav-create-course, nav-admin, user-name, logout-button

## Teacher Flows
1. Teacher registers at /auth/register (select "teacher" role) and logs in at /auth/login
2. Teacher creates a course at /courses/create (data-testid: create-course-form, course-title-input, course-description-input, submit-button)
3. Teacher clicks on a course to open /courses/[id] detail page
4. Teacher clicks "+ New Assignment" to open a form, fills title + description + max score, clicks "Create Assignment"
5. Teacher clicks on an assignment to expand it, sees submissions list
6. Teacher enters score + feedback for each submission and clicks "Grade"

## Student Flows
1. Student registers at /auth/register (select "student" role) and logs in at /auth/login
2. Student browses courses at /, clicks a course card to open /courses/[id]
3. Student clicks "Enroll in Course" button
4. Student clicks on an assignment to expand it, sees the submit form
5. Student types text and/or uploads a file, clicks "Submit Assignment"
6. Student checks graded status and score after teacher grades

## Admin Flows
1. Admin registers and logs in
2. Admin views dashboard at /admin (data-testid: users-table)
3. Admin can see all users, course stats, submission stats

## Key data-testid attributes
- Course cards: course-card-{id}, course-title
- Assignment cards: assignment-card-{id}, assignment-title
- Navigation: main-nav, nav-home, nav-assignments, nav-create-course, nav-admin
- Forms: login-form, register-form, create-course-form
- Inputs: email-input, password-input, name-input, role-select, course-title-input, course-description-input
- Buttons: submit-button, logout-button, create-course-link
`;

const SHOP_README = `# E-commerce Checkout
A mini e-commerce platform with buyer and anonymous user roles.

## Roles
- **buyer**: Browses products, adds to cart, completes checkout
- **anonymous**: Browses products, views product detail pages

## Key Flows
1. Anonymous user browses product catalog
2. Buyer registers and logs in
3. Buyer adds items to cart
4. Buyer applies discount code
5. Buyer completes checkout with address and payment
6. Buyer views order confirmation
`;

export function NewRunModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (runId: string) => void;
}) {
  const [sut, setSut] = useState<"lms" | "shop">("lms");
  const [readme, setReadme] = useState(LMS_README);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSutChange = (value: "lms" | "shop") => {
    setSut(value);
    setReadme(value === "lms" ? LMS_README : SHOP_README);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.runs.create({ sut, readme });
      onCreated(res.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create run");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl rounded-2xl border border-border/60 bg-card shadow-2xl p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground">New QA Run</h2>
            <p className="text-sm text-muted-foreground">Configure Debugra to autonomously test an application</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-accent transition-colors">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* SUT selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">System Under Test</label>
            <div className="grid grid-cols-2 gap-3">
              {(["lms", "shop"] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => handleSutChange(option)}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    sut === option
                      ? "border-indigo-500/60 bg-indigo-500/10 text-indigo-300"
                      : "border-border/40 bg-card/30 text-muted-foreground hover:border-border"
                  }`}
                >
                  <div className="font-medium text-sm uppercase">{option}</div>
                  <div className="text-xs mt-0.5 opacity-70">
                    {option === "lms" ? "School LMS · Teacher, Student, Admin" : "E-commerce · Buyer, Anonymous"}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* README */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              README / Documentation
              <span className="text-muted-foreground font-normal ml-2">(Debugra reads this to understand the app)</span>
            </label>
            <textarea
              value={readme}
              onChange={(e) => setReadme(e.target.value)}
              rows={10}
              className="w-full rounded-xl border border-border/40 bg-background px-4 py-3 text-sm text-foreground font-mono resize-none focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400 bg-red-400/10 rounded-lg px-3 py-2">{error}</p>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-border/40 text-sm text-muted-foreground hover:text-foreground hover:border-border transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white text-sm font-medium transition-colors"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? "Launching…" : "Launch Run"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
