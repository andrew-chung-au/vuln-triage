import { useMemo } from 'react';
import { services } from '../services';
import { useApp } from '../app/AppContext';
import { CriticalityBadge } from '../components/Badges';
import { PlusCircle, AlertTriangle, UserX, Clock, CircleAlert } from 'lucide-react';
import type { Asset } from '../types';

export function AssetListScreen() {
  const { navigate } = useApp();
  const assets = useMemo(() => services.listAssets(), []);

  // Findings counts per asset, using the services-layer order.
  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const f of services.listFindings()) {
      map.set(f.assetId, (map.get(f.assetId) ?? 0) + 1);
    }
    return map;
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Assets</h1>
          <p className="text-sm text-slate-500">
            Assets under triage, with their owner and scan state.
          </p>
        </div>
        <button
          onClick={() => navigate({ name: 'register-asset' })}
          className="inline-flex items-center gap-1 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800"
        >
          <PlusCircle className="h-4 w-4" />
          Register asset
        </button>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2 font-medium">Name</th>
              <th className="px-3 py-2 font-medium">Owner</th>
              <th className="px-3 py-2 font-medium">Criticality</th>
              <th className="px-3 py-2 font-medium">Internet-facing</th>
              <th className="px-3 py-2 font-medium">Findings</th>
              <th className="px-3 py-2 font-medium">Scan state</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {assets.map((a) => (
              <AssetRow key={a.id} asset={a} findingsCount={counts.get(a.id) ?? 0} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AssetRow({
  asset,
  findingsCount,
}: {
  asset: Asset;
  findingsCount: number;
}) {
  return (
    <tr className="hover:bg-slate-50">
      <td className="px-3 py-3 align-top">
        <div className="font-medium text-slate-800">{asset.name}</div>
        {asset.repositoryUrl && (
          <a
            href={asset.repositoryUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="text-xs text-slate-400 underline"
          >
            {asset.repositoryUrl}
          </a>
        )}
      </td>
      <td className="px-3 py-3 align-top">
        {asset.owner ? (
          <div>
            <div className="text-slate-800">{asset.owner}</div>
            {asset.ownerEmail && (
              <div className="text-xs text-slate-400">{asset.ownerEmail}</div>
            )}
          </div>
        ) : (
          <span className="inline-flex items-center gap-1 rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
            <UserX className="h-3 w-3" />
            ownerless
          </span>
        )}
      </td>
      <td className="px-3 py-3 align-top">
        <CriticalityBadge criticality={asset.criticality} />
      </td>
      <td className="px-3 py-3 align-top">
        {asset.internetFacing ? (
          <span className="text-sky-700">Yes</span>
        ) : (
          <span className="text-slate-500">No</span>
        )}
      </td>
      <td className="px-3 py-3 align-top text-slate-700">
        {asset.scanState === 'not yet scanned' ? (
          <span className="text-slate-400">—</span>
        ) : (
          findingsCount
        )}
      </td>
      <td className="px-3 py-3 align-top">
        <ScanStateBadge state={asset.scanState} />
      </td>
    </tr>
  );
}

function ScanStateBadge({ state }: { state: Asset['scanState'] }) {
  switch (state) {
    case 'ok':
      return (
        <span className="inline-flex items-center gap-1 rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
          scanned
        </span>
      );
    case 'scan error':
      return (
        <span className="inline-flex items-center gap-1 rounded border border-red-200 bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
          <AlertTriangle className="h-3 w-3" />
          scan error
        </span>
      );
    case 'not yet scanned':
      return (
        <span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600">
          <Clock className="h-3 w-3" />
          not yet scanned
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 text-xs text-slate-500">
          <CircleAlert className="h-3 w-3" />
          {state}
        </span>
      );
  }
}
