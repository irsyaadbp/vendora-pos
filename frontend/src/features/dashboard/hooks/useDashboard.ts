import { useQuery } from '@tanstack/react-query';
import { dashboardService } from '../services/dashboard.service';

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const dashboardKeys = {
  all: ['dashboard'] as const,
  metrics: () => [...dashboardKeys.all, 'metrics'] as const,
};

// ─── Queries ──────────────────────────────────────────────────────────────────

/**
 * Fetch dashboard metrics. Refetches every 60 seconds to keep data fresh.
 */
export function useDashboardMetrics() {
  return useQuery({
    queryKey: dashboardKeys.metrics(),
    queryFn: () => dashboardService.getMetrics(),
    refetchInterval: 60_000,
  });
}
