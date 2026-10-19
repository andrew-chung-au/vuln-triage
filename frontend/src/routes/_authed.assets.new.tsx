import { useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { validateAssetName } from "@/lib/validation";
import { ServiceError, services, type Criticality } from "@/services";

export const Route = createFileRoute("/_authed/assets/new")({
  head: () => ({
    meta: [
      { title: "Register asset — VulnTriage" },
      { name: "description", content: "Register a new asset for dependency scanning." },
      { property: "og:title", content: "Register asset — VulnTriage" },
      { property: "og:description", content: "Register a new asset for dependency scanning." },
    ],
  }),
  component: NewAsset,
});

function NewAsset() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [criticality, setCriticality] = useState<Criticality>("medium");
  const [internetFacing, setInternetFacing] = useState(false);
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = validateAssetName(name);
    if (v) return setError(v);
    try {
      await services.registerAsset({ name, ownerName, ownerEmail, criticality, internetFacing, repositoryUrl });
      await qc.invalidateQueries({ queryKey: ["assets"] });
      navigate({ to: "/assets" });
    } catch (err) {
      setError(err instanceof ServiceError ? err.message : "Something went wrong.");
    }
  }

  return (
    <div className="max-w-xl space-y-4">
      <Link to="/assets" className="text-sm text-muted-foreground hover:text-foreground">← Assets</Link>
      <h1 className="text-xl font-semibold">Register asset</h1>
      <form onSubmit={submit} className="space-y-4 rounded-md border bg-card p-4">
        <div className="space-y-1.5"><Label htmlFor="name">Name (required)</Label><Input id="name" value={name} onChange={(e) => { setName(e.target.value); setError(null); }} /></div>
        <div className="space-y-1.5"><Label htmlFor="owner-name">Owner name (optional)</Label><Input id="owner-name" value={ownerName} onChange={(e) => setOwnerName(e.target.value)} /></div>
        <div className="space-y-1.5"><Label htmlFor="owner-email">Owner email (optional)</Label><Input id="owner-email" type="text" placeholder="team@example.com" value={ownerEmail} onChange={(e) => setOwnerEmail(e.target.value)} /></div>
        <div className="space-y-1.5">
          <Label htmlFor="crit">Criticality</Label>
          <select id="crit" className="h-9 w-full rounded-md border border-input bg-card px-2 text-sm" value={criticality} onChange={(e) => setCriticality(e.target.value as Criticality)}>
            {(["low", "medium", "high", "critical"] as const).map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={internetFacing} onChange={(e) => setInternetFacing(e.target.checked)} /> Internet-facing</label>
        <div className="space-y-1.5"><Label htmlFor="repo">Repository URL</Label><Input id="repo" type="text" value={repositoryUrl} onChange={(e) => setRepositoryUrl(e.target.value)} /></div>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <Button type="submit">Register</Button>
      </form>
    </div>
  );
}
