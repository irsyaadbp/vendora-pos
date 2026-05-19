import { apiClient } from '@/core/api/client';
import type { APIResponse, PaginatedResponse } from '@/core/types/api';
import type { Product } from '@/core/types/models';

// ─── Inventory Types ──────────────────────────────────────────────────────────

export type AdjustmentType = 'stock_in' | 'stock_out' | 'adjustment';

export interface InventoryLog {
  id: string;
  product_id: string;
  user_id: string;
  adjustment_type: AdjustmentType;
  quantity_change: number;
  reason: string | null;
  created_at: string;
}

export interface StockOperationData {
  product_id: string;
  quantity: number;
}

export interface StockAdjustmentData {
  product_id: string;
  new_quantity: number;
  reason: string;
}

export interface InventoryLogsParams {
  product_id: string;
  page?: number;
  page_size?: number;
}

export interface LowStockParams {
  page?: number;
  page_size?: number;
}

// ─── Inventory API Calls ──────────────────────────────────────────────────────

/**
 * POST /inventory/stock-in — Record a stock-in operation (admin only).
 */
async function stockIn(data: StockOperationData): Promise<Product> {
  const response = await apiClient.post<APIResponse<Product>>(
    '/inventory/stock-in',
    data
  );
  return response.data.data;
}

/**
 * POST /inventory/stock-out — Record a stock-out operation (admin only).
 */
async function stockOut(data: StockOperationData): Promise<Product> {
  const response = await apiClient.post<APIResponse<Product>>(
    '/inventory/stock-out',
    data
  );
  return response.data.data;
}

/**
 * POST /inventory/adjust — Adjust stock to exact quantity (admin only).
 */
async function adjustStock(data: StockAdjustmentData): Promise<Product> {
  const response = await apiClient.post<APIResponse<Product>>(
    '/inventory/adjust',
    data
  );
  return response.data.data;
}

/**
 * GET /inventory/low-stock — List products below low-stock threshold (admin only).
 */
async function getLowStockProducts(
  params?: LowStockParams
): Promise<PaginatedResponse<Product>> {
  const response = await apiClient.get<PaginatedResponse<Product>>(
    '/inventory/low-stock',
    { params }
  );
  return response.data;
}

/**
 * GET /inventory/logs/:productId — Get inventory log history for a product (admin only).
 */
async function getProductLogs(
  productId: string,
  params?: { page?: number; page_size?: number }
): Promise<PaginatedResponse<InventoryLog>> {
  const response = await apiClient.get<PaginatedResponse<InventoryLog>>(
    `/inventory/logs/${productId}`,
    { params }
  );
  return response.data;
}

export const inventoryService = {
  stockIn,
  stockOut,
  adjustStock,
  getLowStockProducts,
  getProductLogs,
};
