'use client';

import { formatNumber } from '@/shared/utils/formatters';

interface TransactionCountWidgetProps {
  count: number;
}

export function TransactionCountWidget({ count }: TransactionCountWidgetProps) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100">
          <svg
            className="h-5 w-5 text-blue-600"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 0 0-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 0 0-16.536-1.84M7.5 14.25 5.106 5.272M6 20.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm12.75 0a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"
            />
          </svg>
        </div>
        <h3 className="text-sm font-medium text-neutral-500">
          Today&apos;s Transactions
        </h3>
      </div>
      <p className="mt-4 text-2xl font-semibold text-neutral-900">
        {formatNumber(count)}
      </p>
    </div>
  );
}
