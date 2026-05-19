import { useQuery } from '@tanstack/react-query';
import {
  transactionService,
  type TransactionListParams,
} from '../services/transaction.service';

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const transactionKeys = {
  all: ['transactions'] as const,
  lists: () => [...transactionKeys.all, 'list'] as const,
  list: (params: TransactionListParams) =>
    [...transactionKeys.lists(), params] as const,
};

// ─── Transaction Queries ──────────────────────────────────────────────────────

/**
 * Fetch paginated transactions with filters.
 * Role-scoped: staff sees own, admin sees all.
 */
export function useTransactions(params: TransactionListParams) {
  return useQuery({
    queryKey: transactionKeys.list(params),
    queryFn: () => transactionService.listTransactions(params),
  });
}
