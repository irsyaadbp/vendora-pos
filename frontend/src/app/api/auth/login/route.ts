import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * POST /api/auth/login
 *
 * Proxies login to the backend. On success, sets two httpOnly cookies
 * on the frontend domain:
 *   - access_token  (15 min) — used by BE dependency as Bearer fallback
 *   - refresh_token (7 days) — forwarded from backend Set-Cookie header
 *
 * Role is NOT stored in a cookie. The full login response body (including
 * user.role) is returned to the client so Zustand can store it in memory.
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

  const response = NextResponse.json(data, { status: 200 });

  // Forward the refresh_token httpOnly cookie set by the backend
  const setCookieHeaders = backendResponse.headers.getSetCookie();
  for (const cookie of setCookieHeaders) {
    response.headers.append('Set-Cookie', cookie);
  }

  const accessToken: string = data.data?.access_token;
  if (accessToken) {
    response.cookies.set('access_token', accessToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 15 * 60, // 15 minutes
    });
  }

  return response;
}
