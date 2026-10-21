import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Flag, formatDate } from "@/components/vt/Badges";
import { ServiceError, isOwnerless, services, type ScanStatus } from "@/services";

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

const SCAN_TONE: Record<ScanStatus, "default" | "danger" | "warning" | "muted"> = {
  "not yet scanned": "muted",
  "scan failed": "danger",
  "scanned, findings": "default",
  "scanned, incomplete": "warning",
  "scanned, clean": "default",
};

function Assets() {
  const qc = useQueryClient();
  const assets = useQuery({ queryKey: ["assets"], queryFn: () => services.listAssets() });
  const findings = useQuery({ queryKey: ["findings"], queryFn: () => services.listFindings() });
  const [notice, setNotice] = useState<Record<string, { ok: boolean; text: string }>>({});
  const counts = new Map<string, number>();
  findings.data?.forEach((f) => counts.set(f.assetId, (counts.get(f.assetId) ?? 0) + 1));

  async function reScan(assetId: string) {
    try {
      await services.reScan(assetId);
      setNotice((n) => ({ ...n, [assetId]: { ok: true, text: "Re-scan requested" } }));
    } catch (err) {
      const text = err instanceof ServiceError ? err.message : "Something went wrong.";
      setNotice((n) => ({ ...n, [assetId]: { ok: false, text } }));
    }
    await qc.invalidateQueries({ queryKey: ["assets"] });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <h1 className="text-xl font-semibold">Assets</h1>
        <Button asChild><Link to="/assets/new">Register asset</Link></Button>
      </div>
      <div className="overflow-x-auto rounded-md border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted text-left text-xs uppercase text-muted-foreground">
            <tr><th className="px-3 py-2">Name</th><th className="px-3 py-2">Owner</th><th className="px-3 py-2">Criticality</th><th className="px-3 py-2">Internet-facing</th><th className="px-3 py-2">Scan</th><th className="px-3 py-2">Findings</th><th className="px-3 py-2">Actions</th></tr>
          </thead>
          <tbody className="divide-y divide-border">
            {assets.data?.map((a) => {
              const n = counts.get(a.id) ?? 0;
              return (
                <tr key={a.id}>
                  <td className="px-3 py-2 font-mono">{a.name}</td>
                  <td className="px-3 py-2" data-testid={`asset-owner-${a.id}`}>
                    {isOwnerless(a) ? <Flag tone="warning">ownerless</Flag> : (
                      <span>
                        <span>{a.ownerName ?? "—"}</span>
                        <span className="block text-xs text-muted-foreground">{a.ownerEmail ?? "—"}</span>
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2">{a.criticality}</td>
                  <td className="px-3 py-2">{a.internetFacing ? "yes" : "no"}</td>
                  <td className="px-3 py-2" data-testid={`asset-scan-${a.id}`}>
                    <Flag tone={SCAN_TONE[a.scanStatus]}>{a.scanStatus}</Flag>
                    {a.scanFailureReason && <span className="block text-xs text-muted-foreground">{a.scanFailureReason}</span>}
                    {a.scanWarnings.length > 0 && (
                      <ul className="mt-1 text-xs text-muted-foreground">
                        {a.scanWarnings.map((w, i) => <li key={i}>{w.file}{w.line !== null ? `:${w.line}` : ""} {w.message}</li>)}
                      </ul>
                    )}
                    <span className="block text-xs text-muted-foreground">{a.lastScanAt ? `Last scan ${formatDate(a.lastScanAt)}` : "Never scanned"}</span>
                  </td>
                  <td className="px-3 py-2">{n === 0 ? "none" : `${n} finding${n > 1 ? "s" : ""}`}</td>
                  <td className="px-3 py-2">
                    <Button variant="outline" size="sm" onClick={() => reScan(a.id)} aria-label={`Re-scan ${a.name}`}>Re-scan</Button>
                    {notice[a.id] && (
                      <p role={notice[a.id]!.ok ? "status" : "alert"} className={notice[a.id]!.ok ? "mt-1 text-xs text-muted-foreground" : "mt-1 text-xs text-destructive"}>
                        {notice[a.id]!.text}
                      </p>
                    )}
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
