import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * GET /api/auth/me
 *
 * Proxies the /auth/me request to the backend using the access_token
 * from the HTTP-only cookie as the Bearer token.
 *
 * It returns both the user details and the access_token in the body
 * so the frontend can store the token in memory (Zustand) for apiClient calls.
 */
export async function GET(request: NextRequest) {
  const accessToken = request.cookies.get('access_token')?.value;

  if (!accessToken) {
    return NextResponse.json(
      { success: false, message: 'Not authenticated', data: null },
      { status: 401 }
    );
  }

  const backendResponse = await fetch(`${API_URL}/api/v1/auth/me`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
  });

  const data = await backendResponse.json();

  if (!backendResponse.ok) {
    return NextResponse.json(data, { status: backendResponse.status });
  }

  // Wrap the user object and include the access token
  const wrappedData = {
    success: true,
    message: 'User profile retrieved successfully',
    data: {
      user: data.data,
      access_token: accessToken,
    },
  };

  return NextResponse.json(wrappedData, { status: 200 });
}
