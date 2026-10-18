import { cn } from "@/lib/utils";
import { STATUS_LABEL, type FindingStatus, type Tier } from "@/services/types";

const tierClass: Record<Tier, string> = {
  P1: "bg-tier-p1 text-tier-foreground",
  P2: "bg-tier-p2 text-tier-foreground",
  P3: "bg-tier-p3 text-foreground",
  P4: "bg-tier-p4 text-foreground",
};

export function TierBadge({ tier }: { tier: Tier }) {
  return (
    <span data-testid="tier" className={cn("inline-flex min-w-9 justify-center rounded px-1.5 py-0.5 font-mono text-xs font-bold", tierClass[tier])}>
      {tier}
    </span>
  );
}

const statusClass: Record<FindingStatus, string> = {
  open: "border-foreground/30",
  risk_accepted: "border-warning bg-warning/15",
  fixed: "border-success bg-success/15",
  withdrawn: "border-dashed border-muted-foreground text-muted-foreground line-through",
};

export function StatusBadge({ status }: { status: FindingStatus }) {
  return (
    <span className={cn("inline-flex rounded border px-1.5 py-0.5 text-xs font-medium", statusClass[status])}>
      {STATUS_LABEL[status]}
    </span>
  );
}

export function Flag({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "danger" | "warning" | "muted" }) {
  const tones = {
    default: "bg-secondary text-secondary-foreground",
    danger: "bg-destructive/15 text-destructive",
    warning: "bg-warning/20 text-foreground",
    muted: "bg-muted text-muted-foreground",
  };
  return <span className={cn("inline-flex rounded px-1.5 py-0.5 text-xs font-medium", tones[tone])}>{children}</span>;
}

export const formatEpss = (epss: number | null) => (epss === null ? "EPSS: n/a" : `EPSS: ${epss.toFixed(2)}`);
export const formatDate = (iso: string) => new Date(iso).toISOString().replace("T", " ").slice(0, 16) + " UTC";
