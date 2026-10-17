import { useMemo, useState } from 'react';
import { services } from '../services';
import { FINDING_STATUS_VALUES } from '../services/types';
import { useApp } from '../app/AppContext';
import type { FindingStatus } from '../types';
import {
  TierBadge,
  StatusBadge,
  KevBadge,
  EpssText,
  CriticalityBadge,
} from '../components/Badges';
import { Search, Inbox } from 'lucide-react';

type GroupMode = 'none' | 'asset';
const ALL_STATUSES = 'all';

export function DashboardScreen() {
  const { navigate } = useApp();
  const [statusFilter, setStatusFilter] = useState<FindingStatus | typeof ALL_STATUSES>(
    ALL_STATUSES,
  );
  const [assetFilter, setAssetFilter] = useState<string>('all');
  const [groupMode, setGroupMode] = useState<GroupMode>('none');

  const findings = useMemo(() => services.listFindings(), []);
  const assets = useMemo(() => services.listAssets(), []);
  const assetsById = useMemo(
    () => new Map(assets.map((a) => [a.id, a])),
    [assets],
  );

  // Filtering is applied on top of the services-layer order; we never re-sort.
  const filtered = useMemo(() => {
    return findings.filter((f) => {
      if (statusFilter !== ALL_STATUSES && f.status !== statusFilter) {
        return false;
      }
      if (assetFilter !== 'all' && f.assetId !== assetFilter) {
        return false;
      }
      return true;
    });
  }, [findings, statusFilter, assetFilter]);

  // Grouped view: group by asset, preserving the services-layer order within
  // each group.
  const groups = useMemo(() => {
    if (groupMode !== 'asset') return null;
    const map = new Map<string, typeof filtered>();
    for (const f of filtered) {
      const arr = map.get(f.assetId) ?? [];
      arr.push(f);
      map.set(f.assetId, arr);
    }
    return Array.from(map.entries());
  }, [groupMode, filtered]);

  const assetName = (id: string) =>
    assetsById.get(id)?.name ?? 'Unknown asset';

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Findings</h1>
          <p className="text-sm text-slate-500">
            Ranked by priority tier. The order is set by the services layer;
            the dashboard does not re-sort.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-500">Status</label>
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as FindingStatus | typeof ALL_STATUSES)
            }
            className="rounded-md border border-slate-300 px-2 py-1 text-sm focus:border-slate-500 focus:outline-none"
          >
            <option value={ALL_STATUSES}>All statuses</option>
            {FINDING_STATUS_VALUES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-500">Asset</label>
          <select
            value={assetFilter}
            onChange={(e) => setAssetFilter(e.target.value)}
            className="rounded-md border border-slate-300 px-2 py-1 text-sm focus:border-slate-500 focus:outline-none"
          >
            <option value="all">All assets</option>
            {assets.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-slate-500">Group by</label>
          <select
            value={groupMode}
            onChange={(e) => setGroupMode(e.target.value as GroupMode)}
            className="rounded-md border border-slate-300 px-2 py-1 text-sm focus:border-slate-500 focus:outline-none"
          >
            <option value="none">None</option>
            <option value="asset">Asset</option>
          </select>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState />
      ) : groups ? (
        <div className="space-y-6">
          {groups.map(([assetId, items]) => (
            <section key={assetId}>
              <h2 className="mb-2 text-sm font-semibold text-slate-700">
                {assetName(assetId)}
                <span className="ml-2 text-xs font-normal text-slate-400">
                  {items.length} finding{items.length === 1 ? '' : 's'}
                </span>
              </h2>
              <FindingsTable
                findings={items}
                assetsById={assetsById}
                onOpen={(id) => navigate({ name: 'finding', findingId: id })}
              />
            </section>
          ))}
        </div>
      ) : (
        <FindingsTable
          findings={filtered}
          assetsById={assetsById}
          onOpen={(id) => navigate({ name: 'finding', findingId: id })}
        />
      )}
    </div>
  );
}

function FindingsTable({
  findings,
  assetsById,
  onOpen,
}: {
  findings: ReturnType<typeof services.listFindings>;
  assetsById: Map<string, ReturnType<typeof services.getAsset>>;
  onOpen: (id: string) => void;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">Tier</th>
            <th className="px-3 py-2 font-medium">Asset</th>
            <th className="px-3 py-2 font-medium">Package</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium">Why it ranks here</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {findings.map((f) => {
            const asset = assetsById.get(f.assetId);
            return (
              <tr
                key={f.id}
                className="cursor-pointer hover:bg-slate-50"
                onClick={() => onOpen(f.id)}
              >
                <td className="px-3 py-3 align-top">
                  <TierBadge tier={f.tier} />
                </td>
                <td className="px-3 py-3 align-top">
                  <div className="font-medium text-slate-800">
                    {asset?.name ?? 'Unknown'}
                  </div>
                  {asset && (
                    <div className="mt-1 flex items-center gap-1">
                      <CriticalityBadge criticality={asset.criticality} />
                      {asset.internetFacing && (
                        <span className="inline-flex items-center rounded border border-sky-200 bg-sky-50 px-1.5 py-0.5 text-xs text-sky-700">
                          internet-facing
                        </span>
                      )}
                    </div>
                  )}
                </td>
                <td className="px-3 py-3 align-top">
                  <div className="font-mono text-xs text-slate-700">
                    {f.packageName}
                  </div>
                  <div className="mt-0.5 text-xs text-slate-400">
                    {f.vulnerabilityId}
                  </div>
                </td>
                <td className="px-3 py-3 align-top">
                  <StatusBadge status={f.status} />
                </td>
                <td className="px-3 py-3 align-top">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <KevBadge kev={f.kev} />
                    <EpssText epss={f.epss} />
                  </div>
                </td>
                <td className="px-3 py-3 align-top text-right">
                  <span className="text-xs font-medium text-slate-400">
                    Open →
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white py-16 text-center">
      <Inbox className="mb-3 h-8 w-8 text-slate-300" />
      <p className="text-sm font-medium text-slate-600">No findings to show</p>
      <p className="mt-1 text-sm text-slate-400">
        Adjust the filters above, or register a new asset to scan.
      </p>
    </div>
  );
}
