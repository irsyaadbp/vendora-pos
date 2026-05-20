import { useMutation } from '@tanstack/react-query';
import { useSearchParams, useRouter } from 'next/navigation';
import { authService } from '../services/auth.service';

/**
 * TanStack Query mutation for user login.
 * On success, performs a client-side transition to the callbackUrl (if present)
 * or the home page.
 *
 * Uses Next.js router.push to preserve in-memory Zustand auth state, avoiding
 * redundant refresh/profile calls on mount. Cookies are automatically attached
 * by the browser so server-side middleware sees them instantly.
 */
export function useLogin() {
  const searchParams = useSearchParams();
  const router = useRouter();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authService.login(email, password),
    onSuccess: () => {
      const callbackUrl = searchParams.get('callbackUrl') || '/';
      router.push(callbackUrl);
      router.refresh();
    },
  });
}

/**
 * TanStack Query mutation for user logout.
 * On success, performs a client-side transition to the login page.
 */
export function useLogout() {
  const router = useRouter();

  return useMutation({
    mutationFn: () => authService.logout(),
    onSuccess: () => {
      router.push('/login');
      router.refresh();
    },
  });
}
