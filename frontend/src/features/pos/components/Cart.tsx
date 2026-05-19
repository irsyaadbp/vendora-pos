'use client';

import { useCartStore } from '@/core/stores/cart.store';
import { Button } from '@/shared/ui';
import { formatCurrency } from '@/shared/utils/formatters';

export function Cart() {
  const items = useCartStore((state) => state.items);
  const discount = useCartStore((state) => state.discount);
  const updateQuantity = useCartStore((state) => state.updateQuantity);
  const removeItem = useCartStore((state) => state.removeItem);
  const getSubtotal = useCartStore((state) => state.getSubtotal);
  const getTotal = useCartStore((state) => state.getTotal);

  const subtotal = getSubtotal();
  const total = getTotal();

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-12 w-12 text-neutral-300"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
        <p className="mt-3 text-sm text-neutral-500">Cart is empty</p>
        <p className="text-xs text-neutral-400">Search and add products to get started</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Cart Items */}
      <div className="flex-1 overflow-y-auto">
        <ul className="divide-y divide-neutral-100" role="list" aria-label="Cart items">
          {items.map((item) => (
            <li key={item.product.id} className="py-3">
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-neutral-900">
                    {item.product.name}
                  </p>
                  <p className="text-xs text-neutral-500">
                    {formatCurrency(item.product.price)} each
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => removeItem(item.product.id)}
                  aria-label={`Remove ${item.product.name} from cart`}
                  className="ml-2 rounded p-1 text-neutral-400 hover:bg-neutral-100 hover:text-danger-600 transition-colors"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>

              {/* Quantity Controls */}
              <div className="mt-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      updateQuantity(item.product.id, item.quantity - 1)
                    }
                    aria-label={`Decrease quantity of ${item.product.name}`}
                  >
                    −
                  </Button>
                  <span className="min-w-8 text-center text-sm font-medium">
                    {item.quantity}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      updateQuantity(item.product.id, item.quantity + 1)
                    }
                    disabled={item.quantity >= item.product.stock}
                    aria-label={`Increase quantity of ${item.product.name}`}
                  >
                    +
                  </Button>
                </div>
                <span className="text-sm font-semibold text-neutral-900">
                  {formatCurrency(item.subtotal)}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* Cart Summary */}
      <div className="border-t border-neutral-200 pt-3 mt-3 space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-neutral-600">Subtotal</span>
          <span className="font-medium text-neutral-900">
            {formatCurrency(subtotal)}
          </span>
        </div>

        {discount && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-600">
              Discount
              {discount.type === 'percentage'
                ? ` (${discount.value}%)`
                : ''}
            </span>
            <span className="font-medium text-danger-600">
              -{formatCurrency(discount.amount)}
            </span>
          </div>
        )}

        <div className="flex items-center justify-between border-t border-neutral-200 pt-2">
          <span className="text-base font-semibold text-neutral-900">Total</span>
          <span className="text-lg font-bold text-primary-600">
            {formatCurrency(total)}
          </span>
        </div>
      </div>
    </div>
  );
}
