import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { User } from '../types';
import { services } from '../services';

export type Route =
  | { name: 'login' }
  | { name: 'dashboard' }
  | { name: 'finding'; findingId: string }
  | { name: 'assets' }
  | { name: 'register-asset' };

interface AppContextValue {
  user: User | null;
  route: Route;
  navigate: (route: Route) => void;
  signIn: (email: string, password: string) => { ok: boolean; error?: string };
  signOut: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => services.currentUser());
  const [route, setRoute] = useState<Route>(() =>
    services.currentUser() ? { name: 'dashboard' } : { name: 'login' },
  );

  const navigate = useCallback((r: Route) => setRoute(r), []);

  const signIn = useCallback((email: string, password: string) => {
    const res = services.signIn({ email, password });
    if (res.ok && res.user) {
      setUser(res.user);
      setRoute({ name: 'dashboard' });
      return { ok: true };
    }
    return { ok: false, error: res.error };
  }, []);

  const signOut = useCallback(() => {
    services.signOut();
    setUser(null);
    setRoute({ name: 'login' });
  }, []);

  const value = useMemo<AppContextValue>(
    () => ({ user, route, navigate, signIn, signOut }),
    [user, route, navigate, signIn, signOut],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
