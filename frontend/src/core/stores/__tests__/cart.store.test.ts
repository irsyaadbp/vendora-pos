/**
 * Property-based tests for Cart Store calculations.
 *
 * **Validates: Requirements 7.3, 7.4, 7.5**
 *
 * Property 20: Cart state consistency — Cart items always have valid quantities and subtotals
 * Property 21: Cart calculation accuracy — getSubtotal and getTotal always produce correct results
 */

import { describe, it, beforeEach } from 'vitest';
import * as fc from 'fast-check';
import { useCartStore } from '@/core/stores/cart.store';
import { Product, Discount } from '@/core/types/models';

// --- Arbitraries (Generators) ---

const productArbitrary: fc.Arbitrary<Product> = fc.record({
  id: fc.uuid(),
  name: fc.string({ minLength: 1, maxLength: 50 }),
  sku: fc.string({ minLength: 1, maxLength: 20 }),
  barcode: fc.option(fc.string({ minLength: 1, maxLength: 20 }), { nil: null }),
  price: fc.double({ min: 0.01, max: 999999.99, noNaN: true }),
  stock: fc.integer({ min: 0, max: 10000 }),
  category_id: fc.option(fc.uuid(), { nil: null }),
  is_active: fc.constant(true),
  low_stock: fc.boolean(),
  created_at: fc.constant('2024-01-01T00:00:00Z'),
  updated_at: fc.constant('2024-01-01T00:00:00Z'),
});

const quantityArbitrary = fc.integer({ min: 1, max: 100 });

const percentageDiscountArbitrary: fc.Arbitrary<Discount> = fc
  .double({ min: 0.01, max: 100, noNaN: true })
  .map((value) => ({
    type: 'percentage' as const,
    value,
    amount: 0, // will be calculated based on subtotal
  }));

const fixedDiscountArbitrary: fc.Arbitrary<Discount> = fc
  .double({ min: 0.01, max: 999999.99, noNaN: true })
  .map((value) => ({
    type: 'fixed' as const,
    value,
    amount: value,
  }));

const discountArbitrary: fc.Arbitrary<Discount> = fc.oneof(
  percentageDiscountArbitrary,
  fixedDiscountArbitrary
);

// Generate unique products (unique by id)
function uniqueProducts(count: number): fc.Arbitrary<Product[]> {
  return fc
    .array(productArbitrary, { minLength: count, maxLength: count })
    .map((products) => {
      const seen = new Set<string>();
      return products.filter((p) => {
        if (seen.has(p.id)) return false;
        seen.add(p.id);
        return true;
      });
    });
}

// Cart operation commands for model-based testing
type CartCommand =
  | { type: 'addItem'; product: Product; quantity: number }
  | { type: 'removeItem'; productId: string }
  | { type: 'updateQuantity'; productId: string; quantity: number };

// --- Tests ---

describe('Cart Store Property Tests', () => {
  beforeEach(() => {
    // Reset the store before each test
    useCartStore.setState({ items: [], discount: null });
  });

  /**
   * Property 20: Cart state consistency
   * For any sequence of addItem/removeItem/updateQuantity operations,
   * the cart state remains consistent:
   * - No negative quantities
   * - Subtotals match quantity * price
   *
   * **Validates: Requirements 7.3**
   */
  describe('Property 20: Cart state consistency', () => {
    it('cart items always have positive quantities after any sequence of operations', () => {
      fc.assert(
        fc.property(
          fc.array(productArbitrary, { minLength: 1, maxLength: 10 }),
          fc.array(quantityArbitrary, { minLength: 1, maxLength: 10 }),
          (products, quantities) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            // Add items
            products.forEach((product, i) => {
              const qty = quantities[i % quantities.length];
              store.addItem(product, qty);
            });

            // Verify all items have positive quantities
            const state = useCartStore.getState();
            for (const item of state.items) {
              if (item.quantity <= 0) return false;
            }
            return true;
          }
        ),
        { numRuns: 200 }
      );
    });

    it('subtotals always equal quantity * price for each item', () => {
      fc.assert(
        fc.property(
          fc.array(productArbitrary, { minLength: 1, maxLength: 10 }),
          fc.array(quantityArbitrary, { minLength: 1, maxLength: 10 }),
          (products, quantities) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            // Add items
            products.forEach((product, i) => {
              const qty = quantities[i % quantities.length];
              store.addItem(product, qty);
            });

            // Verify subtotals
            const state = useCartStore.getState();
            for (const item of state.items) {
              const expected = item.quantity * item.product.price;
              if (Math.abs(item.subtotal - expected) > 0.001) return false;
            }
            return true;
          }
        ),
        { numRuns: 200 }
      );
    });

    it('updateQuantity with positive value maintains subtotal = quantity * price', () => {
      fc.assert(
        fc.property(
          productArbitrary,
          quantityArbitrary,
          quantityArbitrary,
          (product, initialQty, newQty) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            store.addItem(product, initialQty);
            store.updateQuantity(product.id, newQty);

            const state = useCartStore.getState();
            const item = state.items.find((i) => i.product.id === product.id);

            if (!item) return false;
            const expected = newQty * product.price;
            return Math.abs(item.subtotal - expected) < 0.001;
          }
        ),
        { numRuns: 200 }
      );
    });

    it('updateQuantity with zero or negative removes the item', () => {
      fc.assert(
        fc.property(
          productArbitrary,
          quantityArbitrary,
          fc.integer({ min: -100, max: 0 }),
          (product, initialQty, zeroOrNegQty) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            store.addItem(product, initialQty);
            store.updateQuantity(product.id, zeroOrNegQty);

            const state = useCartStore.getState();
            const item = state.items.find((i) => i.product.id === product.id);
            return item === undefined;
          }
        ),
        { numRuns: 200 }
      );
    });

    it('max 100 distinct items is enforced', () => {
      fc.assert(
        fc.property(
          uniqueProducts(110),
          (products) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            // Try to add more than 100 distinct items
            for (const product of products) {
              store.addItem(product, 1);
            }

            const state = useCartStore.getState();
            return state.items.length <= 100;
          }
        ),
        { numRuns: 50 }
      );
    });

    it('adding same product multiple times accumulates quantity correctly', () => {
      fc.assert(
        fc.property(
          productArbitrary,
          fc.array(quantityArbitrary, { minLength: 2, maxLength: 5 }),
          (product, quantities) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            // Add same product multiple times
            for (const qty of quantities) {
              store.addItem(product, qty);
            }

            const state = useCartStore.getState();
            const item = state.items.find((i) => i.product.id === product.id);

            if (!item) return false;

            const totalQty = quantities.reduce((sum, q) => sum + q, 0);
            if (item.quantity !== totalQty) return false;

            const expectedSubtotal = totalQty * product.price;
            return Math.abs(item.subtotal - expectedSubtotal) < 0.001;
          }
        ),
        { numRuns: 200 }
      );
    });
  });

  /**
   * Property 21: Cart calculation accuracy
   * getSubtotal and getTotal always produce correct results:
   * - getSubtotal equals sum of all item subtotals
   * - getTotal equals subtotal minus discount amount (clamped to 0)
   *
   * **Validates: Requirements 7.4, 7.5**
   */
  describe('Property 21: Cart calculation accuracy', () => {
    it('getSubtotal always equals the sum of all item subtotals', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.tuple(productArbitrary, quantityArbitrary),
            { minLength: 0, maxLength: 20 }
          ),
          (itemPairs) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            // Add items
            for (const [product, qty] of itemPairs) {
              store.addItem(product, qty);
            }

            const state = useCartStore.getState();
            const expectedSubtotal = state.items.reduce(
              (sum, item) => sum + item.subtotal,
              0
            );
            const actualSubtotal = state.getSubtotal();

            return Math.abs(actualSubtotal - expectedSubtotal) < 0.001;
          }
        ),
        { numRuns: 200 }
      );
    });

    it('getTotal equals subtotal when no discount is applied', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.tuple(productArbitrary, quantityArbitrary),
            { minLength: 1, maxLength: 20 }
          ),
          (itemPairs) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            for (const [product, qty] of itemPairs) {
              store.addItem(product, qty);
            }

            const state = useCartStore.getState();
            const subtotal = state.getSubtotal();
            const total = state.getTotal();

            return Math.abs(total - subtotal) < 0.001;
          }
        ),
        { numRuns: 200 }
      );
    });

    it('getTotal equals subtotal minus discount amount (clamped to 0) with fixed discount', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.tuple(productArbitrary, quantityArbitrary),
            { minLength: 1, maxLength: 10 }
          ),
          fc.double({ min: 0.01, max: 999999.99, noNaN: true }),
          (itemPairs, discountAmount) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            for (const [product, qty] of itemPairs) {
              store.addItem(product, qty);
            }

            const discount: Discount = {
              type: 'fixed',
              value: discountAmount,
              amount: discountAmount,
            };
            store.setDiscount(discount);

            const state = useCartStore.getState();
            const subtotal = state.getSubtotal();
            const total = state.getTotal();
            const expected = Math.max(0, subtotal - discountAmount);

            return Math.abs(total - expected) < 0.001;
          }
        ),
        { numRuns: 200 }
      );
    });

    it('getTotal is always non-negative regardless of discount', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.tuple(productArbitrary, quantityArbitrary),
            { minLength: 0, maxLength: 10 }
          ),
          discountArbitrary,
          (itemPairs, discount) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            for (const [product, qty] of itemPairs) {
              store.addItem(product, qty);
            }

            // For percentage discounts, calculate the amount
            if (discount.type === 'percentage') {
              const subtotal = useCartStore.getState().getSubtotal();
              discount.amount = (subtotal * discount.value) / 100;
            }

            store.setDiscount(discount);

            const state = useCartStore.getState();
            const total = state.getTotal();

            return total >= 0;
          }
        ),
        { numRuns: 200 }
      );
    });

    it('discount calculations are correct for percentage type', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.tuple(productArbitrary, quantityArbitrary),
            { minLength: 1, maxLength: 10 }
          ),
          fc.double({ min: 1, max: 100, noNaN: true }),
          (itemPairs, percentage) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            for (const [product, qty] of itemPairs) {
              store.addItem(product, qty);
            }

            const subtotal = useCartStore.getState().getSubtotal();
            const discountAmount = (subtotal * percentage) / 100;

            const discount: Discount = {
              type: 'percentage',
              value: percentage,
              amount: discountAmount,
            };
            store.setDiscount(discount);

            const state = useCartStore.getState();
            const total = state.getTotal();
            const expected = Math.max(0, subtotal - discountAmount);

            return Math.abs(total - expected) < 0.001;
          }
        ),
        { numRuns: 200 }
      );
    });

    it('clearCart resets subtotal and total to 0', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.tuple(productArbitrary, quantityArbitrary),
            { minLength: 1, maxLength: 10 }
          ),
          discountArbitrary,
          (itemPairs, discount) => {
            useCartStore.setState({ items: [], discount: null });
            const store = useCartStore.getState();

            for (const [product, qty] of itemPairs) {
              store.addItem(product, qty);
            }
            store.setDiscount(discount);
            store.clearCart();

            const state = useCartStore.getState();
            return (
              state.getSubtotal() === 0 &&
              state.getTotal() === 0 &&
              state.items.length === 0 &&
              state.discount === null
            );
          }
        ),
        { numRuns: 200 }
      );
    });
  });
});
