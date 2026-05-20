import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * POST /api/auth/logout
 *
 * Proxies logout to the backend. Clears access_token and refresh_token
 * cookies on the frontend domain.
 */
export async function POST(request: NextRequest) {
  const refreshToken = request.cookies.get('refresh_token')?.value;

  const backendResponse = await fetch(`${API_URL}/api/v1/auth/logout`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(refreshToken ? { Cookie: `refresh_token=${refreshToken}` } : {}),
    },
  });

  const data = await backendResponse.json();

  const response = NextResponse.json(data, { status: backendResponse.status });

  response.cookies.delete('access_token', { path: '/' });
  response.cookies.delete('refresh_token', { path: '/' });

  return response;
}
