'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button, Input, Select, Modal } from '@/shared/ui';
import type { Product } from '@/core/types/models';
import { getErrorMessage } from '@/core/api/error-handler';
import {
  useCreateProduct,
  useUpdateProduct,
  useCategories,
} from '../hooks/useProducts';

const productSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .max(255, 'Name must be at most 255 characters'),
  sku: z
    .string()
    .min(1, 'SKU is required')
    .max(100, 'SKU must be at most 100 characters'),
  barcode: z
    .string()
    .max(100, 'Barcode must be at most 100 characters')
    .optional()
    .or(z.literal('')),
  price: z
    .string()
    .min(1, 'Price is required')
    .refine(
      (val) => {
        const num = parseFloat(val);
        return !isNaN(num) && num >= 0.01 && num <= 999999999.99;
      },
      { message: 'Price must be between 0.01 and 999,999,999.99' }
    ),
  stock: z
    .string()
    .min(1, 'Stock is required')
    .refine(
      (val) => {
        const num = parseInt(val, 10);
        return !isNaN(num) && num >= 0;
      },
      { message: 'Stock must be a non-negative integer' }
    ),
  category_id: z.string().optional().or(z.literal('')),
});

type ProductFormValues = z.infer<typeof productSchema>;

interface ProductFormProps {
  isOpen: boolean;
  onClose: () => void;
  product?: Product | null;
}

export function ProductForm({ isOpen, onClose, product }: ProductFormProps) {
  const isEditing = !!product;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ProductFormValues>({
    resolver: zodResolver(productSchema),
    defaultValues: {
      name: '',
      sku: '',
      barcode: '',
      price: '',
      stock: '0',
      category_id: '',
    },
  });

  const { data: categoriesData } = useCategories({ page: 1, page_size: 100 });
  const createProduct = useCreateProduct();
  const updateProduct = useUpdateProduct();

  const mutation = isEditing ? updateProduct : createProduct;

  useEffect(() => {
    if (product) {
      reset({
        name: product.name,
        sku: product.sku,
        barcode: product.barcode ?? '',
        price: String(product.price),
        stock: String(product.stock),
        category_id: product.category_id ?? '',
      });
    } else {
      reset({
        name: '',
        sku: '',
        barcode: '',
        price: '',
        stock: '0',
        category_id: '',
      });
    }
  }, [product, reset]);

  const onSubmit = (data: ProductFormValues) => {
    const payload = {
      name: data.name,
      sku: data.sku,
      barcode: data.barcode || null,
      price: parseFloat(data.price),
      stock: parseInt(data.stock, 10),
      category_id: data.category_id || null,
    };

    if (isEditing && product) {
      updateProduct.mutate(
        { productId: product.id, data: payload },
        {
          onSuccess: () => {
            onClose();
            reset();
          },
        }
      );
    } else {
      createProduct.mutate(payload, {
        onSuccess: () => {
          onClose();
          reset();
        },
      });
    }
  };

  const categoryOptions = [
    { value: '', label: 'No Category' },
    ...(categoriesData?.data?.map((cat) => ({
      value: cat.id,
      label: cat.name,
    })) ?? []),
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Product' : 'Create Product'}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {mutation.isError && (
          <div
            className="rounded-lg border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700"
            role="alert"
          >
            {getErrorMessage(mutation.error)}
          </div>
        )}

        <Input
          label="Name"
          placeholder="Product name"
          error={errors.name?.message}
          register={register('name')}
        />

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="SKU"
            placeholder="e.g. PRD-001"
            error={errors.sku?.message}
            register={register('sku')}
          />
          <Input
            label="Barcode"
            placeholder="Optional"
            error={errors.barcode?.message}
            register={register('barcode')}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Price"
            type="number"
            placeholder="0.00"
            error={errors.price?.message}
            register={register('price')}
          />
          <Input
            label="Stock"
            type="number"
            placeholder="0"
            error={errors.stock?.message}
            register={register('stock')}
          />
        </div>

        <Select
          label="Category"
          options={categoryOptions}
          error={errors.category_id?.message}
          register={register('category_id')}
        />

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            {isEditing ? 'Update' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
