import { AxiosError } from 'axios';

export interface FieldError {
  field: string;
  detail: string;
}

export interface APIErrorResponse {
  success: false;
  data: null;
  message: string;
  errors: FieldError[];
}

/**
 * Type guard to check if an error is an Axios error
 */
export function isAxiosError(error: unknown): error is AxiosError<APIErrorResponse> {
  return error instanceof AxiosError;
}

/**
 * Parse an API error response into a structured format.
 * Returns a consistent error object regardless of the error source.
 */
export function parseAPIError(error: unknown): APIErrorResponse {
  if (isAxiosError(error) && error.response?.data) {
    const data = error.response.data;

    // If the response matches our API error format, return it directly
    if (
      typeof data === 'object' &&
      'success' in data &&
      data.success === false
    ) {
      return {
        success: false,
        data: null,
        message: data.message || 'An error occurred',
        errors: Array.isArray(data.errors) ? data.errors : [],
      };
    }
  }

  // Network error (no response received)
  if (isAxiosError(error) && !error.response) {
    return {
      success: false,
      data: null,
      message: 'Network error. Please check your connection and try again.',
      errors: [],
    };
  }

  // Fallback for unexpected errors
  const message =
    error instanceof Error ? error.message : 'An unexpected error occurred';

  return {
    success: false,
    data: null,
    message,
    errors: [],
  };
}

/**
 * Extract a user-friendly error message from an error.
 * Useful for displaying in toast notifications.
 */
export function getErrorMessage(error: unknown): string {
  const parsed = parseAPIError(error);
  return parsed.message;
}

/**
 * Extract field-specific errors from an API error response.
 * Useful for displaying inline form validation errors.
 */
export function getFieldErrors(error: unknown): Record<string, string> {
  const parsed = parseAPIError(error);
  const fieldErrors: Record<string, string> = {};

  for (const fieldError of parsed.errors) {
    fieldErrors[fieldError.field] = fieldError.detail;
  }

  return fieldErrors;
}

/**
 * Check if an error is a specific HTTP status code.
 */
export function isHttpError(error: unknown, statusCode: number): boolean {
  return isAxiosError(error) && error.response?.status === statusCode;
}

/**
 * Check if an error is an authentication error (401).
 */
export function isAuthError(error: unknown): boolean {
  return isHttpError(error, 401);
}

/**
 * Check if an error is a forbidden error (403).
 */
export function isForbiddenError(error: unknown): boolean {
  return isHttpError(error, 403);
}

/**
 * Check if an error is a not found error (404).
 */
export function isNotFoundError(error: unknown): boolean {
  return isHttpError(error, 404);
}

/**
 * Check if an error is a conflict error (409).
 */
export function isConflictError(error: unknown): boolean {
  return isHttpError(error, 409);
}

/**
 * Check if an error is a validation error (422).
 */
export function isValidationError(error: unknown): boolean {
  return isHttpError(error, 422);
}

/**
 * Check if an error is a rate limit error (429).
 */
export function isRateLimitError(error: unknown): boolean {
  return isHttpError(error, 429);
}
