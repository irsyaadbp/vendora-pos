/**
 * Shared formatting utilities for the Vendora POS frontend.
 */

/**
 * Formats a number as Indonesian Rupiah (IDR) currency.
 *
 * @param amount - The numeric amount to format
 * @returns Formatted currency string (e.g., "Rp 1.500.000")
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Formats an ISO date string to a human-readable format.
 *
 * @param date - ISO 8601 date string
 * @returns Formatted date string (e.g., "15 Jan 2025, 14:30")
 */
export function formatDate(date: string): string {
  return new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
}

/**
 * Formats a number with thousand separators using Indonesian locale.
 *
 * @param num - The number to format
 * @returns Formatted number string (e.g., "1.500.000")
 */
export function formatNumber(num: number): string {
  return new Intl.NumberFormat("id-ID").format(num);
}
