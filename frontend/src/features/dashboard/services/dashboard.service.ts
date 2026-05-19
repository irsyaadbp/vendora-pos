import { apiClient } from '@/core/api/client';
import type { APIResponse } from '@/core/types/api';
import type { Product } from '@/core/types/models';

// ─── Dashboard Types ──────────────────────────────────────────────────────────

export interface RecentTransaction {
  id: string;
  cashier_name: string;
  total_amount: number;
  created_at: string;
}

export interface DashboardMetrics {
  today_sales: number;
  today_transaction_count: number;
  low_stock_products: Product[];
  active_staff_count: number;
  recent_transactions: RecentTransaction[];
  errors: Record<string, string> | null;
}

// ─── Dashboard API Calls ──────────────────────────────────────────────────────

/**
 * GET /dashboard — Retrieve aggregated dashboard metrics (admin only).
 */
async function getMetrics(): Promise<DashboardMetrics> {
  const response = await apiClient.get<APIResponse<DashboardMetrics>>(
    '/dashboard'
  );
  return response.data.data;
}

export const dashboardService = {
  getMetrics,
};
