import { useState } from 'react';
import { services } from '../services';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

export function RiskAcceptanceForm({
  findingId,
  onAccepted,
}: {
  findingId: string;
  onAccepted: () => void;
}) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Client mirrors the services-layer guard: whitespace-only is rejected.
    if (reason.trim() === '') {
      setError('A reason is required to accept risk.');
      return;
    }
    setSubmitting(true);
    const res = services.acceptRisk({ findingId, reason });
    setSubmitting(false);
    if (!res.ok) {
      setError(res.error ?? 'Could not accept risk.');
      return;
    }
    setError(null);
    setReason('');
    onAccepted();
  };

  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <div className="mb-2 flex items-center gap-2">
        <CheckCircle2 className="h-4 w-4 text-slate-700" />
        <h3 className="text-sm font-semibold text-slate-800">
          Accept risk for this finding
        </h3>
      </div>
      <p className="mb-3 text-xs text-slate-500">
        Only this human action sets the status to “risk accepted”. A reason is
        required and will be recorded in the audit trail.
      </p>
      <form onSubmit={onSubmit} className="space-y-3">
        <label htmlFor="risk-reason" className="block text-sm font-medium text-slate-700">
          Reason
        </label>
        <textarea
          id="risk-reason"
          value={reason}
          onChange={(e) => {
            setReason(e.target.value);
            setError(null);
          }}
          rows={3}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          placeholder="Explain why this risk is accepted…"
        />
        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-700"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-800 disabled:opacity-50"
        >
          Accept risk
        </button>
      </form>
    </div>
  );
}
