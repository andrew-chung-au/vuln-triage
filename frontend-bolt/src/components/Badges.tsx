import type {
  Criticality,
  FindingStatus,
  Tier,
} from '../types';

const TIER_STYLES: Record<Tier, string> = {
  P1: 'bg-red-100 text-red-800 border-red-200',
  P2: 'bg-orange-100 text-orange-800 border-orange-200',
  P3: 'bg-amber-100 text-amber-800 border-amber-200',
  P4: 'bg-slate-100 text-slate-700 border-slate-200',
};

const STATUS_STYLES: Record<FindingStatus, string> = {
  open: 'bg-blue-50 text-blue-700 border-blue-200',
  'risk accepted': 'bg-purple-50 text-purple-700 border-purple-200',
  fixed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  withdrawn: 'bg-gray-100 text-gray-500 border-gray-200 line-through',
};

const CRITICALITY_STYLES: Record<Criticality, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-amber-100 text-amber-800 border-amber-200',
  low: 'bg-slate-100 text-slate-700 border-slate-200',
};

export function TierBadge({ tier }: { tier: Tier }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-semibold ${TIER_STYLES[tier]}`}
    >
      {tier}
    </span>
  );
}

export function StatusBadge({ status }: { status: FindingStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}

export function CriticalityBadge({
  criticality,
}: {
  criticality: Criticality;
}) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium capitalize ${CRITICALITY_STYLES[criticality]}`}
    >
      {criticality}
    </span>
  );
}

export function KevBadge({ kev }: { kev: boolean }) {
  if (!kev) {
    return (
      <span className="inline-flex items-center rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600">
        KEV: no
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded border border-red-200 bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700">
      KEV: yes
    </span>
  );
}

export function EpssText({ epss }: { epss: number | null }) {
  if (epss == null) {
    return <span className="text-sm text-slate-500">EPSS: n/a</span>;
  }
  // Show as a percentage with two decimals.
  const pct = (epss * 100).toFixed(2);
  return <span className="text-sm tabular-nums text-slate-700">EPSS: {pct}%</span>;
}
