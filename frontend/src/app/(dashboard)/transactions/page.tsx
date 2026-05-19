"use client";

import { useAuthStore } from "@/core/stores/auth.store";
import { TransactionHistory } from "@/features/pos/components/TransactionHistory";

export default function TransactionsPage() {
  const user = useAuthStore((state) => state.user);
  const isAdmin = user?.role === "admin";

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-neutral-900">
          Transaction History
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          {isAdmin
            ? "View all transactions with filters"
            : "View your transaction history"}
        </p>
      </div>

      {/* Transaction History */}
      <TransactionHistory />
    </div>
  );
}
