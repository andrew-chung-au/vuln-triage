import { STATUS_LABEL, type AuditEntry, type FindingStatus } from "@/services";
import { formatDate } from "./Badges";

const isStatus = (value: string): value is FindingStatus => value in STATUS_LABEL;

/** Stored audit values are wire values; the screen shows the human label. */
export function formatAuditValue(field: string, value: string | null): string {
  if (value === null) return "—";
  return field === "status" && isStatus(value) ? STATUS_LABEL[value] : value;
}

export function AuditTrail({ entries }: { entries: AuditEntry[] }) {
  if (entries.length === 0) return <p className="text-sm text-muted-foreground">No changes recorded.</p>;

  return (
    <div className="overflow-x-auto rounded-md border bg-card">
      <table className="w-full text-sm">
        <thead className="bg-muted text-left text-xs uppercase text-muted-foreground">
          <tr><th className="px-3 py-2">Who</th><th className="px-3 py-2">When</th><th className="px-3 py-2">Previous</th><th className="px-3 py-2">New</th><th className="px-3 py-2">Reason</th></tr>
        </thead>
        <tbody className="divide-y divide-border">
          {entries.map((a) => (
            <tr key={a.id}>
              <td className="px-3 py-2">{a.actorDisplayName ?? a.actor}</td>
              <td className="px-3 py-2 font-mono text-xs">{formatDate(a.createdAt)}</td>
              <td className="px-3 py-2">{formatAuditValue(a.field, a.previousValue)}</td>
              <td className="px-3 py-2">{formatAuditValue(a.field, a.newValue)}</td>
              <td className="px-3 py-2">{a.reason ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
