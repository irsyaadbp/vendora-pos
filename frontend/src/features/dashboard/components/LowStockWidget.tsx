'use client';

import type { Product } from '@/core/types/models';
import { formatNumber } from '@/shared/utils/formatters';

interface LowStockWidgetProps {
  products: Product[];
}

export function LowStockWidget({ products }: LowStockWidgetProps) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100">
          <svg
            className="h-5 w-5 text-amber-600"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
            />
          </svg>
        </div>
        <h3 className="text-sm font-medium text-neutral-500">
          Low Stock Products
        </h3>
      </div>
      <p className="mt-4 text-2xl font-semibold text-neutral-900">
        {formatNumber(products.length)}
      </p>

      {products.length > 0 && (
        <ul className="mt-4 max-h-48 space-y-2 overflow-y-auto">
          {products.map((product) => (
            <li
              key={product.id}
              className="flex items-center justify-between rounded-md bg-amber-50 px-3 py-2 text-sm"
            >
              <span className="truncate font-medium text-neutral-700">
                {product.name}
              </span>
              <span className="ml-2 whitespace-nowrap text-amber-700">
                {product.stock} left
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
