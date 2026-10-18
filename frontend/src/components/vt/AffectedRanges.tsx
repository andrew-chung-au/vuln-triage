import type { AffectedRange } from "@/services/types";

export function AffectedRanges({ ranges }: { ranges: AffectedRange[] }) {
  return (
    <ul className="divide-y divide-border rounded-md border">
      {ranges.map((r, i) => (
        <li key={i} data-testid="affected-range" className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm">
          <span className="font-mono">{r.range}</span>
          {r.fixedVersion ? (
            <span>
              fixed in <span className="font-mono font-medium">{r.fixedVersion}</span>
            </span>
          ) : (
            <span className="font-medium text-destructive">no fixed version</span>
          )}
        </li>
      ))}
    </ul>
  );
}
