import { describe, expect, it } from 'vitest';
import { mockServices } from '../services/mockServices';
import { mockFindings, mockAssets, rankFindings } from '../services/mockData';
import { TIER_ORDER } from '../types';

const assetsById = new Map(mockAssets.map((a) => [a.id, a]));

describe('mock services layer', () => {
  it('returns the mock findings pre-ranked by tier', () => {
    const findings = mockServices.listFindings();
    expect(findings.length).toBeGreaterThan(0);

    // Every finding from the mock data is present.
    expect(findings.length).toBe(mockFindings.length);

    // The tier order matches P1 -> P4.
    const tiers = findings.map((f) => f.tier);
    for (let i = 0; i < tiers.length - 1; i++) {
      const a = TIER_ORDER.indexOf(tiers[i]);
      const b = TIER_ORDER.indexOf(tiers[i + 1]);
      expect(a).toBeLessThanOrEqual(b);
    }

    // Each finding shows its tier in the data the dashboard renders from.
    for (const f of findings) {
      expect(TIER_ORDER).toContain(f.tier);
    }
  });

  it('returns findings in the rankFindings order (dashboard does not re-sort)', () => {
    const ranked = rankFindings(mockFindings, assetsById);
    const fromServices = mockServices.listFindings();
    expect(fromServices.map((f) => f.id)).toEqual(ranked.map((f) => f.id));
  });

  it('signs in with the demo credentials and rejects wrong ones', () => {
    const ok = mockServices.signIn({
      email: 'dana.reyes@example.com',
      password: 'triage-demo',
    });
    expect(ok.ok).toBe(true);
    expect(ok.user?.name).toBe('Dana Reyes');

    const bad = mockServices.signIn({
      email: 'dana.reyes@example.com',
      password: 'wrong',
    });
    expect(bad.ok).toBe(false);
    expect(bad.error).toBeTruthy();
  });

  it('accepting risk records an audit entry that includes the reason', () => {
    mockServices.signIn({
      email: 'dana.reyes@example.com',
      password: 'triage-demo',
    });

    const findings = mockServices.listFindings();
    const open = findings.find((f) => f.status === 'open')!;

    const res = mockServices.acceptRisk({
      findingId: open.id,
      reason: 'Compensating control in place; fix scheduled for Q3.',
    });
    expect(res.ok).toBe(true);
    expect(res.finding?.status).toBe('risk accepted');

    const last = res.finding!.audit[res.finding!.audit.length - 1];
    expect(last.who).toBe('Dana Reyes');
    expect(last.field).toBe('status');
    expect(last.previousValue).toBe('open');
    expect(last.newValue).toBe('risk accepted');
    expect(last.reason).toBe(
      'Compensating control in place; fix scheduled for Q3.',
    );

    // The store reflects the change.
    const after = mockServices.getFinding(open.id);
    expect(after?.status).toBe('risk accepted');
  });
});
