import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  userService,
  type UserCreatePayload,
  type UserUpdatePayload,
  type UserListParams,
  type PasswordResetPayload,
} from '../services/user.service';

const USERS_QUERY_KEY = 'users';

/**
 * TanStack Query hook for fetching paginated user list with filters.
 */
export function useUsers(params: UserListParams) {
  return useQuery({
    queryKey: [USERS_QUERY_KEY, params],
    queryFn: () => userService.listUsers(params),
  });
}

/**
 * TanStack Query mutation for creating a new user.
 * Invalidates the users list on success.
 */
export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UserCreatePayload) => userService.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [USERS_QUERY_KEY] });
    },
  });
}

/**
 * TanStack Query mutation for updating an existing user.
 * Invalidates the users list on success.
 */
export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UserUpdatePayload }) =>
      userService.updateUser(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [USERS_QUERY_KEY] });
    },
  });
}

/**
 * TanStack Query mutation for deactivating a user.
 * Invalidates the users list on success.
 */
export function useDeactivateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => userService.deactivateUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [USERS_QUERY_KEY] });
    },
  });
}

/**
 * TanStack Query mutation for resetting a user's password.
 */
export function useResetPassword() {
  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: PasswordResetPayload }) =>
      userService.resetPassword(userId, data),
  });
}
