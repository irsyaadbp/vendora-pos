'use client';

import { useState } from 'react';
import { SearchInput } from '@/shared/ui';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useCartStore } from '@/core/stores/cart.store';
import { usePosProductSearch } from '../hooks/usePos';
import { formatCurrency } from '@/shared/utils/formatters';
import type { Product } from '@/core/types/models';

export function ProductSearch() {
  const [searchValue, setSearchValue] = useState('');
  const debouncedQuery = useDebounce(searchValue, 300);
  const { data, isLoading } = usePosProductSearch(debouncedQuery);
  const addItem = useCartStore((state) => state.addItem);

  const handleAddToCart = (product: Product) => {
    addItem(product, 1);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4">
        <SearchInput
          value={searchValue}
          onChange={setSearchValue}
          placeholder="Search by name, SKU, or barcode..."
          debounceMs={0}
        />
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <svg
              className="h-5 w-5 animate-spin text-neutral-400"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span className="ml-2 text-sm text-neutral-500">Loading products...</span>
          </div>
        )}

        {!isLoading && data?.data.length === 0 && (
          <div className="py-8 text-center text-sm text-neutral-500">
            {debouncedQuery
              ? `No products found for "${debouncedQuery}"`
              : 'No products available'}
          </div>
        )}

        {data && data.data.length > 0 && (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {data.data.map((product) => (
              <button
                key={product.id}
                type="button"
                onClick={() => handleAddToCart(product)}
                disabled={product.stock <= 0}
                className="flex items-start justify-between rounded-lg border border-neutral-200 p-3 text-left transition-colors hover:border-primary-300 hover:bg-primary-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <div className="min-w-0 flex-1 pr-2">
                  <p className="truncate text-sm font-medium text-neutral-900">
                    {product.name}
                  </p>
                  <p className="truncate text-xs text-neutral-500">
                    {product.sku}
                  </p>
                  <p className="mt-1 text-sm font-semibold text-primary-600">
                    {formatCurrency(product.price)}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                    product.stock <= 0
                      ? 'bg-danger-100 text-danger-700'
                      : product.low_stock
                        ? 'bg-warning-100 text-warning-700'
                        : 'bg-success-100 text-success-700'
                  }`}
                >
                  {product.stock}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
