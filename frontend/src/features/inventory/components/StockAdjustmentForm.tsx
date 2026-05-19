'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button, Input, Modal } from '@/shared/ui';
import { getErrorMessage } from '@/core/api/error-handler';
import { useAdjustStock } from '../hooks/useInventory';

const stockAdjustmentSchema = z.object({
  product_id: z.string().min(1, 'Product ID is required'),
  new_quantity: z
    .string()
    .min(1, 'New quantity is required')
    .refine(
      (val) => {
        const num = parseInt(val, 10);
        return !isNaN(num) && num >= 0 && num <= 999999;
      },
      { message: 'Quantity must be between 0 and 999,999' }
    ),
  reason: z
    .string()
    .min(1, 'Reason is required')
    .max(500, 'Reason must be at most 500 characters'),
});

type StockAdjustmentFormValues = z.infer<typeof stockAdjustmentSchema>;

interface StockAdjustmentFormProps {
  isOpen: boolean;
  onClose: () => void;
  productId?: string;
  productName?: string;
  currentStock?: number;
}

export function StockAdjustmentForm({
  isOpen,
  onClose,
  productId,
  productName,
  currentStock,
}: StockAdjustmentFormProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<StockAdjustmentFormValues>({
    resolver: zodResolver(stockAdjustmentSchema),
    defaultValues: {
      product_id: productId ?? '',
      new_quantity: '',
      reason: '',
    },
  });

  const adjustStock = useAdjustStock();

  const onSubmit = (data: StockAdjustmentFormValues) => {
    const payload = {
      product_id: data.product_id,
      new_quantity: parseInt(data.new_quantity, 10),
      reason: data.reason,
    };

    adjustStock.mutate(payload, {
      onSuccess: () => {
        onClose();
        reset();
      },
    });
  };

  const handleClose = () => {
    onClose();
    reset();
    adjustStock.reset();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Adjust Stock">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {adjustStock.isError && (
          <div
            className="rounded-lg border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700"
            role="alert"
          >
            {getErrorMessage(adjustStock.error)}
          </div>
        )}

        {productName && (
          <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3">
            <p className="text-sm text-neutral-600">Product</p>
            <p className="font-medium text-neutral-900">{productName}</p>
            {currentStock !== undefined && (
              <p className="mt-1 text-sm text-neutral-500">
                Current stock: <span className="font-medium">{currentStock}</span>
              </p>
            )}
          </div>
        )}

        {!productId && (
          <Input
            label="Product ID"
            placeholder="Enter product UUID"
            error={errors.product_id?.message}
            register={register('product_id')}
          />
        )}

        {productId && (
          <input type="hidden" {...register('product_id')} value={productId} />
        )}

        <Input
          label="New Quantity"
          type="number"
          placeholder="Enter new stock quantity (0 - 999,999)"
          error={errors.new_quantity?.message}
          register={register('new_quantity')}
        />

        <div className="w-full">
          <label
            htmlFor="reason"
            className="mb-1.5 block text-sm font-medium text-neutral-700"
          >
            Reason
          </label>
          <textarea
            id="reason"
            rows={3}
            placeholder="Explain why this adjustment is being made..."
            aria-invalid={!!errors.reason}
            aria-describedby={errors.reason ? 'reason-error' : undefined}
            className={`w-full rounded-lg border px-3 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-offset-0 ${
              errors.reason
                ? 'border-danger-500 focus:border-danger-500 focus:ring-danger-500/20'
                : 'border-neutral-300 focus:border-primary-500 focus:ring-primary-500/20'
            }`}
            {...register('reason')}
          />
          {errors.reason && (
            <p id="reason-error" className="mt-1.5 text-sm text-danger-600" role="alert">
              {errors.reason.message}
            </p>
          )}
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" loading={adjustStock.isPending}>
            Adjust Stock
          </Button>
        </div>
      </form>
    </Modal>
  );
}
