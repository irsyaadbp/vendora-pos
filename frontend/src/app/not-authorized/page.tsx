import Link from "next/link";

export default function NotAuthorizedPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-danger-100">
          <svg
            className="h-8 w-8 text-danger-600"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
            />
          </svg>
        </div>
        <h1 className="mb-2 text-2xl font-semibold text-neutral-900">
          Access Denied
        </h1>
        <p className="mb-8 text-neutral-600">
          You don&apos;t have permission to access this page. Please contact
          your administrator if you believe this is an error.
        </p>
        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link
            href="/pos"
            className="inline-flex items-center justify-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700"
          >
            Go to POS
          </Link>
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
          >
            Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
}
