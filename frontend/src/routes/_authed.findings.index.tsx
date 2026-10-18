import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { FindingsTable } from "@/components/vt/FindingsTable";
import { services, STATUS_LABEL, type FindingStatus } from "@/services";

export const Route = createFileRoute("/_authed/findings/")({
  head: () => ({
    meta: [
      { title: "Findings — VulnTriage" },
      { name: "description", content: "Vulnerable dependencies ranked P1 to P4 by KEV, EPSS and asset context." },
      { property: "og:title", content: "Findings — VulnTriage" },
      { property: "og:description", content: "Ranked vulnerability findings across your assets." },
    ],
  }),
  component: Findings,
});

const sel = "h-9 rounded-md border border-input bg-card px-2 text-sm";

function Findings() {
  const { data, isLoading } = useQuery({ queryKey: ["findings"], queryFn: () => services.listFindings() });
  const [asset, setAsset] = useState("all");
  const [status, setStatus] = useState<"all" | FindingStatus>("all");
  const [group, setGroup] = useState(false);

  const findings = data ?? [];
  const assetNames = Array.from(new Set(findings.map((f) => f.asset.name))).sort();
  const visible = findings.filter((f) => (asset === "all" || f.asset.name === asset) && (status === "all" || f.status === status));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Findings</h1>
          <p className="text-sm text-muted-foreground">Ranked by priority tier, P1 highest.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <select aria-label="Filter by asset" className={sel} value={asset} onChange={(e) => setAsset(e.target.value)}>
            <option value="all">All assets</option>
            {assetNames.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <select aria-label="Filter by status" className={sel} value={status} onChange={(e) => setStatus(e.target.value as typeof status)}>
            <option value="all">All statuses</option>
            {(Object.keys(STATUS_LABEL) as FindingStatus[]).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
          <label className="flex items-center gap-1.5">
            <input type="checkbox" checked={group} onChange={(e) => setGroup(e.target.checked)} /> Group by asset
          </label>
        </div>
      </div>
      {isLoading ? <p className="text-sm text-muted-foreground">Loading…</p> : <FindingsTable findings={visible} groupByAsset={group} />}
    </div>
  );
}
