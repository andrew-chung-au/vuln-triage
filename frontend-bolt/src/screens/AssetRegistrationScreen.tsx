import { useState } from 'react';
import { services } from '../services';
import { useApp } from '../app/AppContext';
import { AlertCircle, ArrowLeft, CheckCircle2 } from 'lucide-react';
import type { Criticality } from '../types';

const CRITICALITIES: Criticality[] = ['low', 'medium', 'high', 'critical'];

export function AssetRegistrationScreen() {
  const { navigate } = useApp();
  const [name, setName] = useState('');
  const [owner, setOwner] = useState('');
  const [ownerEmail, setOwnerEmail] = useState('');
  const [criticality, setCriticality] = useState<Criticality>('medium');
  const [internetFacing, setInternetFacing] = useState(false);
  const [repositoryUrl, setRepositoryUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const trimmedName = name.trim();
    if (trimmedName === '') {
      setError('Asset name is required.');
      return;
    }

    const res = services.registerAsset({
      name: trimmedName,
      owner: owner.trim() ? owner.trim() : null,
      ownerEmail: ownerEmail.trim() ? ownerEmail.trim() : null,
      criticality,
      internetFacing,
      repositoryUrl: repositoryUrl.trim() ? repositoryUrl.trim() : null,
    });

    if (!res.ok) {
      setError(res.error ?? 'Could not register asset.');
      return;
    }

    setSuccess(`Registered “${res.asset!.name}”. It is not yet scanned.`);
    setName('');
    setOwner('');
    setOwnerEmail('');
    setCriticality('medium');
    setInternetFacing(false);
    setRepositoryUrl('');
  };

  return (
    <div className="max-w-xl space-y-4">
      <button
        onClick={() => navigate({ name: 'assets' })}
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to assets
      </button>

      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <h1 className="text-lg font-semibold tracking-tight">Register asset</h1>
        <p className="mt-1 text-sm text-slate-500">
          Add a new asset so it can be scanned for vulnerable dependencies.
        </p>

        <form onSubmit={onSubmit} className="mt-5 space-y-4">
          <div>
            <label
              htmlFor="asset-name"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              Name <span className="text-red-500">*</span>
            </label>
            <input
              id="asset-name"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setError(null);
              }}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
              placeholder="payments-api"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="asset-owner"
                className="mb-1 block text-sm font-medium text-slate-700"
              >
                Owner <span className="text-slate-400">(optional)</span>
              </label>
              <input
                id="asset-owner"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
                placeholder="Dana Reyes"
              />
            </div>
            <div>
              <label
                htmlFor="asset-owner-email"
                className="mb-1 block text-sm font-medium text-slate-700"
              >
                Owner email <span className="text-slate-400">(optional)</span>
              </label>
              <input
                id="asset-owner-email"
                type="email"
                value={ownerEmail}
                onChange={(e) => setOwnerEmail(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
                placeholder="owner@example.com"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="asset-criticality"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              Criticality
            </label>
            <select
              id="asset-criticality"
              value={criticality}
              onChange={(e) => setCriticality(e.target.value as Criticality)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
            >
              {CRITICALITIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <input
              id="asset-internet-facing"
              type="checkbox"
              checked={internetFacing}
              onChange={(e) => setInternetFacing(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-500"
            />
            <label
              htmlFor="asset-internet-facing"
              className="text-sm font-medium text-slate-700"
            >
              Internet-facing
            </label>
          </div>

          <div>
            <label
              htmlFor="asset-repo"
              className="mb-1 block text-sm font-medium text-slate-700"
            >
              Repository URL
            </label>
            <input
              id="asset-repo"
              value={repositoryUrl}
              onChange={(e) => setRepositoryUrl(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
              placeholder="https://repo.example.org/your-asset"
            />
          </div>

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div
              role="status"
              className="flex items-start gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700"
            >
              <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>{success}</span>
            </div>
          )}

          <button
            type="submit"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
          >
            Register asset
          </button>
        </form>
      </div>
    </div>
  );
}
