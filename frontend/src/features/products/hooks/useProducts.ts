import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  productService,
  type CategoryCreateData,
  type CategoryUpdateData,
  type ProductCreateData,
  type ProductSearchParams,
  type ProductUpdateData,
} from '../services/product.service';

// ─── Query Keys ───────────────────────────────────────────────────────────────

export const productKeys = {
  all: ['products'] as const,
  lists: () => [...productKeys.all, 'list'] as const,
  list: (params: ProductSearchParams) =>
    [...productKeys.lists(), params] as const,
  details: () => [...productKeys.all, 'detail'] as const,
  detail: (id: string) => [...productKeys.details(), id] as const,
};

export const categoryKeys = {
  all: ['categories'] as const,
  lists: () => [...categoryKeys.all, 'list'] as const,
  list: (params?: { page?: number; page_size?: number }) =>
    [...categoryKeys.lists(), params] as const,
};

// ─── Product Queries ──────────────────────────────────────────────────────────

/**
 * Fetch paginated products with search and category filter.
 */
export function useProducts(params: ProductSearchParams) {
  return useQuery({
    queryKey: productKeys.list(params),
    queryFn: () => productService.searchProducts(params),
  });
}

/**
 * Fetch a single product by ID.
 */
export function useProduct(productId: string) {
  return useQuery({
    queryKey: productKeys.detail(productId),
    queryFn: () => productService.getProduct(productId),
    enabled: !!productId,
  });
}

// ─── Product Mutations ────────────────────────────────────────────────────────

/**
 * Create a new product. Invalidates product list queries on success.
 */
export function useCreateProduct() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProductCreateData) => productService.createProduct(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
    },
  });
}

/**
 * Update an existing product. Invalidates product list and detail queries on success.
 */
export function useUpdateProduct() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      productId,
      data,
    }: {
      productId: string;
      data: ProductUpdateData;
    }) => productService.updateProduct(productId, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: productKeys.detail(variables.productId),
      });
    },
  });
}

/**
 * Soft delete a product. Invalidates product list queries on success.
 */
export function useDeleteProduct() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (productId: string) => productService.deleteProduct(productId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
    },
  });
}

// ─── Category Queries ─────────────────────────────────────────────────────────

/**
 * Fetch paginated categories.
 */
export function useCategories(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: categoryKeys.list(params),
    queryFn: () => productService.listCategories(params),
  });
}

// ─── Category Mutations ───────────────────────────────────────────────────────

/**
 * Create a new category. Invalidates category list queries on success.
 */
export function useCreateCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CategoryCreateData) =>
      productService.createCategory(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: categoryKeys.lists() });
    },
  });
}

/**
 * Update an existing category. Invalidates category list queries on success.
 */
export function useUpdateCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      categoryId,
      data,
    }: {
      categoryId: string;
      data: CategoryUpdateData;
    }) => productService.updateCategory(categoryId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: categoryKeys.lists() });
    },
  });
}

/**
 * Delete a category. Invalidates category list queries on success.
 */
export function useDeleteCategory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (categoryId: string) =>
      productService.deleteCategory(categoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: categoryKeys.lists() });
    },
  });
}
