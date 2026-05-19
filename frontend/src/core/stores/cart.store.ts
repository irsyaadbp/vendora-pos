import { create } from 'zustand';
import { Product, CartItem, Discount } from '@/core/types/models';

const MAX_DISTINCT_ITEMS = 100;

interface CartState {
  items: CartItem[];
  discount: Discount | null;
  addItem: (product: Product, quantity: number) => void;
  removeItem: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  setDiscount: (discount: Discount) => void;
  clearDiscount: () => void;
  clearCart: () => void;
  getSubtotal: () => number;
  getTotal: () => number;
}

export const useCartStore = create<CartState>((set, get) => ({
  items: [],
  discount: null,

  addItem: (product, quantity) => {
    set((state) => {
      const existingIndex = state.items.findIndex(
        (item) => item.product.id === product.id
      );

      if (existingIndex >= 0) {
        const updatedItems = [...state.items];
        const newQuantity = updatedItems[existingIndex].quantity + quantity;
        updatedItems[existingIndex] = {
          ...updatedItems[existingIndex],
          quantity: newQuantity,
          subtotal: newQuantity * product.price,
        };
        return { items: updatedItems };
      }

      if (state.items.length >= MAX_DISTINCT_ITEMS) {
        return state;
      }

      return {
        items: [
          ...state.items,
          { product, quantity, subtotal: quantity * product.price },
        ],
      };
    });
  },

  removeItem: (productId) => {
    set((state) => ({
      items: state.items.filter((item) => item.product.id !== productId),
    }));
  },

  updateQuantity: (productId, quantity) => {
    set((state) => {
      if (quantity <= 0) {
        return {
          items: state.items.filter((item) => item.product.id !== productId),
        };
      }

      return {
        items: state.items.map((item) =>
          item.product.id === productId
            ? { ...item, quantity, subtotal: quantity * item.product.price }
            : item
        ),
      };
    });
  },

  setDiscount: (discount) => {
    set({ discount });
  },

  clearDiscount: () => {
    set({ discount: null });
  },

  clearCart: () => {
    set({ items: [], discount: null });
  },

  getSubtotal: () => {
    const { items } = get();
    return items.reduce((sum, item) => sum + item.subtotal, 0);
  },

  getTotal: () => {
    const { items, discount } = get();
    const subtotal = items.reduce((sum, item) => sum + item.subtotal, 0);

    if (!discount) {
      return subtotal;
    }

    return Math.max(0, subtotal - discount.amount);
  },
}));
