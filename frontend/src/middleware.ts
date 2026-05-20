import { NextRequest, NextResponse } from "next/server";

/**
 * Cookie names used for authentication state in middleware.
 *
 * - USER_ROLE_COOKIE: Non-HTTP-only cookie set by the frontend after login.
 *   Contains the user's role ("admin" | "staff") for route-level access control.
 *   This is the primary indicator of an active session for middleware purposes.
 *
 * Note: The refresh_token is an HTTP-only cookie set by the backend domain.
 * In cross-origin deployments (frontend and backend on different subdomains),
 * the browser won't send the backend's cookie to the frontend server,
 * so we rely solely on user_role for middleware route protection.
 */
const USER_ROLE_COOKIE = "user_role";

type UserRole = "admin" | "staff";

/**
 * Route protection configuration.
 *
 * - publicRoutes: Accessible without authentication.
 * - adminRoutes: Require authentication + admin role.
 * - staffRoutes: Require authentication + any role (admin or staff).
 */
const publicRoutes: string[] = ["/login"];

/**
 * Admin-only route patterns.
 * These routes require the user to have the "admin" role.
 */
const adminRoutePatterns: RegExp[] = [
  /^\/users(\/.*)?$/,
  /^\/inventory(\/.*)?$/,
  /^\/products(\/.*)?$/,
  /^\/dashboard(\/.*)?$/,
];

/**
 * Staff-accessible route patterns.
 * These routes are accessible by both "admin" and "staff" roles.
 */
const staffRoutePatterns: RegExp[] = [
  /^\/pos(\/.*)?$/,
  /^\/transactions(\/.*)?$/,
];

/**
 * Check if a pathname matches any pattern in the given list.
 */
function matchesPattern(pathname: string, patterns: RegExp[]): boolean {
  return patterns.some((pattern) => pattern.test(pathname));
}

/**
 * Check if a pathname is a public route.
 */
function isPublicRoute(pathname: string): boolean {
  return publicRoutes.includes(pathname);
}

/**
 * Determine the minimum role required for a given pathname.
 * Returns null if the route doesn't match any protected pattern.
 */
function getRequiredRole(pathname: string): UserRole | null {
  if (matchesPattern(pathname, adminRoutePatterns)) {
    return "admin";
  }
  if (matchesPattern(pathname, staffRoutePatterns)) {
    return "staff";
  }
  return null;
}

/**
 * Check if the user's role satisfies the required role.
 * Admin can access everything. Staff can only access staff routes.
 */
function hasAccess(userRole: UserRole, requiredRole: UserRole): boolean {
  if (userRole === "admin") {
    return true;
  }
  return requiredRole === "staff";
}

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  // Allow public routes without any auth check
  if (isPublicRoute(pathname)) {
    // If user is already authenticated and visits /login, redirect to home
    const userRoleCookie = request.cookies.get(USER_ROLE_COOKIE);
    if (userRoleCookie) {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return NextResponse.next();
  }

  // Check authentication: user_role cookie indicates an active session
  const userRoleCookie = request.cookies.get(USER_ROLE_COOKIE);
  if (!userRoleCookie) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Determine required role for the route
  const requiredRole = getRequiredRole(pathname);

  // If route has role requirements, check the user's role
  if (requiredRole) {
    const userRole = userRoleCookie?.value as UserRole | undefined;

    if (!userRole || (userRole !== "admin" && userRole !== "staff")) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl);
    }

    // Check if user has sufficient permissions
    if (!hasAccess(userRole, requiredRole)) {
      return NextResponse.redirect(new URL("/not-authorized", request.url));
    }
  }

  return NextResponse.next();
}

/**
 * Middleware matcher configuration.
 * Excludes Next.js internals, static files, and API routes from middleware processing.
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico, sitemap.xml, robots.txt (metadata files)
     * - api routes (handled by backend)
     */
    "/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt|api).*)",
  ],
};
