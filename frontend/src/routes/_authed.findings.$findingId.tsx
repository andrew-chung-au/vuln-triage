import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { AffectedRanges } from "@/components/vt/AffectedRanges";
import { AuditTrail } from "@/components/vt/AuditTrail";
import { Flag, StatusBadge, TierBadge, formatDate, formatEpss } from "@/components/vt/Badges";
import { ServiceError, isOwnerless, services } from "@/services";

export const Route = createFileRoute("/_authed/findings/$findingId")({
  head: () => ({
    meta: [
      { title: "Finding detail — VulnTriage" },
      { name: "description", content: "Vulnerability ids, affected ranges, brief, exploit signals and audit trail." },
      { property: "og:title", content: "Finding detail — VulnTriage" },
      { property: "og:description", content: "Full context for a vulnerable dependency finding." },
    ],
  }),
  component: Detail,
});

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h2>
      {children}
    </section>
  );
}

function Detail() {
  const { findingId } = Route.useParams();
  const { data: f, isLoading, error } = useQuery({ queryKey: ["finding", findingId], queryFn: () => services.getFinding(findingId) });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (error || !f) {
    const message = error instanceof ServiceError ? error.message : "Something went wrong.";
    return <p>{message} <Link to="/findings" className="text-primary underline">Back to findings</Link></p>;
  }

  return (
    <div className="space-y-6">
      <Link to="/findings" className="text-sm text-muted-foreground hover:text-foreground">← Findings</Link>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2"><TierBadge tier={f.tier} /><StatusBadge status={f.status} /></div>
          <h1 className="font-mono text-xl font-semibold">{f.packageName}@{f.installedVersion}</h1>
          <p className="text-sm text-muted-foreground">on {f.asset.name}</p>
        </div>
        {f.status === "open" && (
          <Button asChild variant="outline">
            <Link to="/findings/$findingId/accept" params={{ findingId: f.id }}>Accept risk</Link>
          </Button>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Section title="Identifiers">
          <p className="font-mono text-sm font-medium">{f.vulnerabilityId}</p>
          {f.aliases.length ? (
            <ul className="font-mono text-sm text-muted-foreground">{f.aliases.map((a) => <li key={a}>alias: {a}</li>)}</ul>
          ) : <p className="text-sm text-muted-foreground">No aliases</p>}
        </Section>
        <Section title="Status">
          <StatusBadge status={f.status} />
          {f.status === "fixed" && f.fixedAt && <p className="text-sm">Fixed at {formatDate(f.fixedAt)}</p>}
          {f.status === "withdrawn" && <p className="text-sm text-muted-foreground">This vulnerability was withdrawn: it left its advisory feed.</p>}
        </Section>
        <Section title="Affected version ranges"><AffectedRanges ranges={f.affectedRanges} /></Section>
        <Section title="Exploit signals & asset context">
          <div className="flex flex-wrap gap-1">
            <Flag tone={f.kev ? "danger" : "muted"}>KEV: {f.kev ? "yes" : "no"}</Flag>
            <Flag>{formatEpss(f.epss)}</Flag>
          </div>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-muted-foreground">Owner</dt>
            <dd data-testid="asset-owner">
              {isOwnerless(f.asset) ? <Flag tone="warning">ownerless</Flag> : (
                <span>
                  <span>{f.asset.ownerName ?? "—"}</span>
                  <span className="block text-muted-foreground">{f.asset.ownerEmail ?? "—"}</span>
                </span>
              )}
            </dd>
            <dt className="text-muted-foreground">Criticality</dt><dd>{f.asset.criticality}</dd>
            <dt className="text-muted-foreground">Internet-facing</dt><dd>{f.asset.internetFacing ? "yes" : "no"}</dd>
          </dl>
        </Section>
      </div>

      <Section title="Brief">
        {f.briefStatus === "available" && f.brief ? (
          <div className="space-y-2 rounded-md border bg-card p-4 text-sm">
            <p className="font-medium">{f.brief.summary}</p>
            <p><span className="text-muted-foreground">Impact: </span>{f.brief.impact}</p>
            <p><span className="text-muted-foreground">Remediation: </span>{f.brief.remediation}</p>
            <p><span className="text-muted-foreground">Advisory: </span><a href={f.brief.advisoryReference} target="_blank" rel="noreferrer" className="break-all text-primary underline">{f.brief.advisoryReference}</a></p>
          </div>
        ) : (
          <div className="space-y-2 rounded-md border bg-card p-4 text-sm">
            <Flag tone="warning">brief unavailable</Flag>
            <p>{f.structuredSummary}</p>
            <p className="text-muted-foreground">Package {f.packageName} {f.installedVersion} · {f.vulnerabilityId}</p>
          </div>
        )}
      </Section>

      <Section title="Audit trail">
        <AuditTrail entries={f.auditTrail} />
      </Section>
    </div>
  );
}
