import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { authService } from '../services/auth.service';

/**
 * TanStack Query mutation for user login.
 * On success, redirects to the home page.
 */
export function useLogin() {
  const router = useRouter();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authService.login(email, password),
    onSuccess: () => {
      router.push('/');
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
