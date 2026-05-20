'use client';

import { useDashboardMetrics } from '@/features/dashboard/hooks/useDashboard';
import { SalesWidget } from '@/features/dashboard/components/SalesWidget';
import { TransactionCountWidget } from '@/features/dashboard/components/TransactionCountWidget';
import { LowStockWidget } from '@/features/dashboard/components/LowStockWidget';
import { ActiveStaffWidget } from '@/features/dashboard/components/ActiveStaffWidget';
import { RecentTransactions } from '@/features/dashboard/components/RecentTransactions';

export default function DashboardPage() {
  const { data: metrics, isLoading, isError } = useDashboardMetrics();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Dashboard</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Overview of today&apos;s business performance
          </p>
        </div>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-lg border border-neutral-200 bg-neutral-100"
            />
          ))}
        </div>
        <div className="h-64 animate-pulse rounded-lg border border-neutral-200 bg-neutral-100" />
      </div>
    );
  }

  if (isError || !metrics) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Dashboard</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Overview of today&apos;s business performance
          </p>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6">
          <p className="text-sm text-red-700">
            Failed to load dashboard metrics. Please try again later.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-neutral-900">Dashboard</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Overview of today&apos;s business performance
        </p>
      </div>

      {/* Partial failure warning */}
      {metrics.errors && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm text-amber-700">
            Some metrics could not be loaded:{' '}
            {Object.values(metrics.errors).join(', ')}
          </p>
        </div>
      )}

      {/* Metric Widgets Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        <SalesWidget totalSales={metrics.today_sales} />
        <TransactionCountWidget count={metrics.today_transaction_count} />
        <LowStockWidget products={metrics.low_stock_products} />
        <ActiveStaffWidget count={metrics.active_staff_count} />
      </div>

      {/* Recent Transactions */}
      <RecentTransactions transactions={metrics.recent_transactions} />
    </div>
  );
}
