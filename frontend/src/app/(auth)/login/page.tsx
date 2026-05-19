import { LoginForm } from '@/features/auth/components/LoginForm';
import { DemoAccounts } from '@/features/auth/components/DemoAccounts';

export const metadata = {
  title: 'Login — Vendora POS',
  description: 'Sign in to your Vendora POS account',
};

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
      <div className="w-full max-w-sm space-y-6">
        {/* Branding */}
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-primary-600">
            Vendora
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            Point of Sale
          </p>
        </div>

        {/* Login Card */}
        <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
          <h2 className="mb-6 text-lg font-semibold text-neutral-900">
            Sign in to your account
          </h2>
          <LoginForm />
        </div>

        {/* Demo Accounts */}
        <DemoAccounts />
      </div>
    </div>
  );
}
