'use client';

const DEMO_ACCOUNTS = [
  {
    role: 'Admin',
    email: 'admin@vendora.com',
    password: 'admin123',
    description: 'Full access: dashboard, users, products, inventory, POS',
  },
  {
    role: 'Staff',
    email: 'staff@vendora.com',
    password: 'staff123',
    description: 'POS and transaction history only',
  },
];

export function DemoAccounts() {
  const handleCopy = (email: string, password: string) => {
    // Fill the form inputs directly
    const emailInput = document.querySelector<HTMLInputElement>('input[type="email"]');
    const passwordInput = document.querySelector<HTMLInputElement>('input[type="password"]');

    if (emailInput && passwordInput) {
      // Trigger React-compatible value setting
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        'value'
      )?.set;

      if (nativeInputValueSetter) {
        nativeInputValueSetter.call(emailInput, email);
        emailInput.dispatchEvent(new Event('input', { bubbles: true }));

        nativeInputValueSetter.call(passwordInput, password);
        passwordInput.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }
  };

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
      <p className="mb-3 text-center text-xs font-medium uppercase tracking-wide text-neutral-500">
        Demo Accounts
      </p>
      <div className="space-y-2">
        {DEMO_ACCOUNTS.map((account) => (
          <button
            key={account.role}
            type="button"
            onClick={() => handleCopy(account.email, account.password)}
            className="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-left transition-colors hover:border-primary-300 hover:bg-primary-50"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-neutral-900">
                {account.role}
              </span>
              <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600">
                Click to fill
              </span>
            </div>
            <p className="mt-0.5 text-xs text-neutral-500">
              {account.email} / {account.password}
            </p>
            <p className="mt-0.5 text-xs text-neutral-400">
              {account.description}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
