import { describe, it, expect } from 'vitest';
import { NextRequest } from 'next/server';
import { middleware } from '@/middleware';

/**
 * Helper to create a NextRequest with optional cookies.
 */
function createRequest(
  pathname: string,
  cookies: Record<string, string> = {}
): NextRequest {
  const url = new URL(pathname, 'http://localhost:3000');
  const request = new NextRequest(url);
  for (const [name, value] of Object.entries(cookies)) {
    request.cookies.set(name, value);
  }
  return request;
}

describe('middleware', () => {
  describe('public routes', () => {
    it('allows unauthenticated access to /login', () => {
      const request = createRequest('/login');
      const response = middleware(request);
      // NextResponse.next() has no Location header
      expect(response.headers.get('Location')).toBeNull();
    });

    it('redirects authenticated users away from /login to /', () => {
      const request = createRequest('/login', { refresh_token: 'some-token' });
      const response = middleware(request);
      expect(response.headers.get('Location')).toBe('http://localhost:3000/');
    });
  });

  describe('unauthenticated access to protected routes', () => {
    it('redirects to /login with callbackUrl when no refresh_token', () => {
      const request = createRequest('/dashboard');
      const response = middleware(request);
      const location = response.headers.get('Location');
      expect(location).toContain('/login');
      expect(location).toContain('callbackUrl=%2Fdashboard');
    });

    it('redirects to /login for /pos without auth', () => {
      const request = createRequest('/pos');
      const response = middleware(request);
      const location = response.headers.get('Location');
      expect(location).toContain('/login');
      expect(location).toContain('callbackUrl=%2Fpos');
    });

    it('redirects to /login for /users without auth', () => {
      const request = createRequest('/users');
      const response = middleware(request);
      expect(response.headers.get('Location')).toContain('/login');
    });

    it('redirects to /login for /inventory without auth', () => {
      const request = createRequest('/inventory');
      const response = middleware(request);
      expect(response.headers.get('Location')).toContain('/login');
    });
  });

  describe('authenticated access', () => {
    it('allows authenticated user to access /dashboard', () => {
      const request = createRequest('/dashboard', { refresh_token: 'some-token' });
      const response = middleware(request);
      expect(response.headers.get('Location')).toBeNull();
    });

    it('allows authenticated user to access /users', () => {
      const request = createRequest('/users', { refresh_token: 'some-token' });
      const response = middleware(request);
      expect(response.headers.get('Location')).toBeNull();
    });

    it('allows authenticated user to access /inventory', () => {
      const request = createRequest('/inventory', { refresh_token: 'some-token' });
      const response = middleware(request);
      expect(response.headers.get('Location')).toBeNull();
    });

    it('allows authenticated user to access /products', () => {
      const request = createRequest('/products', { refresh_token: 'some-token' });
      const response = middleware(request);
      expect(response.headers.get('Location')).toBeNull();
    });

    it('allows authenticated user to access /pos', () => {
      const request = createRequest('/pos', { refresh_token: 'some-token' });
      const response = middleware(request);
      expect(response.headers.get('Location')).toBeNull();
    });

    it('allows authenticated user to access /transactions', () => {
      const request = createRequest('/transactions', { refresh_token: 'some-token' });
      const response = middleware(request);
      expect(response.headers.get('Location')).toBeNull();
    });

    it('allows authenticated user to access /', () => {
      const request = createRequest('/', { refresh_token: 'some-token' });
      const response = middleware(request);
      expect(response.headers.get('Location')).toBeNull();
    });

    it('allows authenticated user to access /not-authorized', () => {
      const request = createRequest('/not-authorized', { refresh_token: 'some-token' });
      const response = middleware(request);
      expect(response.headers.get('Location')).toBeNull();
    });

    it('allows authenticated user to access /users/123 (nested route)', () => {
      const request = createRequest('/users/123', { refresh_token: 'some-token' });
      const response = middleware(request);
      expect(response.headers.get('Location')).toBeNull();
    });

    it('allows authenticated user to access /transactions/abc (nested route)', () => {
      const request = createRequest('/transactions/abc', { refresh_token: 'some-token' });
      const response = middleware(request);
      expect(response.headers.get('Location')).toBeNull();
    });
  });
});
