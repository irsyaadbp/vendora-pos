"use client";

import { useState } from "react";
import { Table, type TableColumn } from "@/shared/ui";
import { useAuthStore } from "@/core/stores/auth.store";
import { useTransactions } from "../hooks/useTransactions";
import type { TransactionListParams, TransactionListItem } from "../services/transaction.service";
import type { PaymentMethod } from "@/core/types/models";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function truncateId(id: string): string {
  if (id.length <= 8) return id;
  return `${id.slice(0, 8)}…`;
}

function formatPaymentMethod(method: PaymentMethod): string {
  const labels: Record<PaymentMethod, string> = {
    cash: "Cash",
    qris: "QRIS",
    debit_card: "Debit Card",
    credit_card: "Credit Card",
  };
  return labels[method] || method;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat("id-ID", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(dateStr));
}

// ─── Payment Method Options ───────────────────────────────────────────────────

const PAYMENT_METHOD_OPTIONS = [
  { value: "", label: "All Methods" },
  { value: "cash", label: "Cash" },
  { value: "qris", label: "QRIS" },
  { value: "debit_card", label: "Debit Card" },
  { value: "credit_card", label: "Credit Card" },
];

// ─── Component ────────────────────────────────────────────────────────────────

export function TransactionHistory() {
  const user = useAuthStore((state) => state.user);
  const isAdmin = user?.role === "admin";

  const [page, setPage] = useState(1);
  const [paymentMethodFilter, setPaymentMethodFilter] = useState<PaymentMethod | "">("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const params: TransactionListParams = {
    page,
    page_size: 20,
    ...(paymentMethodFilter ? { payment_method: paymentMethodFilter } : {}),
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo ? { date_to: dateTo } : {}),
  };

  const { data, isLoading, isError } = useTransactions(params);

  function getCashierName(row: TransactionListItem): string {
    if (row.cashier_name) return row.cashier_name;
    if (!isAdmin && user) return user.full_name;
    return "—";
  }

  const columns: TableColumn<TransactionListItem>[] = [
    {
      key: "id",
      header: "ID",
      render: (row) => (
        <span className="font-mono text-xs" title={row.id}>
          {truncateId(row.id)}
        </span>
      ),
    },
    {
      key: "cashier_name",
      header: "Cashier",
      render: (row) => getCashierName(row),
    },
    {
      key: "total_amount",
      header: "Total",
      render: (row) => (
        <span className="font-medium">{formatCurrency(row.total_amount)}</span>
      ),
    },
    {
      key: "payment_method",
      header: "Payment",
      render: (row) => (
        <span className="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-700">
          {formatPaymentMethod(row.payment_method)}
        </span>
      ),
    },
    {
      key: "created_at",
      header: "Date",
      render: (row) => (
        <span className="text-sm text-neutral-600">{formatDate(row.created_at)}</span>
      ),
    },
  ];

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  const handlePaymentMethodChange = (value: string) => {
    setPaymentMethodFilter(value as PaymentMethod | "");
    setPage(1);
  };

  const handleDateFromChange = (value: string) => {
    setDateFrom(value);
    setPage(1);
  };

  const handleDateToChange = (value: string) => {
    setDateTo(value);
    setPage(1);
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3">
        {/* Payment method filter */}
        <div className="w-full sm:w-44">
          <label
            htmlFor="payment-method-filter"
            className="mb-1.5 block text-sm font-medium text-neutral-700"
          >
            Payment Method
          </label>
          <select
            id="payment-method-filter"
            value={paymentMethodFilter}
            onChange={(e) => handlePaymentMethodChange(e.target.value)}
            className="w-full appearance-none rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          >
            {PAYMENT_METHOD_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Date from filter */}
        <div className="w-full sm:w-44">
          <label
            htmlFor="date-from-filter"
            className="mb-1.5 block text-sm font-medium text-neutral-700"
          >
            From
          </label>
          <input
            id="date-from-filter"
            type="date"
            value={dateFrom}
            onChange={(e) => handleDateFromChange(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          />
        </div>

        {/* Date to filter */}
        <div className="w-full sm:w-44">
          <label
            htmlFor="date-to-filter"
            className="mb-1.5 block text-sm font-medium text-neutral-700"
          >
            To
          </label>
          <input
            id="date-to-filter"
            type="date"
            value={dateTo}
            onChange={(e) => handleDateToChange(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm transition-colors focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          />
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
          <span className="ml-2 text-sm text-neutral-500">Loading transactions…</span>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="rounded-lg border border-danger-200 bg-danger-50 p-4 text-sm text-danger-700">
          Failed to load transactions. Please try again.
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && data && (
        <Table<TransactionListItem>
          columns={columns}
          data={data.data}
          pagination={{
            page: data.meta.page,
            totalPages: data.meta.total_pages,
          }}
          onPageChange={handlePageChange}
          emptyMessage="No transactions found"
        />
      )}
    </div>
  );
}
