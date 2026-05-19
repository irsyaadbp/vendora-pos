import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  inventoryService,
  type LowStockParams,
  type StockAdjustmentData,
  type StockOperationData,
} from '../services/inventory.service';

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const inventoryKeys = {
  all: ['inventory'] as const,
  lowStock: () => [...inventoryKeys.all, 'low-stock'] as const,
  lowStockList: (params?: LowStockParams) =>
    [...inventoryKeys.lowStock(), params] as const,
  logs: () => [...inventoryKeys.all, 'logs'] as const,
  logsByProduct: (productId: string, params?: { page?: number; page_size?: number }) =>
    [...inventoryKeys.logs(), productId, params] as const,
};

// ─── Queries ──────────────────────────────────────────────────────────────────

/**
 * Fetch paginated low-stock products.
 */
export function useLowStockProducts(params?: LowStockParams) {
  return useQuery({
    queryKey: inventoryKeys.lowStockList(params),
    queryFn: () => inventoryService.getLowStockProducts(params),
  });
}

/**
 * Fetch paginated inventory logs for a specific product.
 */
export function useInventoryLogs(
  productId: string,
  params?: { page?: number; page_size?: number }
) {
  return useQuery({
    queryKey: inventoryKeys.logsByProduct(productId, params),
    queryFn: () => inventoryService.getProductLogs(productId, params),
    enabled: !!productId,
  });
}

// ─── Mutations ────────────────────────────────────────────────────────────────

/**
 * Record a stock-in operation. Invalidates low-stock and product queries on success.
 */
export function useStockIn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StockOperationData) => inventoryService.stockIn(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.all });
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

/**
 * Record a stock-out operation. Invalidates low-stock and product queries on success.
 */
export function useStockOut() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StockOperationData) => inventoryService.stockOut(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.all });
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}

/**
 * Adjust stock to exact quantity. Invalidates low-stock and product queries on success.
 */
export function useAdjustStock() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StockAdjustmentData) =>
      inventoryService.adjustStock(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: inventoryKeys.all });
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
}
