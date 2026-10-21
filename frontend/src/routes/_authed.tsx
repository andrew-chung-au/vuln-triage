import { Link, Outlet, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { setUser, useUser } from "@/lib/auth";
import { services } from "@/services";

export const Route = createFileRoute("/_authed")({
  component: AuthedLayout,
});

function AuthedLayout() {
  const user = useUser();
  const navigate = useNavigate();

  useEffect(() => {
    if (user === null) navigate({ to: "/login" });
  }, [user, navigate]);

  if (!user) return null;

  async function signOut() {
    try {
      await services.logout();
    } finally {
      setUser(null);
      navigate({ to: "/login" });
    }
  }

  const nav = "rounded px-2 py-1 text-sm text-muted-foreground hover:text-foreground";
  const active = { className: "rounded px-2 py-1 text-sm bg-secondary text-foreground font-medium" };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
          <span className="font-mono font-bold">VulnTriage</span>
          <nav className="flex gap-1">
            <Link to="/findings" className={nav} activeProps={active}>Findings</Link>
            <Link to="/assets" className={nav} activeProps={active} activeOptions={{ exact: true }}>Assets</Link>
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="text-muted-foreground">{user.displayName}</span>
            <Button variant="outline" size="sm" onClick={signOut}>Sign out</Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
