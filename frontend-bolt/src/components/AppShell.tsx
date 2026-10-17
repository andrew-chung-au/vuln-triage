import type { ReactNode } from 'react';
import { useApp } from '../app/AppContext';
import { Shield, LayoutDashboard, Server, PlusCircle, LogOut } from 'lucide-react';

export function AppShell({ children }: { children: ReactNode }) {
  const { user, route, navigate, signOut } = useApp();

  const navItem = (
    label: string,
    active: boolean,
    onClick: () => void,
    icon: ReactNode,
  ) => (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
        active
          ? 'bg-slate-900 text-white'
          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
      }`}
    >
      {icon}
      {label}
    </button>
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-slate-900" />
            <span className="text-base font-semibold tracking-tight">
              VulnTriage
            </span>
          </div>
          {user && (
            <div className="flex items-center gap-2">
              <nav className="hidden items-center gap-1 sm:flex">
                {navItem(
                  'Dashboard',
                  route.name === 'dashboard' || route.name === 'finding',
                  () => navigate({ name: 'dashboard' }),
                  <LayoutDashboard className="h-4 w-4" />,
                )}
                {navItem(
                  'Assets',
                  route.name === 'assets' || route.name === 'register-asset',
                  () => navigate({ name: 'assets' }),
                  <Server className="h-4 w-4" />,
                )}
                {navItem(
                  'Register asset',
                  route.name === 'register-asset',
                  () => navigate({ name: 'register-asset' }),
                  <PlusCircle className="h-4 w-4" />,
                )}
              </nav>
              <div className="flex items-center gap-3 border-l border-slate-200 pl-3">
                <div className="text-right">
                  <div className="text-sm font-medium leading-tight">
                    {user.name}
                  </div>
                  <div className="text-xs leading-tight text-slate-500">
                    {user.email}
                  </div>
                </div>
                <button
                  onClick={signOut}
                  className="flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                  title="Sign out"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
        {user && (
          <div className="mx-auto flex max-w-6xl gap-1 px-4 pb-2 sm:hidden">
            {navItem(
              'Dashboard',
              route.name === 'dashboard' || route.name === 'finding',
              () => navigate({ name: 'dashboard' }),
              <LayoutDashboard className="h-4 w-4" />,
            )}
            {navItem(
              'Assets',
              route.name === 'assets',
              () => navigate({ name: 'assets' }),
              <Server className="h-4 w-4" />,
            )}
            {navItem(
              'Register',
              route.name === 'register-asset',
              () => navigate({ name: 'register-asset' }),
              <PlusCircle className="h-4 w-4" />,
            )}
          </div>
        )}
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
