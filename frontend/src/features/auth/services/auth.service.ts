import axios from 'axios';
import { useAuthStore } from '@/core/stores/auth.store';
import type { APIResponse } from '@/core/types/api';
import type { User } from '@/core/types/models';

/**
 * Auth API client — calls the Next.js proxy routes (/api/auth/*)
 * which handle HTTP-only cookie management on the frontend domain.
 */
const authClient = axios.create({
  baseURL: '/api/auth',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

/**
 * POST /api/auth/login — Authenticate with email and password.
 * The proxy route sets access_token and refresh_token as HTTP-only cookies.
 */
async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await authClient.post<APIResponse<LoginResponse>>(
    '/login',
    { email, password }
  );

  const data = response.data.data;
  const { access_token, user } = data;

  if (!user) {
    throw new Error('Login response missing user data');
  }

  // Store auth state in Zustand (memory only)
  useAuthStore.getState().setAuth(user, access_token);

  return data;
}

/**
 * POST /api/auth/refresh — Refresh the access token.
 * The proxy route updates the HTTP-only cookies.
 */
async function refresh(): Promise<string> {
  const response = await authClient.post<APIResponse<{ access_token: string }>>(
    '/refresh'
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
 * POST /api/auth/logout — Invalidate session.
 * The proxy route clears all HTTP-only cookies.
 */
async function logout(): Promise<void> {
  await authClient.post('/logout');
  useAuthStore.getState().clearAuth();
}

/**
 * GET /api/auth/me — Get current user info.
 * The proxy route reads the access_token cookie and calls the backend.
 */
async function me(): Promise<{ user: User; access_token: string }> {
  const response = await authClient.get<APIResponse<{ user: User; access_token: string }>>('/me');
  return response.data.data;
}

export const authService = {
  login,
  refresh,
  logout,
  me,
};
