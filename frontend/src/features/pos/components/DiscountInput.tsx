'use client';

import { useState } from 'react';
import { useCartStore } from '@/core/stores/cart.store';
import { Button } from '@/shared/ui';
import type { Discount } from '@/core/types/models';

export function DiscountInput() {
  const [discountType, setDiscountType] = useState<'percentage' | 'fixed'>('percentage');
  const [discountValue, setDiscountValue] = useState('');
  const discount = useCartStore((state) => state.discount);
  const setDiscount = useCartStore((state) => state.setDiscount);
  const clearDiscount = useCartStore((state) => state.clearDiscount);
  const getSubtotal = useCartStore((state) => state.getSubtotal);

  const subtotal = getSubtotal();

  const handleApply = () => {
    const value = parseFloat(discountValue);
    if (isNaN(value) || value <= 0) return;

    if (discountType === 'percentage' && value > 100) return;

    const amount =
      discountType === 'percentage'
        ? Math.round((subtotal * value) / 100)
        : value;

    if (amount > subtotal) return;

    const newDiscount: Discount = {
      type: discountType,
      value,
      amount,
    };

    setDiscount(newDiscount);
    setDiscountValue('');
  };

  const handleClear = () => {
    clearDiscount();
    setDiscountValue('');
  };

  return (
    <div className="space-y-2">
      <label className="text-xs font-medium text-neutral-600">Discount</label>

      {discount ? (
        <div className="flex items-center justify-between rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
          <span className="text-sm text-neutral-700">
            {discount.type === 'percentage'
              ? `${discount.value}% off`
              : `Fixed ${new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(discount.value)} off`}
          </span>
          <button
            type="button"
            onClick={handleClear}
            aria-label="Remove discount"
            className="rounded p-1 text-neutral-400 hover:text-danger-600 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          {/* Type Toggle */}
          <div className="flex rounded-lg border border-neutral-300 overflow-hidden">
            <button
              type="button"
              onClick={() => setDiscountType('percentage')}
              className={`px-2.5 py-1.5 text-xs font-medium transition-colors ${
                discountType === 'percentage'
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-neutral-600 hover:bg-neutral-50'
              }`}
              aria-pressed={discountType === 'percentage'}
            >
              %
            </button>
            <button
              type="button"
              onClick={() => setDiscountType('fixed')}
              className={`px-2.5 py-1.5 text-xs font-medium transition-colors border-l border-neutral-300 ${
                discountType === 'fixed'
                  ? 'bg-primary-600 text-white'
                  : 'bg-white text-neutral-600 hover:bg-neutral-50'
              }`}
              aria-pressed={discountType === 'fixed'}
            >
              Rp
            </button>
          </div>

          {/* Value Input */}
          <input
            type="number"
            value={discountValue}
            onChange={(e) => setDiscountValue(e.target.value)}
            placeholder={discountType === 'percentage' ? '0-100' : 'Amount'}
            min="0"
            max={discountType === 'percentage' ? '100' : undefined}
            className="flex-1 rounded-lg border border-neutral-300 px-3 py-1.5 text-sm placeholder:text-neutral-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            aria-label="Discount value"
          />

          {/* Apply Button */}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleApply}
            disabled={!discountValue || subtotal <= 0}
          >
            Apply
          </Button>
        </div>
      )}
    </div>
  );
}
