import { useMutation, useQuery } from '@tanstack/react-query';
import { posService, type TransactionCreateData } from '../services/pos.service';

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const posKeys = {
  all: ['pos'] as const,
  search: (query: string) => [...posKeys.all, 'search', query] as const,
};

// ─── Product Search Query ─────────────────────────────────────────────────────

/**
 * Search products for POS with debounced query.
 * Fetches all products when query is empty, filters when query is provided.
 */
export function usePosProductSearch(query: string) {
  return useQuery({
    queryKey: posKeys.search(query),
    queryFn: () => posService.searchProducts(query),
    staleTime: 30_000,
  });
}

// ─── Transaction Mutation ─────────────────────────────────────────────────────

/**
 * Submit a new transaction. Returns the receipt on success.
 */
export function useCreateTransaction() {
  return useMutation({
    mutationFn: (data: TransactionCreateData) =>
      posService.createTransaction(data),
  });
}
