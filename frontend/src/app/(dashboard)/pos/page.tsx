'use client';

import { useState } from 'react';
import { Button } from '@/shared/ui';
import { useCartStore } from '@/core/stores/cart.store';
import { ProductSearch } from '@/features/pos/components/ProductSearch';
import { Cart } from '@/features/pos/components/Cart';
import { DiscountInput } from '@/features/pos/components/DiscountInput';
import { PaymentSelector } from '@/features/pos/components/PaymentSelector';
import { Receipt } from '@/features/pos/components/Receipt';
import { useCreateTransaction } from '@/features/pos/hooks/usePos';
import type { TransactionReceipt } from '@/features/pos/services/pos.service';
import type { PaymentMethod } from '@/core/types/models';

export default function PosPage() {
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod | null>(null);
  const [receipt, setReceipt] = useState<TransactionReceipt | null>(null);
  const [isReceiptOpen, setIsReceiptOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const items = useCartStore((state) => state.items);
  const discount = useCartStore((state) => state.discount);
  const clearCart = useCartStore((state) => state.clearCart);

  const createTransaction = useCreateTransaction();

  const canSubmit =
    items.length > 0 && paymentMethod !== null && !createTransaction.isPending;

  const handleSubmit = async () => {
    if (!canSubmit || !paymentMethod) return;

    setError(null);

    const transactionData = {
      items: items.map((item) => ({
        product_id: item.product.id,
        quantity: item.quantity,
      })),
      discount_type: discount?.type ?? null,
      discount_value: discount?.value ?? null,
      payment_method: paymentMethod,
    };

    try {
      const result = await createTransaction.mutateAsync(transactionData);
      setReceipt(result);
      setIsReceiptOpen(true);
      clearCart();
      setPaymentMethod(null);
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { message?: string } } };
        setError(axiosError.response?.data?.message || 'Transaction failed. Please try again.');
      } else {
        setError('Transaction failed. Please try again.');
      }
    }
  };

  const handleReceiptClose = () => {
    setIsReceiptOpen(false);
    setReceipt(null);
  };

  return (
    <div className="flex h-[calc(100vh-5rem)] gap-6">
      {/* Left Panel - Product Search */}
      <div className="flex-1 rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold text-neutral-900">
          Products
        </h2>
        <ProductSearch />
      </div>

      {/* Right Panel - Cart & Checkout */}
      <div className="flex w-96 flex-col rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold text-neutral-900">Cart</h2>

        {/* Cart Items */}
        <div className="flex-1 overflow-hidden">
          <Cart />
        </div>

        {/* Checkout Controls */}
        {items.length > 0 && (
          <div className="mt-4 space-y-3 border-t border-neutral-200 pt-4">
            <DiscountInput />
            <PaymentSelector value={paymentMethod} onChange={setPaymentMethod} />

            {error && (
              <div
                className="rounded-lg bg-danger-50 px-3 py-2 text-sm text-danger-700"
                role="alert"
              >
                {error}
              </div>
            )}

            <Button
              variant="primary"
              size="lg"
              className="w-full"
              onClick={handleSubmit}
              disabled={!canSubmit}
              loading={createTransaction.isPending}
            >
              Complete Transaction
            </Button>
          </div>
        )}
      </div>

      {/* Receipt Modal */}
      <Receipt
        isOpen={isReceiptOpen}
        onClose={handleReceiptClose}
        receipt={receipt}
      />
    </div>
  );
}
