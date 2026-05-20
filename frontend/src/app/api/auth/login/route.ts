import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const COOKIE_DOMAIN = process.env.NEXT_PUBLIC_COOKIE_DOMAIN || undefined;

/**
 * POST /api/auth/login
 *
 * Proxies login to the backend. On success, sets two httpOnly cookies
 * on the frontend domain:
 *   - access_token  (15 min)
 *   - refresh_token (7 days)
 *
 * Note: Node.js fetch() strips Set-Cookie headers in server-to-server calls,
 * so the backend includes both tokens in the response body. The proxy reads
 * them, sets them as httpOnly cookies, then strips them from the body before
 * returning to the browser.
 *
 * Role is NOT stored in a cookie — the full user object (including role)
 * is in the response body so Zustand can store it in memory.
 */
export async function POST(request: NextRequest) {
  const body = await request.json();

  const backendResponse = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const data = await backendResponse.json();

  if (!backendResponse.ok) {
    return NextResponse.json(data, { status: backendResponse.status });
  }

  const accessToken: string = data.data?.access_token;
  const refreshToken: string = data.data?.refresh_token;

  // Strip refresh_token from the response body — it must not reach the browser
  if (data.data) {
    delete data.data.refresh_token;
  }

  const response = NextResponse.json(data, { status: 200 });

  const commonOptions = {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax' as const,
    path: '/',
    ...(COOKIE_DOMAIN ? { domain: COOKIE_DOMAIN } : {}),
  };

  if (accessToken) {
    response.cookies.set('access_token', accessToken, {
      ...commonOptions,
      maxAge: 15 * 60, // 15 minutes
    });
  }

  if (refreshToken) {
    response.cookies.set('refresh_token', refreshToken, {
      ...commonOptions,
      maxAge: 7 * 24 * 60 * 60, // 7 days
    });
  }

  return response;
}
