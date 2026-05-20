import { NextRequest, NextResponse } from 'next/server';

/**
 * Session cookie — 7-day refresh token. Its presence indicates the user
 * has an active (or recently expired) session.
 * We check refresh_token rather than access_token because the access_token
 * expires every 15 minutes; using it here would cause middleware redirects
 * while the axios interceptor is silently refreshing in the background.
 */
const SESSION_COOKIE = 'refresh_token';

const publicRoutes: string[] = ['/login'];

function isPublicRoute(pathname: string): boolean {
  return publicRoutes.includes(pathname);
}

/**
 * Session gate only — no RBAC.
 * Role-based access control is handled at the page/component level
 * using the Zustand auth store (populated from the login response or /me).
 */
export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const hasSession = request.cookies.has(SESSION_COOKIE);

  if (isPublicRoute(pathname)) {
    if (hasSession) {
      return NextResponse.redirect(new URL('/', request.url));
    }
    return NextResponse.next();
  }

  if (!hasSession) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

/**
 * Middleware matcher configuration.
 * Excludes Next.js internals, static files, and API routes from middleware processing.
 */
export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt|api).*)',
  ],
};
