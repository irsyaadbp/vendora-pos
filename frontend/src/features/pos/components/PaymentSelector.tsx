'use client';

import type { PaymentMethod } from '@/core/types/models';

interface PaymentSelectorProps {
  value: PaymentMethod | null;
  onChange: (method: PaymentMethod) => void;
}

const PAYMENT_METHODS: { value: PaymentMethod; label: string; icon: string }[] = [
  { value: 'cash', label: 'Cash', icon: '💵' },
  { value: 'qris', label: 'QRIS', icon: '📱' },
  { value: 'debit_card', label: 'Debit Card', icon: '💳' },
  { value: 'credit_card', label: 'Credit Card', icon: '💳' },
];

export function PaymentSelector({ value, onChange }: PaymentSelectorProps) {
  return (
    <div className="space-y-2">
      <label className="text-xs font-medium text-neutral-600">
        Payment Method
      </label>
      <div
        className="grid grid-cols-2 gap-2"
        role="radiogroup"
        aria-label="Payment method"
      >
        {PAYMENT_METHODS.map((method) => (
          <button
            key={method.value}
            type="button"
            role="radio"
            aria-checked={value === method.value}
            onClick={() => onChange(method.value)}
            className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
              value === method.value
                ? 'border-primary-500 bg-primary-50 text-primary-700'
                : 'border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50'
            }`}
          >
            <span aria-hidden="true">{method.icon}</span>
            <span>{method.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
