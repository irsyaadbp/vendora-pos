'use client';

import { formatCurrency } from '@/shared/utils/formatters';

interface SalesWidgetProps {
  totalSales: number;
}

export function SalesWidget({ totalSales }: SalesWidgetProps) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
          <svg
            className="h-5 w-5 text-green-600"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
            />
          </svg>
        </div>
        <h3 className="text-sm font-medium text-neutral-500">
          Today&apos;s Sales
        </h3>
      </div>
      <p className="mt-4 text-2xl font-semibold text-neutral-900">
        {formatCurrency(totalSales)}
      </p>
    </div>
  );
}
