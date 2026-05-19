'use client';

import { useState } from 'react';
import { Button } from '@/shared/ui';
import type { Product } from '@/core/types/models';
import { ProductList } from '@/features/products/components/ProductList';
import { ProductForm } from '@/features/products/components/ProductForm';
import { CategoryManager } from '@/features/products/components/CategoryManager';

export default function ProductsPage() {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isCategoryManagerOpen, setIsCategoryManagerOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);

  const handleCreate = () => {
    setEditingProduct(null);
    setIsFormOpen(true);
  };

  const handleEdit = (product: Product) => {
    setEditingProduct(product);
    setIsFormOpen(true);
  };

  const handleCloseForm = () => {
    setIsFormOpen(false);
    setEditingProduct(null);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Products</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Manage your product catalog and categories
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => setIsCategoryManagerOpen(true)}
        >
          Manage Categories
        </Button>
      </div>

      {/* Product List */}
      <ProductList onEdit={handleEdit} onCreate={handleCreate} />

      {/* Product Form Modal */}
      <ProductForm
        isOpen={isFormOpen}
        onClose={handleCloseForm}
        product={editingProduct}
      />

      {/* Category Manager Modal */}
      <CategoryManager
        isOpen={isCategoryManagerOpen}
        onClose={() => setIsCategoryManagerOpen(false)}
      />
    </div>
  );
}
