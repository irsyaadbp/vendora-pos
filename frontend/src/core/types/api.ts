/**
 * Typed API response interfaces matching the backend response format.
 *
 * Backend schemas: app/schemas/common.py
 */

export interface APIResponse<T> {
  success: boolean;
  data: T;
  message: string;
}

export interface APIErrorResponse {
  success: false;
  data: null;
  message: string;
  errors: FieldError[];
}

export interface FieldError {
  field: string;
  detail: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  message: string;
  meta: PaginationMeta;
}

export interface PaginationMeta {
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}
