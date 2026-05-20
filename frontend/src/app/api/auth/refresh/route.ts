import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const COOKIE_DOMAIN = process.env.NEXT_PUBLIC_COOKIE_DOMAIN || undefined;

/**
 * POST /api/auth/refresh
 *
 * Proxies token refresh to the backend. Rotates access_token and
 * refresh_token cookies.
 *
 * Note: Node.js fetch() strips Set-Cookie headers in server-to-server calls,
 * so the backend includes refresh_token in the response body. The proxy reads
 * it, sets it as an httpOnly cookie, then strips it from the body before
 * returning to the browser.
 */
export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get('refresh_token')?.value;

  const backendResponse = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(refreshToken ? { Cookie: `refresh_token=${refreshToken}` } : {}),
    },
  });

  const data = await backendResponse.json();

  const commonOptions = {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax' as const,
    path: '/',
    ...(COOKIE_DOMAIN ? { domain: COOKIE_DOMAIN } : {}),
  };

  if (!backendResponse.ok) {
    const response = NextResponse.json(data, { status: backendResponse.status });
    response.cookies.delete('access_token', {
      path: '/',
      ...(COOKIE_DOMAIN ? { domain: COOKIE_DOMAIN } : {}),
    });
    response.cookies.delete('refresh_token', {
      path: '/',
      ...(COOKIE_DOMAIN ? { domain: COOKIE_DOMAIN } : {}),
    });
    return response;
  }

  const newAccessToken: string = data.data?.access_token;
  const newRefreshToken: string = data.data?.refresh_token;

  // Strip refresh_token from the response body — it must not reach the browser
  if (data.data) {
    delete data.data.refresh_token;
  }

  const response = NextResponse.json(data, { status: 200 });

  if (newAccessToken) {
    response.cookies.set('access_token', newAccessToken, {
      ...commonOptions,
      maxAge: 15 * 60,
    });
  }

  if (newRefreshToken) {
    response.cookies.set('refresh_token', newRefreshToken, {
      ...commonOptions,
      maxAge: 7 * 24 * 60 * 60,
    });
  }

  return response;
}
