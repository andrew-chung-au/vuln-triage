import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { setUser } from "@/lib/auth";
import { services } from "@/services";
import { DEMO_CREDENTIALS } from "@/services/mockData";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in — VulnTriage" },
      { name: "description", content: "Sign in to VulnTriage to triage vulnerable dependencies by exploit risk." },
      { property: "og:title", content: "Sign in — VulnTriage" },
      { property: "og:description", content: "Rank vulnerable dependencies by real-world exploit risk." },
    ],
  }),
  component: Login,
});

function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await services.login(username, password);
      setUser(user);
      navigate({ to: "/findings" });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <div>
          <h1 className="font-mono text-2xl font-bold">VulnTriage</h1>
          <p className="text-sm text-muted-foreground">Rank vulnerable dependencies by exploit risk.</p>
        </div>
        <form onSubmit={submit} className="space-y-4 rounded-md border bg-card p-5">
          <div className="space-y-1.5">
            <Label htmlFor="u">Username</Label>
            <Input id="u" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p">Password</Label>
            <Input id="p" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </div>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={busy}>Sign in</Button>
        </form>
        <div className="rounded-md border border-dashed p-3 text-sm">
          <p className="font-medium">Demo credentials (fictional)</p>
          <p className="font-mono">{DEMO_CREDENTIALS.username}</p>
          <p className="font-mono">{DEMO_CREDENTIALS.password}</p>
        </div>
      </div>
    </main>
  );
}
