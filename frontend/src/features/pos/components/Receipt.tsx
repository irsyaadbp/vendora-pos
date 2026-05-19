'use client';

import { Modal } from '@/shared/ui';
import { formatCurrency, formatDate } from '@/shared/utils/formatters';
import type { TransactionReceipt } from '../services/pos.service';

interface ReceiptProps {
  isOpen: boolean;
  onClose: () => void;
  receipt: TransactionReceipt | null;
}

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: 'Cash',
  qris: 'QRIS',
  debit_card: 'Debit Card',
  credit_card: 'Credit Card',
};

export function Receipt({ isOpen, onClose, receipt }: ReceiptProps) {
  if (!receipt) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Transaction Receipt">
      <div className="space-y-4">
        {/* Receipt Header */}
        <div className="text-center border-b border-dashed border-neutral-300 pb-3">
          <p className="text-xs text-neutral-500">Transaction ID</p>
          <p className="font-mono text-xs text-neutral-700">
            {receipt.id}
          </p>
          <p className="mt-1 text-xs text-neutral-500">
            {formatDate(receipt.created_at)}
          </p>
          <p className="text-xs text-neutral-500">
            Cashier: {receipt.cashier_name}
          </p>
        </div>

        {/* Items */}
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase text-neutral-500">
            Items
          </h3>
          <ul className="divide-y divide-neutral-100" role="list" aria-label="Receipt items">
            {receipt.items.map((item, index) => (
              <li key={index} className="flex items-start justify-between py-2">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-neutral-900">{item.product_name}</p>
                  <p className="text-xs text-neutral-500">
                    {item.quantity} × {formatCurrency(item.unit_price)}
                  </p>
                </div>
                <span className="ml-3 text-sm font-medium text-neutral-900">
                  {formatCurrency(item.subtotal)}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Totals */}
        <div className="border-t border-dashed border-neutral-300 pt-3 space-y-1">
          {receipt.discount_amount > 0 && (
            <>
              <div className="flex items-center justify-between text-sm">
                <span className="text-neutral-600">Subtotal</span>
                <span className="text-neutral-900">
                  {formatCurrency(receipt.total_amount + receipt.discount_amount)}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-neutral-600">Discount</span>
                <span className="text-danger-600">
                  -{formatCurrency(receipt.discount_amount)}
                </span>
              </div>
            </>
          )}
          <div className="flex items-center justify-between text-base font-bold">
            <span className="text-neutral-900">Total</span>
            <span className="text-primary-600">
              {formatCurrency(receipt.total_amount)}
            </span>
          </div>
        </div>

        {/* Payment Method */}
        <div className="flex items-center justify-between rounded-lg bg-neutral-50 px-3 py-2">
          <span className="text-sm text-neutral-600">Payment</span>
          <span className="text-sm font-medium text-neutral-900">
            {PAYMENT_METHOD_LABELS[receipt.payment_method] || receipt.payment_method}
          </span>
        </div>

        {/* Close Button */}
        <div className="pt-2">
          <button
            type="button"
            onClick={onClose}
            className="w-full rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
          >
            Done
          </button>
        </div>
      </div>
    </Modal>
  );
}
