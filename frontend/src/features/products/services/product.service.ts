import { apiClient } from '@/core/api/client';
import type { APIResponse, PaginatedResponse } from '@/core/types/api';
import type { Product } from '@/core/types/models';

// ─── Category Types ───────────────────────────────────────────────────────────

export interface Category {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface CategoryCreateData {
  name: string;
  description?: string | null;
}

export interface CategoryUpdateData {
  name?: string;
  description?: string | null;
}

// ─── Product Types ────────────────────────────────────────────────────────────

export interface ProductCreateData {
  name: string;
  sku: string;
  barcode?: string | null;
  price: number;
  stock: number;
  category_id?: string | null;
}

export interface ProductUpdateData {
  name?: string;
  sku?: string;
  barcode?: string | null;
  price?: number;
  stock?: number;
  category_id?: string | null;
  is_active?: boolean;
}

export interface ProductSearchParams {
  q?: string;
  category_id?: string;
  page?: number;
  page_size?: number;
}

// ─── Product API Calls ────────────────────────────────────────────────────────

/**
 * GET /products — List products with pagination.
 */
async function listProducts(params: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<Product>> {
  const response = await apiClient.get<PaginatedResponse<Product>>('/products', {
    params,
  });
  return response.data;
}

/**
 * GET /products/search — Search products by name/SKU/barcode with filters.
 */
async function searchProducts(
  params: ProductSearchParams
): Promise<PaginatedResponse<Product>> {
  const response = await apiClient.get<PaginatedResponse<Product>>(
    '/products/search',
    { params }
  );
  return response.data;
}

/**
 * GET /products/:id — Get a single product by ID.
 */
async function getProduct(productId: string): Promise<Product> {
  const response = await apiClient.get<APIResponse<Product>>(
    `/products/${productId}`
  );
  return response.data.data;
}

/**
 * POST /products — Create a new product (admin only).
 */
async function createProduct(data: ProductCreateData): Promise<Product> {
  const response = await apiClient.post<APIResponse<Product>>('/products', data);
  return response.data.data;
}

/**
 * PUT /products/:id — Update an existing product (admin only).
 */
async function updateProduct(
  productId: string,
  data: ProductUpdateData
): Promise<Product> {
  const response = await apiClient.put<APIResponse<Product>>(
    `/products/${productId}`,
    data
  );
  return response.data.data;
}

/**
 * DELETE /products/:id — Soft delete a product (admin only).
 */
async function deleteProduct(productId: string): Promise<void> {
  await apiClient.delete(`/products/${productId}`);
}

// ─── Category API Calls ───────────────────────────────────────────────────────

/**
 * GET /categories — List categories with pagination.
 */
async function listCategories(params?: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<Category>> {
  const response = await apiClient.get<PaginatedResponse<Category>>(
    '/categories',
    { params }
  );
  return response.data;
}

/**
 * POST /categories — Create a new category (admin only).
 */
async function createCategory(data: CategoryCreateData): Promise<Category> {
  const response = await apiClient.post<APIResponse<Category>>(
    '/categories',
    data
  );
  return response.data.data;
}

/**
 * PUT /categories/:id — Update a category (admin only).
 */
async function updateCategory(
  categoryId: string,
  data: CategoryUpdateData
): Promise<Category> {
  const response = await apiClient.put<APIResponse<Category>>(
    `/categories/${categoryId}`,
    data
  );
  return response.data.data;
}

/**
 * DELETE /categories/:id — Delete a category (admin only).
 */
async function deleteCategory(categoryId: string): Promise<void> {
  await apiClient.delete(`/categories/${categoryId}`);
}

export const productService = {
  listProducts,
  searchProducts,
  getProduct,
  createProduct,
  updateProduct,
  deleteProduct,
  listCategories,
  createCategory,
  updateCategory,
  deleteCategory,
};
