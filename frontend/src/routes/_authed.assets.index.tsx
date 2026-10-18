import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Flag } from "@/components/vt/Badges";
import { services } from "@/services";

export const Route = createFileRoute("/_authed/assets/")({
  head: () => ({
    meta: [
      { title: "Assets — VulnTriage" },
      { name: "description", content: "Registered assets with owner, criticality, exposure and scan state." },
      { property: "og:title", content: "Assets — VulnTriage" },
      { property: "og:description", content: "Registered assets and who owns each fix." },
    ],
  }),
  component: Assets,
});

function Assets() {
  const assets = useQuery({ queryKey: ["assets"], queryFn: () => services.listAssets() });
  const findings = useQuery({ queryKey: ["findings"], queryFn: () => services.listFindings() });
  const counts = new Map<string, number>();
  findings.data?.forEach((f) => counts.set(f.assetId, (counts.get(f.assetId) ?? 0) + 1));

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <h1 className="text-xl font-semibold">Assets</h1>
        <Button asChild><Link to="/assets/new">Register asset</Link></Button>
      </div>
      <div className="overflow-x-auto rounded-md border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted text-left text-xs uppercase text-muted-foreground">
            <tr><th className="px-3 py-2">Name</th><th className="px-3 py-2">Owner</th><th className="px-3 py-2">Criticality</th><th className="px-3 py-2">Internet-facing</th><th className="px-3 py-2">Scan</th></tr>
          </thead>
          <tbody className="divide-y divide-border">
            {assets.data?.map((a) => {
              const n = counts.get(a.id) ?? 0;
              return (
                <tr key={a.id}>
                  <td className="px-3 py-2 font-mono">{a.name}</td>
                  <td className="px-3 py-2">{a.owner ?? <Flag tone="warning">ownerless</Flag>}</td>
                  <td className="px-3 py-2">{a.criticality}</td>
                  <td className="px-3 py-2">{a.internetFacing ? "yes" : "no"}</td>
                  <td className="px-3 py-2">
                    {a.scanStatus === "scan_error" ? <Flag tone="danger">scan error</Flag>
                      : a.scanStatus === "not_scanned" ? <Flag tone="muted">not yet scanned</Flag>
                      : n === 0 ? <Flag>no findings</Flag> : <span>{n} finding{n > 1 ? "s" : ""}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
