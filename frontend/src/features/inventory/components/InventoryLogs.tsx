'use client';

import { useState } from 'react';
import { Table, SearchInput } from '@/shared/ui';
import type { TableColumn } from '@/shared/ui';
import { formatDate } from '@/shared/utils/formatters';
import { usePagination } from '@/shared/hooks/usePagination';
import { useInventoryLogs } from '../hooks/useInventory';
import type { InventoryLog } from '../services/inventory.service';

type InventoryLogRow = InventoryLog & Record<string, unknown>;

function getAdjustmentTypeLabel(type: string): string {
  switch (type) {
    case 'stock_in':
      return 'Stock In';
    case 'stock_out':
      return 'Stock Out';
    case 'adjustment':
      return 'Adjustment';
    default:
      return type;
  }
}

function getAdjustmentTypeBadgeClass(type: string): string {
  switch (type) {
    case 'stock_in':
      return 'bg-success-100 text-success-700';
    case 'stock_out':
      return 'bg-danger-100 text-danger-700';
    case 'adjustment':
      return 'bg-warning-100 text-warning-700';
    default:
      return 'bg-neutral-100 text-neutral-600';
  }
}

interface InventoryLogsProps {
  productId?: string;
}

export function InventoryLogs({ productId: initialProductId }: InventoryLogsProps) {
  const [productId, setProductId] = useState(initialProductId ?? '');
  const { page, goToPage } = usePagination({ totalCount: 0 });

  const { data, isLoading } = useInventoryLogs(productId, {
    page,
    page_size: 20,
  });

  const columns: TableColumn<InventoryLogRow>[] = [
    {
      key: 'adjustment_type',
      header: 'Type',
      render: (row) => (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${getAdjustmentTypeBadgeClass(row.adjustment_type)}`}
        >
          {getAdjustmentTypeLabel(row.adjustment_type)}
        </span>
      ),
    },
    {
      key: 'quantity_change',
      header: 'Quantity Change',
      render: (row) => (
        <span
          className={`font-medium ${
            row.quantity_change > 0
              ? 'text-success-600'
              : row.quantity_change < 0
                ? 'text-danger-600'
                : 'text-neutral-600'
          }`}
        >
          {row.quantity_change > 0 ? '+' : ''}
          {row.quantity_change}
        </span>
      ),
    },
    {
      key: 'reason',
      header: 'Reason',
      render: (row) => (
        <span className="text-neutral-600">{row.reason ?? '—'}</span>
      ),
    },
    {
      key: 'created_at',
      header: 'Date',
      render: (row) => (
        <span className="text-neutral-600">{formatDate(row.created_at)}</span>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {!initialProductId && (
        <div className="w-full max-w-sm">
          <SearchInput
            value={productId}
            onChange={(value) => {
              setProductId(value);
              goToPage(1);
            }}
            placeholder="Enter product ID to view logs..."
            debounceMs={500}
          />
        </div>
      )}

      {!productId ? (
        <div className="flex items-center justify-center rounded-lg border border-neutral-200 bg-neutral-50 py-12">
          <p className="text-sm text-neutral-500">
            Enter a product ID to view inventory logs
          </p>
        </div>
      ) : isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
        </div>
      ) : (
        <Table<InventoryLogRow>
          columns={columns}
          data={(data?.data ?? []) as InventoryLogRow[]}
          pagination={{
            page,
            totalPages: data?.meta?.total_pages ?? 1,
          }}
          onPageChange={goToPage}
          emptyMessage="No inventory logs found for this product"
        />
      )}
    </div>
  );
}
