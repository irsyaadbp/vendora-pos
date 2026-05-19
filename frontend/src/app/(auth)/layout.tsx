"use client";

import { QueryProvider } from "@/core/providers/QueryProvider";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <QueryProvider>
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4 py-12">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </QueryProvider>
  );
}
