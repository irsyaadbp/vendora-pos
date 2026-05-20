'use client';

import { useEffect, useState } from 'react';
import { useAuthStore } from '@/core/stores/auth.store';
import { authService } from '../services/auth.service';

/**
 * Rehydrates auth state on page load.
 * Optimistic flow:
 * 1. Tries to call /api/auth/me using the current access_token cookie first (1 network call).
 * 2. If it fails (due to missing or expired access_token), attempts /api/auth/refresh to rotate cookies.
 * 3. If refresh succeeds, retries /api/auth/me to fetch profile.
 * 4. If everything fails, clears the auth state.
 */
export function useAuthHydration() {
  const [isHydrating, setIsHydrating] = useState(true);
  const { user, accessToken, setAuth, clearAuth } = useAuthStore();

  useEffect(() => {
    // If already hydrated (user exists in store), skip
    if (user && accessToken) {
      setIsHydrating(false);
      return;
    }

    async function hydrate() {
      try {
        try {
          // 1. Optimistic: Try to get user profile and access token directly (saves network calls if active)
          const { user: userData, access_token: token } = await authService.me();
          setAuth(userData, token);
        } catch (meError) {
          // 2. Fallback: If /me failed (e.g. token expired/missing), try to refresh cookies
          const token = await authService.refresh();
          // 3. Retry /me with the fresh cookies
          const { user: userData } = await authService.me();
          setAuth(userData, token);
        }
      } catch (finalError) {
        // 4. Everything failed — user session is completely invalid/expired
        clearAuth();
      } finally {
        setIsHydrating(false);
      }
    }

    hydrate();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { isHydrating };
}
