import { apiClient } from '@/core/api/client';
import type { PaginatedResponse } from '@/core/types/api';
import type { PaymentMethod } from '@/core/types/models';

// ─── Transaction Types ────────────────────────────────────────────────────────

export interface TransactionListItem {
  id: string;
  cashier_id: string;
  cashier_name?: string;
  total_amount: number;
  discount_amount: number;
  payment_method: PaymentMethod;
  status: string;
  created_at: string;
  [key: string]: unknown;
}

export interface TransactionListParams {
  page?: number;
  page_size?: number;
  cashier_id?: string;
  payment_method?: PaymentMethod | '';
  date_from?: string;
  date_to?: string;
}

// ─── Transaction API Calls ────────────────────────────────────────────────────

/**
 * GET /transactions — List transactions with filters and pagination.
 * Staff users see only their own transactions.
 * Admin users see all transactions with optional filters.
 */
async function listTransactions(
  params: TransactionListParams
): Promise<PaginatedResponse<TransactionListItem>> {
  const queryParams: Record<string, string> = {};

  if (params.page) queryParams.page = String(params.page);
  if (params.page_size) queryParams.page_size = String(params.page_size);
  if (params.cashier_id) queryParams.cashier_id = params.cashier_id;
  if (params.payment_method) queryParams.payment_method = params.payment_method;
  if (params.date_from) queryParams.date_from = params.date_from;
  if (params.date_to) queryParams.date_to = params.date_to;

  const response = await apiClient.get<PaginatedResponse<TransactionListItem>>(
    '/transactions/',
    { params: queryParams }
  );

  return response.data;
}

export const transactionService = {
  listTransactions,
};
