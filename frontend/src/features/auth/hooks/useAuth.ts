import { useMutation } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { authService } from '../services/auth.service';

/**
 * TanStack Query mutation for user login.
 * On success, redirects to the callbackUrl (if present) or home page.
 * Uses window.location for a full navigation to ensure the freshly-set
 * user_role cookie is sent with the request to the middleware.
 */
export function useLogin() {
  const searchParams = useSearchParams();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authService.login(email, password),
    onSuccess: () => {
      const callbackUrl = searchParams.get('callbackUrl') || '/';
      window.location.href = callbackUrl;
    },
  });
}

/**
 * TanStack Query mutation for user logout.
 * On success, redirects to the login page.
 */
export function useLogout() {
  const router = useRouter();

  return useMutation({
    mutationFn: () => authService.logout(),
    onSuccess: () => {
      router.push('/login');
    },
  });
}
