import { apiClient } from '@/core/api/client';
import { useAuthStore } from '@/core/stores/auth.store';
import type { APIResponse } from '@/core/types/api';
import type { User } from '@/core/types/models';

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

/**
 * POST /auth/login — Authenticate with email and password.
 * Stores access token in auth store and sets user_role cookie.
 */
async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await apiClient.post<APIResponse<LoginResponse>>(
    '/auth/login',
    { email, password }
  );

  const data = response.data.data;
  const { access_token, user } = data;

  if (!user) {
    throw new Error('Login response missing user data');
  }

  // Store auth state in Zustand (memory only)
  useAuthStore.getState().setAuth(user, access_token);

  // Set user_role cookie for middleware route protection (non-HTTP-only)
  document.cookie = `user_role=${user.role}; path=/; SameSite=Lax`;

  return data;
}

/**
 * POST /auth/refresh — Refresh the access token using the HTTP-only refresh cookie.
 * Returns a new access token.
 */
async function refresh(): Promise<string> {
  const response = await apiClient.post<APIResponse<{ access_token: string }>>(
    '/auth/refresh'
  );

  const { access_token } = response.data.data;

  // Update access token in auth store
  const authStore = useAuthStore.getState();
  const currentUser = authStore.user;
  if (currentUser) {
    authStore.setAuth(currentUser, access_token);
  }

  return access_token;
}

/**
 * POST /auth/logout — Invalidate the current refresh token.
 * Clears auth store and user_role cookie.
 */
async function logout(): Promise<void> {
  await apiClient.post('/auth/logout');

  // Clear auth state
  useAuthStore.getState().clearAuth();

  // Clear user_role cookie
  document.cookie = 'user_role=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
}

export const authService = {
  login,
  refresh,
  logout,
};
