import { z } from "zod";

/**
 * Shared Zod validation schemas for the Vendora POS frontend.
 */

/**
 * Email validation schema.
 */
export const emailSchema = z.string().email("Invalid email address");

/**
 * Password validation schema (minimum 8 characters).
 */
export const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters");

/**
 * Pagination parameters validation schema.
 * - page: minimum 1
 * - pageSize: minimum 1, maximum 100
 */
export const paginationSchema = z.object({
  page: z.number().int().min(1, "Page must be at least 1"),
  pageSize: z
    .number()
    .int()
    .min(1, "Page size must be at least 1")
    .max(100, "Page size must not exceed 100"),
});

export type PaginationParams = z.infer<typeof paginationSchema>;
