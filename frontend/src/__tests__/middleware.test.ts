import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "@/middleware";

/**
 * Helper to create a NextRequest with optional cookies.
 */
function createRequest(
  pathname: string,
  cookies: Record<string, string> = {}
): NextRequest {
  const url = new URL(pathname, "http://localhost:3000");
  const request = new NextRequest(url);

  for (const [name, value] of Object.entries(cookies)) {
    request.cookies.set(name, value);
  }

  return request;
}

describe("middleware", () => {
  describe("public routes", () => {
    it("allows unauthenticated access to /login", () => {
      const request = createRequest("/login");
      const response = middleware(request);

      // Should not redirect — NextResponse.next() has no Location header
      expect(response.headers.get("Location")).toBeNull();
    });

    it("redirects authenticated users away from /login to /", () => {
      const request = createRequest("/login", {
        refresh_token: "some-token",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBe("http://localhost:3000/");
    });
  });

  describe("unauthenticated access to protected routes", () => {
    it("redirects to /login when no refresh_token cookie", () => {
      const request = createRequest("/dashboard");
      const response = middleware(request);

      const location = response.headers.get("Location");
      expect(location).toContain("/login");
      expect(location).toContain("callbackUrl=%2Fdashboard");
    });

    it("redirects to /login for /pos without auth", () => {
      const request = createRequest("/pos");
      const response = middleware(request);

      const location = response.headers.get("Location");
      expect(location).toContain("/login");
      expect(location).toContain("callbackUrl=%2Fpos");
    });

    it("redirects to /login for /users without auth", () => {
      const request = createRequest("/users");
      const response = middleware(request);

      const location = response.headers.get("Location");
      expect(location).toContain("/login");
    });
  });

  describe("admin route protection", () => {
    it("allows admin to access /users", () => {
      const request = createRequest("/users", {
        refresh_token: "some-token",
        user_role: "admin",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });

    it("allows admin to access /inventory", () => {
      const request = createRequest("/inventory", {
        refresh_token: "some-token",
        user_role: "admin",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });

    it("allows admin to access /products", () => {
      const request = createRequest("/products", {
        refresh_token: "some-token",
        user_role: "admin",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });

    it("allows admin to access /dashboard", () => {
      const request = createRequest("/dashboard", {
        refresh_token: "some-token",
        user_role: "admin",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });

    it("redirects staff to /not-authorized for /users", () => {
      const request = createRequest("/users", {
        refresh_token: "some-token",
        user_role: "staff",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBe(
        "http://localhost:3000/not-authorized"
      );
    });

    it("redirects staff to /not-authorized for /inventory", () => {
      const request = createRequest("/inventory", {
        refresh_token: "some-token",
        user_role: "staff",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBe(
        "http://localhost:3000/not-authorized"
      );
    });

    it("redirects staff to /not-authorized for /products", () => {
      const request = createRequest("/products", {
        refresh_token: "some-token",
        user_role: "staff",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBe(
        "http://localhost:3000/not-authorized"
      );
    });

    it("redirects staff to /not-authorized for /dashboard", () => {
      const request = createRequest("/dashboard", {
        refresh_token: "some-token",
        user_role: "staff",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBe(
        "http://localhost:3000/not-authorized"
      );
    });
  });

  describe("staff route protection", () => {
    it("allows staff to access /pos", () => {
      const request = createRequest("/pos", {
        refresh_token: "some-token",
        user_role: "staff",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });

    it("allows staff to access /transactions", () => {
      const request = createRequest("/transactions", {
        refresh_token: "some-token",
        user_role: "staff",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });

    it("allows admin to access /pos", () => {
      const request = createRequest("/pos", {
        refresh_token: "some-token",
        user_role: "admin",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });

    it("allows admin to access /transactions", () => {
      const request = createRequest("/transactions", {
        refresh_token: "some-token",
        user_role: "admin",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });
  });

  describe("nested routes", () => {
    it("protects /users/123 as admin-only", () => {
      const request = createRequest("/users/123", {
        refresh_token: "some-token",
        user_role: "staff",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBe(
        "http://localhost:3000/not-authorized"
      );
    });

    it("allows admin to access /users/123", () => {
      const request = createRequest("/users/123", {
        refresh_token: "some-token",
        user_role: "admin",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });

    it("allows staff to access /transactions/abc", () => {
      const request = createRequest("/transactions/abc", {
        refresh_token: "some-token",
        user_role: "staff",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });
  });

  describe("invalid role cookie", () => {
    it("redirects to /login when role cookie has invalid value", () => {
      const request = createRequest("/users", {
        refresh_token: "some-token",
        user_role: "invalid-role",
      });
      const response = middleware(request);

      const location = response.headers.get("Location");
      expect(location).toContain("/login");
    });

    it("redirects to /login when role cookie is missing for protected route", () => {
      const request = createRequest("/users", {
        refresh_token: "some-token",
      });
      const response = middleware(request);

      const location = response.headers.get("Location");
      expect(location).toContain("/login");
    });
  });

  describe("unprotected authenticated routes", () => {
    it("allows authenticated user to access / without role check", () => {
      const request = createRequest("/", {
        refresh_token: "some-token",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });

    it("allows authenticated user to access /not-authorized page", () => {
      const request = createRequest("/not-authorized", {
        refresh_token: "some-token",
      });
      const response = middleware(request);

      expect(response.headers.get("Location")).toBeNull();
    });
  });
});
