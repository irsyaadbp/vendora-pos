import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * POST /api/auth/refresh
 *
 * Proxies token refresh to the backend. Rotates access_token and
 * refresh_token cookies. On failure, clears access_token only
 * (refresh_token is already invalid at that point).
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

  if (!backendResponse.ok) {
    const response = NextResponse.json(data, { status: backendResponse.status });
    response.cookies.delete('access_token');
    return response;
  }

  const response = NextResponse.json(data, { status: 200 });

  // Forward the rotated refresh_token from backend
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
      maxAge: 15 * 60,
    });
  }

  return response;
}
