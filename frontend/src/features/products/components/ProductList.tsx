'use client';

import { useState } from 'react';
import { Table, SearchInput, Select, Button } from '@/shared/ui';
import type { TableColumn } from '@/shared/ui';
import type { Product } from '@/core/types/models';

type ProductRow = Product & Record<string, unknown>;
import { formatCurrency } from '@/shared/utils/formatters';
import { usePagination } from '@/shared/hooks/usePagination';
import { useProducts, useCategories, useDeleteProduct } from '../hooks/useProducts';

interface ProductListProps {
  onEdit: (product: Product) => void;
  onCreate: () => void;
}

export function ProductList({ onEdit, onCreate }: ProductListProps) {
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  const { data: categoriesData } = useCategories({ page: 1, page_size: 100 });

  const { page, goToPage } = usePagination({
    totalCount: 0,
  });

  const searchParams = {
    q: search || undefined,
    category_id: categoryFilter || undefined,
    page,
    page_size: 20,
  };

  const { data, isLoading } = useProducts(searchParams);
  const deleteProduct = useDeleteProduct();

  const handleDelete = (productId: string) => {
    if (window.confirm('Are you sure you want to delete this product?')) {
      deleteProduct.mutate(productId);
    }
  };

  const categoryOptions = [
    { value: '', label: 'All Categories' },
    ...(categoriesData?.data?.map((cat) => ({
      value: cat.id,
      label: cat.name,
    })) ?? []),
  ];

  const columns: TableColumn<ProductRow>[] = [
    {
      key: 'name',
      header: 'Name',
      render: (row) => (
        <div className="flex items-center gap-2">
          <span className="font-medium text-neutral-900">{row.name}</span>
          {row.low_stock && (
            <span className="inline-flex items-center rounded-full bg-danger-100 px-2 py-0.5 text-xs font-medium text-danger-700">
              Low Stock
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'sku',
      header: 'SKU',
    },
    {
      key: 'barcode',
      header: 'Barcode',
      render: (row) => <span>{row.barcode ?? '—'}</span>,
    },
    {
      key: 'price',
      header: 'Price',
      render: (row) => <span>{formatCurrency(row.price)}</span>,
    },
    {
      key: 'stock',
      header: 'Stock',
      render: (row) => (
        <span
          className={
            row.low_stock ? 'font-semibold text-danger-600' : 'text-neutral-900'
          }
        >
          {row.stock}
        </span>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (row) => (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
            row.is_active
              ? 'bg-success-100 text-success-700'
              : 'bg-neutral-100 text-neutral-600'
          }`}
        >
          {row.is_active ? 'Active' : 'Inactive'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => onEdit(row)}>
            Edit
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDelete(row.id)}
            className="text-danger-600 hover:text-danger-700"
          >
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center gap-3">
          <div className="w-full max-w-sm">
            <SearchInput
              value={search}
              onChange={(value) => {
                setSearch(value);
                goToPage(1);
              }}
              placeholder="Search by name, SKU, or barcode..."
              debounceMs={300}
            />
          </div>
          <div className="w-48">
            <Select
              options={categoryOptions}
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                goToPage(1);
              }}
              placeholder="All Categories"
            />
          </div>
        </div>
        <Button onClick={onCreate}>Add Product</Button>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
        </div>
      ) : (
        <Table<ProductRow>
          columns={columns}
          data={(data?.data ?? []) as ProductRow[]}
          pagination={{
            page,
            totalPages: data?.meta?.total_pages ?? 1,
          }}
          onPageChange={goToPage}
          emptyMessage="No products found"
        />
      )}
    </div>
  );
}
