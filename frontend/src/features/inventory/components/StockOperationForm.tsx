'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button, Input, Modal } from '@/shared/ui';
import { getErrorMessage } from '@/core/api/error-handler';
import { useStockIn, useStockOut } from '../hooks/useInventory';

const stockOperationSchema = z.object({
  product_id: z.string().min(1, 'Product ID is required'),
  quantity: z
    .string()
    .min(1, 'Quantity is required')
    .refine(
      (val) => {
        const num = parseInt(val, 10);
        return !isNaN(num) && num >= 1 && num <= 999999;
      },
      { message: 'Quantity must be between 1 and 999,999' }
    ),
});

type StockOperationFormValues = z.infer<typeof stockOperationSchema>;

type OperationType = 'stock_in' | 'stock_out';

interface StockOperationFormProps {
  isOpen: boolean;
  onClose: () => void;
  operationType: OperationType;
  productId?: string;
  productName?: string;
}

export function StockOperationForm({
  isOpen,
  onClose,
  operationType,
  productId,
  productName,
}: StockOperationFormProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<StockOperationFormValues>({
    resolver: zodResolver(stockOperationSchema),
    defaultValues: {
      product_id: productId ?? '',
      quantity: '',
    },
  });

  const stockIn = useStockIn();
  const stockOut = useStockOut();

  const mutation = operationType === 'stock_in' ? stockIn : stockOut;
  const title = operationType === 'stock_in' ? 'Stock In' : 'Stock Out';

  const onSubmit = (data: StockOperationFormValues) => {
    const payload = {
      product_id: data.product_id,
      quantity: parseInt(data.quantity, 10),
    };

    mutation.mutate(payload, {
      onSuccess: () => {
        onClose();
        reset();
      },
    });
  };

  const handleClose = () => {
    onClose();
    reset();
    mutation.reset();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={title}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {mutation.isError && (
          <div
            className="rounded-lg border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700"
            role="alert"
          >
            {getErrorMessage(mutation.error)}
          </div>
        )}

        {productName && (
          <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3">
            <p className="text-sm text-neutral-600">Product</p>
            <p className="font-medium text-neutral-900">{productName}</p>
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
          label="Quantity"
          type="number"
          placeholder="Enter quantity (1 - 999,999)"
          error={errors.quantity?.message}
          register={register('quantity')}
        />

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            {title}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
