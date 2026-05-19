import { apiClient } from '@/core/api/client';
import type { APIResponse, PaginatedResponse } from '@/core/types/api';
import type { User, UserRole } from '@/core/types/models';

export interface UserCreatePayload {
  full_name: string;
  email: string;
  password: string;
  role: UserRole;
}

export interface UserUpdatePayload {
  full_name?: string;
  email?: string;
  role?: UserRole;
  is_active?: boolean;
}

export interface UserListParams {
  page?: number;
  page_size?: number;
  search?: string;
  role?: UserRole | '';
  is_active?: boolean | '';
}

export interface PasswordResetPayload {
  new_password: string;
}

/**
 * GET /users — List users with search, filters, and pagination.
 */
async function listUsers(params: UserListParams): Promise<PaginatedResponse<User>> {
  const queryParams: Record<string, string> = {};

  if (params.page) queryParams.page = String(params.page);
  if (params.page_size) queryParams.page_size = String(params.page_size);
  if (params.search) queryParams.search = params.search;
  if (params.role) queryParams.role = params.role;
  if (params.is_active !== undefined && params.is_active !== '') {
    queryParams.is_active = String(params.is_active);
  }

  const response = await apiClient.get<PaginatedResponse<User>>('/users', {
    params: queryParams,
  });

  return response.data;
}

/**
 * POST /users — Create a new user.
 */
async function createUser(data: UserCreatePayload): Promise<User> {
  const response = await apiClient.post<APIResponse<User>>('/users', data);
  return response.data.data;
}

/**
 * PUT /users/:id — Update an existing user.
 */
async function updateUser(userId: string, data: UserUpdatePayload): Promise<User> {
  const response = await apiClient.put<APIResponse<User>>(`/users/${userId}`, data);
  return response.data.data;
}

/**
 * PATCH /users/:id/deactivate — Deactivate a user account.
 */
async function deactivateUser(userId: string): Promise<User> {
  const response = await apiClient.patch<APIResponse<User>>(
    `/users/${userId}/deactivate`
  );
  return response.data.data;
}

/**
 * POST /users/:id/reset-password — Reset a user's password.
 */
async function resetPassword(userId: string, data: PasswordResetPayload): Promise<void> {
  await apiClient.post<APIResponse<null>>(
    `/users/${userId}/reset-password`,
    data
  );
}

export const userService = {
  listUsers,
  createUser,
  updateUser,
  deactivateUser,
  resetPassword,
};
