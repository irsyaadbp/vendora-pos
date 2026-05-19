'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button, Input, Modal } from '@/shared/ui';
import { getErrorMessage } from '@/core/api/error-handler';
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from '../hooks/useProducts';
import type { Category } from '../services/product.service';

const categorySchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .max(100, 'Name must be at most 100 characters'),
  description: z
    .string()
    .max(500, 'Description must be at most 500 characters')
    .optional()
    .or(z.literal('')),
});

type CategoryFormValues = z.infer<typeof categorySchema>;

interface CategoryManagerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CategoryManager({ isOpen, onClose }: CategoryManagerProps) {
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [isFormVisible, setIsFormVisible] = useState(false);

  const { data: categoriesData, isLoading } = useCategories({
    page: 1,
    page_size: 100,
  });
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CategoryFormValues>({
    resolver: zodResolver(categorySchema),
    defaultValues: { name: '', description: '' },
  });

  const handleCreate = () => {
    setEditingCategory(null);
    reset({ name: '', description: '' });
    setIsFormVisible(true);
  };

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    reset({ name: category.name, description: category.description ?? '' });
    setIsFormVisible(true);
  };

  const handleDelete = (categoryId: string) => {
    if (window.confirm('Are you sure you want to delete this category?')) {
      deleteCategory.mutate(categoryId);
    }
  };

  const handleCancel = () => {
    setIsFormVisible(false);
    setEditingCategory(null);
    reset({ name: '', description: '' });
  };

  const onSubmit = (data: CategoryFormValues) => {
    const payload = {
      name: data.name,
      description: data.description || null,
    };

    if (editingCategory) {
      updateCategory.mutate(
        { categoryId: editingCategory.id, data: payload },
        {
          onSuccess: () => {
            handleCancel();
          },
        }
      );
    } else {
      createCategory.mutate(payload, {
        onSuccess: () => {
          handleCancel();
        },
      });
    }
  };

  const mutation = editingCategory ? updateCategory : createCategory;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Manage Categories">
      <div className="space-y-4">
        {/* Category List */}
        <div className="max-h-64 space-y-2 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-6">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
            </div>
          ) : categoriesData?.data?.length === 0 ? (
            <p className="py-4 text-center text-sm text-neutral-500">
              No categories yet
            </p>
          ) : (
            categoriesData?.data?.map((category) => (
              <div
                key={category.id}
                className="flex items-center justify-between rounded-lg border border-neutral-200 px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium text-neutral-900">
                    {category.name}
                  </p>
                  {category.description && (
                    <p className="text-xs text-neutral-500">
                      {category.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleEdit(category)}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(category.id)}
                    className="text-danger-600 hover:text-danger-700"
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Inline Form */}
        {isFormVisible ? (
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="space-y-3 rounded-lg border border-neutral-200 bg-neutral-50 p-3"
            noValidate
          >
            {mutation.isError && (
              <div
                className="rounded-lg border border-danger-200 bg-danger-50 px-3 py-2 text-sm text-danger-700"
                role="alert"
              >
                {getErrorMessage(mutation.error)}
              </div>
            )}

            <Input
              label="Name"
              placeholder="Category name"
              error={errors.name?.message}
              register={register('name')}
            />

            <Input
              label="Description"
              placeholder="Optional description"
              error={errors.description?.message}
              register={register('description')}
            />

            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={handleCancel}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" loading={mutation.isPending}>
                {editingCategory ? 'Update' : 'Create'}
              </Button>
            </div>
          </form>
        ) : (
          <Button variant="secondary" onClick={handleCreate} className="w-full">
            Add Category
          </Button>
        )}
      </div>
    </Modal>
  );
}
