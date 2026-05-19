import { apiClient } from '@/core/api/client';
import type { APIResponse, PaginatedResponse } from '@/core/types/api';
import type { PaymentMethod, Product } from '@/core/types/models';

// ─── Transaction Types ────────────────────────────────────────────────────────

export interface TransactionItemCreate {
  product_id: string;
  quantity: number;
}

export interface TransactionCreateData {
  items: TransactionItemCreate[];
  discount_type?: 'percentage' | 'fixed' | null;
  discount_value?: number | null;
  payment_method: PaymentMethod;
}

export interface ReceiptItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface TransactionReceipt {
  id: string;
  items: ReceiptItem[];
  total_amount: number;
  discount_amount: number;
  payment_method: PaymentMethod;
  cashier_name: string;
  created_at: string;
}

// ─── POS API Calls ────────────────────────────────────────────────────────────

/**
 * GET /products/search — Search products by name/SKU/barcode for POS.
 */
async function searchProducts(query: string): Promise<PaginatedResponse<Product>> {
  const params: Record<string, string | number> = { page_size: 20 };
  if (query) {
    params.q = query;
  }
  const response = await apiClient.get<PaginatedResponse<Product>>(
    '/products/search',
    { params }
  );
  return response.data;
}

/**
 * POST /transactions — Submit a new transaction.
 */
async function createTransaction(
  data: TransactionCreateData
): Promise<TransactionReceipt> {
  const response = await apiClient.post<APIResponse<TransactionReceipt>>(
    '/transactions/',
    data
  );
  return response.data.data;
}

export const posService = {
  searchProducts,
  createTransaction,
};
