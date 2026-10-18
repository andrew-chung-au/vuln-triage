import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { getUser } from "@/lib/auth";
import { validateRiskReason } from "@/lib/validation";
import { services } from "@/services";

export const Route = createFileRoute("/_authed/findings/$findingId_/accept")({
  head: () => ({
    meta: [
      { title: "Accept risk — VulnTriage" },
      { name: "description", content: "Record a reasoned risk acceptance for a finding." },
      { property: "og:title", content: "Accept risk — VulnTriage" },
      { property: "og:description", content: "Record a reasoned risk acceptance for a finding." },
    ],
  }),
  component: Accept,
});

function Accept() {
  const { findingId } = Route.useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: f } = useQuery({ queryKey: ["finding", findingId], queryFn: () => services.getFinding(findingId) });
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = validateRiskReason(reason);
    if (v) return setError(v);
    const user = getUser();
    if (!user) return;
    setBusy(true);
    try {
      await services.acceptRisk(findingId, reason, user);
      await qc.invalidateQueries();
      navigate({ to: "/findings/$findingId", params: { findingId } });
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="max-w-xl space-y-4">
      <Link to="/findings/$findingId" params={{ findingId }} className="text-sm text-muted-foreground hover:text-foreground">← Back to finding</Link>
      <h1 className="text-xl font-semibold">Accept risk</h1>
      {f && <p className="text-sm"><span className="font-mono">{f.packageName}@{f.installedVersion}</span> on {f.asset.name} · {f.vulnerabilityId}</p>}
      {f && f.status !== "open" ? (
        <p className="text-sm text-muted-foreground">Only open findings can be risk accepted.</p>
      ) : (
        <form onSubmit={submit} className="space-y-3 rounded-md border bg-card p-4">
          <div className="space-y-1.5">
            <Label htmlFor="reason">Reason (required)</Label>
            <Textarea id="reason" rows={4} value={reason} onChange={(e) => { setReason(e.target.value); setError(null); }} />
          </div>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          <Button type="submit" disabled={busy}>Accept risk</Button>
        </form>
      )}
    </div>
  );
}
