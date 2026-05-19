/**
 * Domain model type definitions matching backend entity schemas.
 *
 * Backend enums: app/schemas/enums.py
 * Backend models: app/models/
 */

export type UserRole = "admin" | "staff";

export type PaymentMethod = "cash" | "qris" | "debit_card" | "credit_card";

export type TransactionStatus = "completed" | "voided";

export interface User {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: string;
  name: string;
  sku: string;
  barcode: string | null;
  price: number;
  stock: number;
  category_id: string | null;
  is_active: boolean;
  low_stock: boolean;
  created_at: string;
  updated_at: string;
}

export interface CartItem {
  product: Product;
  quantity: number;
  subtotal: number;
}

export interface Discount {
  type: "percentage" | "fixed";
  value: number;
  amount: number;
}

export interface Transaction {
  id: string;
  cashier_id: string;
  total_amount: number;
  discount_amount: number;
  payment_method: PaymentMethod;
  status: TransactionStatus;
  created_at: string;
}
