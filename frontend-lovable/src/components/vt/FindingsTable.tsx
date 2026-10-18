import { Link } from "@tanstack/react-router";
import type { FindingWithAsset } from "@/services/types";
import { Flag, StatusBadge, TierBadge, formatEpss } from "./Badges";

function Row({ f }: { f: FindingWithAsset }) {
  const withdrawn = f.status === "withdrawn";
  return (
    <tr data-testid="finding-row" data-id={f.id} className={withdrawn ? "bg-muted/60 text-muted-foreground" : "hover:bg-muted/40"}>
      <td className="px-3 py-2 align-top"><TierBadge tier={f.tier} /></td>
      <td className="px-3 py-2 align-top">{f.asset.name}</td>
      <td className="px-3 py-2 align-top">
        <Link to="/findings/$findingId" params={{ findingId: f.id }} className="font-mono text-primary underline-offset-2 hover:underline">
          {f.packageName}@{f.installedVersion}
        </Link>
        <div className="font-mono text-xs text-muted-foreground">{f.vulnerabilityId}</div>
      </td>
      <td className="px-3 py-2 align-top">
        <StatusBadge status={f.status} />
        {withdrawn && <div className="mt-1 text-xs">left its feed</div>}
      </td>
      <td className="px-3 py-2 align-top">
        <div className="flex flex-wrap gap-1">
          <Flag tone={f.kev ? "danger" : "muted"}>KEV: {f.kev ? "yes" : "no"}</Flag>
          <Flag>{formatEpss(f.epss)}</Flag>
          <Flag>criticality: {f.asset.criticality}</Flag>
          <Flag tone={f.asset.internetFacing ? "warning" : "muted"}>
            {f.asset.internetFacing ? "internet-facing" : "internal"}
          </Flag>
        </div>
      </td>
    </tr>
  );
}

function Table({ rows }: { rows: FindingWithAsset[] }) {
  return (
    <div className="overflow-x-auto rounded-md border bg-card">
      <table className="w-full text-sm">
        <thead className="bg-muted text-left text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2">Tier</th>
            <th className="px-3 py-2">Asset</th>
            <th className="px-3 py-2">Package</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Why it ranks here</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((f) => <Row key={f.id} f={f} />)}
        </tbody>
      </table>
    </div>
  );
}

/** Renders findings exactly in the order given. Never re-sorts. */
export function FindingsTable({ findings, groupByAsset = false }: { findings: FindingWithAsset[]; groupByAsset?: boolean }) {
  if (findings.length === 0) {
    return (
      <div className="rounded-md border border-dashed bg-card p-10 text-center">
        <p className="font-medium">No findings</p>
        <p className="text-sm text-muted-foreground">Nothing matches the current filters.</p>
      </div>
    );
  }
  if (!groupByAsset) return <Table rows={findings} />;

  const groups: { name: string; rows: FindingWithAsset[] }[] = [];
  for (const f of findings) {
    let g = groups.find((x) => x.name === f.asset.name);
    if (!g) groups.push((g = { name: f.asset.name, rows: [] }));
    g.rows.push(f);
  }
  return (
    <div className="space-y-6">
      {groups.map((g) => (
        <section key={g.name}>
          <h3 className="mb-2 font-mono text-sm font-semibold">{g.name} <span className="text-muted-foreground">({g.rows.length})</span></h3>
          <Table rows={g.rows} />
        </section>
      ))}
    </div>
  );
}
