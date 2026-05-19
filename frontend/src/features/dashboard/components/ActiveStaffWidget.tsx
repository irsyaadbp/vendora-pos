'use client';

import { formatNumber } from '@/shared/utils/formatters';

interface ActiveStaffWidgetProps {
  count: number;
}

export function ActiveStaffWidget({ count }: ActiveStaffWidgetProps) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-purple-100">
          <svg
            className="h-5 w-5 text-purple-600"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z"
            />
          </svg>
        </div>
        <h3 className="text-sm font-medium text-neutral-500">Active Staff</h3>
      </div>
      <p className="mt-4 text-2xl font-semibold text-neutral-900">
        {formatNumber(count)}
      </p>
    </div>
  );
}
