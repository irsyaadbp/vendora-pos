'use client';

import { Table } from '@/shared/ui';
import type { TableColumn } from '@/shared/ui';
import type { Product } from '@/core/types/models';
import { formatCurrency } from '@/shared/utils/formatters';
import { usePagination } from '@/shared/hooks/usePagination';
import { useLowStockProducts } from '../hooks/useInventory';

type ProductRow = Product & Record<string, unknown>;

export function LowStockList() {
  const { page, goToPage } = usePagination({ totalCount: 0 });

  const { data, isLoading } = useLowStockProducts({ page, page_size: 20 });

  const columns: TableColumn<ProductRow>[] = [
    {
      key: 'name',
      header: 'Product Name',
      render: (row) => (
        <span className="font-medium text-neutral-900">{row.name}</span>
      ),
    },
    {
      key: 'sku',
      header: 'SKU',
    },
    {
      key: 'stock',
      header: 'Current Stock',
      render: (row) => (
        <span className="font-semibold text-danger-600">{row.stock}</span>
      ),
    },
    {
      key: 'price',
      header: 'Price',
      render: (row) => <span>{formatCurrency(row.price)}</span>,
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
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  return (
    <Table<ProductRow>
      columns={columns}
      data={(data?.data ?? []) as ProductRow[]}
      pagination={{
        page,
        totalPages: data?.meta?.total_pages ?? 1,
      }}
      onPageChange={goToPage}
      emptyMessage="No low-stock products found"
    />
  );
}
