'use client';

import { useState } from 'react';
import { Button } from '@/shared/ui';
import { StockOperationForm } from '@/features/inventory/components/StockOperationForm';
import { StockAdjustmentForm } from '@/features/inventory/components/StockAdjustmentForm';
import { LowStockList } from '@/features/inventory/components/LowStockList';
import { InventoryLogs } from '@/features/inventory/components/InventoryLogs';

type TabKey = 'operations' | 'low-stock' | 'logs';

const tabs: { key: TabKey; label: string }[] = [
  { key: 'operations', label: 'Stock Operations' },
  { key: 'low-stock', label: 'Low Stock Products' },
  { key: 'logs', label: 'Inventory Logs' },
];

export default function InventoryPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('operations');
  const [isStockInOpen, setIsStockInOpen] = useState(false);
  const [isStockOutOpen, setIsStockOutOpen] = useState(false);
  const [isAdjustOpen, setIsAdjustOpen] = useState(false);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-neutral-900">
          Inventory Management
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          Manage stock levels, record movements, and monitor low-stock products
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-neutral-200">
        <nav className="-mb-px flex gap-6" aria-label="Inventory tabs">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-neutral-500 hover:border-neutral-300 hover:text-neutral-700'
              }`}
              aria-current={activeTab === tab.key ? 'page' : undefined}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'operations' && (
        <div className="space-y-6">
          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => setIsStockInOpen(true)}>Stock In</Button>
            <Button variant="secondary" onClick={() => setIsStockOutOpen(true)}>
              Stock Out
            </Button>
            <Button variant="secondary" onClick={() => setIsAdjustOpen(true)}>
              Adjust Stock
            </Button>
          </div>

          {/* Info Panel */}
          <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-6">
            <h3 className="text-sm font-medium text-neutral-900">
              Stock Operations
            </h3>
            <p className="mt-2 text-sm text-neutral-600">
              Use the buttons above to record stock movements. Stock-in increases
              inventory, stock-out decreases it, and adjustments set stock to an
              exact quantity with a mandatory reason.
            </p>
            <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-neutral-600">
              <li>
                <strong>Stock In:</strong> Record incoming inventory (1 - 999,999
                units)
              </li>
              <li>
                <strong>Stock Out:</strong> Record outgoing inventory (cannot
                exceed current stock)
              </li>
              <li>
                <strong>Adjust:</strong> Set exact stock level with a reason for
                audit trail
              </li>
            </ul>
          </div>

          {/* Modals */}
          <StockOperationForm
            isOpen={isStockInOpen}
            onClose={() => setIsStockInOpen(false)}
            operationType="stock_in"
          />
          <StockOperationForm
            isOpen={isStockOutOpen}
            onClose={() => setIsStockOutOpen(false)}
            operationType="stock_out"
          />
          <StockAdjustmentForm
            isOpen={isAdjustOpen}
            onClose={() => setIsAdjustOpen(false)}
          />
        </div>
      )}

      {activeTab === 'low-stock' && <LowStockList />}

      {activeTab === 'logs' && <InventoryLogs />}
    </div>
  );
}
