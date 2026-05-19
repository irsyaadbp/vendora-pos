'use client';

import { formatCurrency, formatDate } from '@/shared/utils/formatters';
import type { RecentTransaction } from '../services/dashboard.service';

interface RecentTransactionsProps {
  transactions: RecentTransaction[];
}

export function RecentTransactions({ transactions }: RecentTransactionsProps) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-6">
      <h3 className="text-sm font-medium text-neutral-900">
        Recent Transactions
      </h3>

      {transactions.length === 0 ? (
        <p className="mt-4 text-sm text-neutral-500">
          No transactions recorded today.
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-neutral-200 text-neutral-500">
                <th className="pb-2 pr-4 font-medium">Cashier</th>
                <th className="pb-2 pr-4 font-medium">Amount</th>
                <th className="pb-2 font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {transactions.map((txn) => (
                <tr key={txn.id}>
                  <td className="py-2.5 pr-4 text-neutral-700">
                    {txn.cashier_name}
                  </td>
                  <td className="py-2.5 pr-4 font-medium text-neutral-900">
                    {formatCurrency(txn.total_amount)}
                  </td>
                  <td className="py-2.5 text-neutral-500">
                    {formatDate(txn.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
