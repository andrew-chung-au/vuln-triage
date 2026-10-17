import { useState } from 'react';
import { useApp } from '../app/AppContext';
import { DEMO_CREDENTIALS } from '../services/mockServices';
import { Shield, AlertCircle } from 'lucide-react';

export function LoginScreen() {
  const { signIn } = useApp();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const res = signIn(email.trim(), password);
    if (!res.ok) {
      setError(res.error ?? 'Sign in failed.');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6 flex items-center gap-2">
          <Shield className="h-6 w-6 text-slate-900" />
          <span className="text-lg font-semibold tracking-tight">VulnTriage</span>
        </div>
        <h1 className="mb-1 text-base font-semibold text-slate-900">
          Sign in
        </h1>
        <p className="mb-6 text-sm text-slate-500">
          Triage vulnerable dependencies by real-world exploit risk.
        </p>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="login-email"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              Email
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setError(null);
              }}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label
              htmlFor="login-password"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              Password
            </label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError(null);
              }}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
          >
            Sign in
          </button>
        </form>

        <div className="mt-6 rounded-md border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs font-medium text-slate-500">Demo credentials</p>
          <p className="mt-1 text-sm text-slate-700">
            Email: <span className="font-mono">{DEMO_CREDENTIALS.email}</span>
          </p>
          <p className="text-sm text-slate-700">
            Password: <span className="font-mono">{DEMO_CREDENTIALS.password}</span>
          </p>
        </div>
      </div>
    </div>
  );
}
