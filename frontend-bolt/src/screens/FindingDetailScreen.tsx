import { useMemo, useState } from 'react';
import { services } from '../services';
import { useApp } from '../app/AppContext';
import {
  TierBadge,
  StatusBadge,
  KevBadge,
  EpssText,
  CriticalityBadge,
} from '../components/Badges';
import { RiskAcceptanceForm } from './RiskAcceptanceForm';
import { ArrowLeft, ShieldAlert, ExternalLink } from 'lucide-react';
import type { Finding } from '../types';

export function FindingDetailScreen({ findingId }: { findingId: string }) {
  const { navigate } = useApp();
  const [finding, setFinding] = useState<Finding | null>(() =>
    services.getFinding(findingId),
  );
  const asset = useMemo(
    () => (finding ? services.getAsset(finding.assetId) : null),
    [finding],
  );

  if (!finding) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-8 text-center">
        <p className="text-sm text-slate-600">Finding not found.</p>
        <button
          onClick={() => navigate({ name: 'dashboard' })}
          className="mt-3 text-sm font-medium text-slate-900 underline"
        >
          Back to dashboard
        </button>
      </div>
    );
  }

  const onAccepted = () => {
    const updated = services.getFinding(findingId);
    if (updated) setFinding(updated);
  };

  const allIds = [finding.vulnerabilityId, ...finding.aliases];

  return (
    <div className="space-y-5">
      <button
        onClick={() => navigate({ name: 'dashboard' })}
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to dashboard
      </button>

      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center gap-2">
          <TierBadge tier={finding.tier} />
          <StatusBadge status={finding.status} />
          <span className="font-mono text-sm text-slate-700">
            {finding.packageName}
          </span>
        </div>
        <h1 className="mt-3 text-lg font-semibold tracking-tight">
          {finding.vulnerabilityId}
        </h1>

        {/* Identifiers */}
        <section className="mt-5">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Identifiers
          </h2>
          <div className="mt-2 flex flex-wrap gap-2">
            <IdChip label={finding.vulnerabilityId} primary />
            {finding.aliases.length === 0 ? (
              <span className="text-sm text-slate-400">No aliases</span>
            ) : (
              finding.aliases.map((a) => <IdChip key={a} label={a} />)
            )}
          </div>
        </section>

        {/* Affected ranges */}
        <section className="mt-5">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Affected version ranges
          </h2>
          <ul className="mt-2 divide-y divide-slate-100 rounded-md border border-slate-200">
            {finding.affectedRanges.map((r) => (
              <li
                key={r.id}
                className="flex flex-wrap items-center justify-between gap-2 px-3 py-2"
              >
                <span className="font-mono text-sm text-slate-700">
                  {r.range}
                </span>
                {r.fixedVersion ? (
                  <span className="inline-flex items-center gap-1 text-sm text-emerald-700">
                    Fixed in{' '}
                    <span className="font-mono font-medium">
                      {r.fixedVersion}
                    </span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                    no fixed version
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>

        {/* AI brief / structured finding */}
        <section className="mt-5">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            AI brief
          </h2>
          {finding.brief ? (
            <p className="mt-2 text-sm leading-relaxed text-slate-700">
              {finding.brief}
            </p>
          ) : (
            <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 p-3">
              <div className="flex items-center gap-2 text-sm font-medium text-amber-800">
                <ShieldAlert className="h-4 w-4" />
                Brief unavailable
              </div>
              <p className="mt-1 text-sm text-slate-700">
                The AI brief was rejected for this finding. The structured
                finding is shown instead:
              </p>
              <p className="mt-2 text-sm leading-relaxed text-slate-700">
                {finding.structuredSummary}
              </p>
            </div>
          )}
        </section>

        {/* Risk context */}
        <section className="mt-5">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Risk context
          </h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <KevBadge kev={finding.kev} />
            <EpssText epss={finding.epss} />
          </div>
        </section>

        {/* Asset context */}
        <section className="mt-5">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Asset context
          </h2>
          {asset ? (
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
              <Field label="Asset" value={asset.name} />
              <Field
                label="Owner"
                value={
                  asset.owner
                    ? `${asset.owner} (${asset.ownerEmail ?? 'no email'})`
                    : 'Ownerless'
                }
              />
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Criticality</span>
                <CriticalityBadge criticality={asset.criticality} />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Internet-facing</span>
                <span className="text-sm text-slate-700">
                  {asset.internetFacing ? 'Yes' : 'No'}
                </span>
              </div>
              {asset.repositoryUrl && (
                <a
                  href={asset.repositoryUrl}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex items-center gap-1 text-sm text-slate-700 underline hover:text-slate-900"
                >
                  Repository
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          ) : (
            <p className="mt-2 text-sm text-slate-400">Asset not found.</p>
          )}
        </section>

        {/* Status detail */}
        <section className="mt-5">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Status
          </h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge status={finding.status} />
            {finding.status === 'fixed' && finding.fixedAt && (
              <span className="text-sm text-slate-600">
                Fixed at {formatTimestamp(finding.fixedAt)}
              </span>
            )}
            {finding.status === 'withdrawn' && finding.withdrawnNote && (
              <span className="text-sm text-slate-600">
                {finding.withdrawnNote}
              </span>
            )}
          </div>
        </section>

        {/* Risk acceptance action */}
        {finding.status === 'open' && (
          <section className="mt-5">
            <RiskAcceptanceForm
              findingId={finding.id}
              onAccepted={onAccepted}
            />
          </section>
        )}

        {/* Audit trail */}
        <section className="mt-6">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Audit trail
          </h2>
          <AuditTrail finding={finding} />
        </section>
      </div>
    </div>
  );
}

function AuditTrail({ finding }: { finding: Finding }) {
  if (finding.audit.length === 0) {
    return (
      <p className="mt-2 text-sm text-slate-400">No audit entries yet.</p>
    );
  }
  return (
    <ol className="mt-2 divide-y divide-slate-100 rounded-md border border-slate-200">
      {finding.audit.map((a) => (
        <li key={a.id} className="px-3 py-2">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium text-slate-800">{a.who}</span>
            <span className="text-slate-400">changed</span>
            <span className="font-mono text-xs text-slate-600">{a.field}</span>
            <span className="text-slate-400">from</span>
            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">
              {a.previousValue}
            </span>
            <span className="text-slate-400">to</span>
            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">
              {a.newValue}
            </span>
          </div>
          <div className="mt-0.5 text-xs text-slate-400">
            {formatTimestamp(a.when)}
          </div>
          {a.reason && (
            <div className="mt-1 text-sm text-slate-600">
              <span className="text-xs text-slate-400">Reason: </span>
              {a.reason}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}

function IdChip({ label, primary }: { label: string; primary?: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-xs ${
        primary
          ? 'border-slate-300 bg-slate-100 text-slate-800'
          : 'border-slate-200 bg-white text-slate-600'
      }`}
    >
      {label}
    </span>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-sm text-slate-700">{value}</div>
    </div>
  );
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
