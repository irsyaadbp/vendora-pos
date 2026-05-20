import { useQuery } from '@tanstack/react-query';
import { authService } from '../services/auth.service';

/**
 * TanStack Query hook to fetch the current authenticated user's profile.
 *
 * Calls GET /api/auth/me → backend GET /api/v1/auth/me.
 * The response includes user.role which page components use for RBAC.
 *
 * retry=false — a 401 surfaces immediately; the axios interceptor in
 * client.ts handles the refresh before this query even sees a 401.
 * staleTime=5min — avoids redundant refetches on window focus.
 */
export function useMe() {
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const data = await authService.me();
      return data.user;
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}
