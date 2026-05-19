'use client';

import { useEffect, useState } from 'react';
import { useAuthStore } from '@/core/stores/auth.store';
import { authService } from '../services/auth.service';
import { apiClient } from '@/core/api/client';
import type { APIResponse } from '@/core/types/api';
import type { User } from '@/core/types/models';

/**
 * Rehydrates auth state on page refresh.
 * If the refresh_token cookie exists but the Zustand store is empty,
 * calls /auth/refresh to get a new access token, then fetches user info.
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

    // Check if user_role cookie exists (indicates a session)
    const hasSession = document.cookie.includes('user_role=');
    if (!hasSession) {
      setIsHydrating(false);
      return;
    }

    // Try to refresh the token and get user info
    async function hydrate() {
      try {
        // Refresh token to get new access token
        const newToken = await authService.refresh();

        // Fetch current user info using the new token
        const response = await apiClient.get<APIResponse<User>>('/auth/me');
        const userData = response.data.data;

        setAuth(userData, newToken);
      } catch {
        // Refresh failed — clear cookies and state
        clearAuth();
        document.cookie = 'user_role=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
      } finally {
        setIsHydrating(false);
      }
    }

    hydrate();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { isHydrating };
}
