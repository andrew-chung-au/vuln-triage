import { describe, expect, it } from 'vitest';
import { mockServices } from '../services/mockServices';

describe('affected range display data', () => {
  it('each affected range carries a fixedVersion or null (no fixed version)', () => {
    const findings = mockServices.listFindings();
    for (const f of findings) {
      for (const r of f.affectedRanges) {
        // fixedVersion is either a non-empty string or null.
        if (r.fixedVersion === null) {
          expect(r.fixedVersion).toBeNull();
        } else {
          expect(typeof r.fixedVersion).toBe('string');
          expect(r.fixedVersion.length).toBeGreaterThan(0);
        }
      }
    }
  });

  it('includes a finding whose only affected range has no fixed version', () => {
    const findings = mockServices.listFindings();
    const onlyNoFix = findings.find(
      (f) =>
        f.affectedRanges.length === 1 &&
        f.affectedRanges.every((r) => r.fixedVersion === null),
    );
    expect(onlyNoFix).toBeDefined();
  });

  it('includes a finding with two or more ranges where at least one has no fixed version', () => {
    const findings = mockServices.listFindings();
    const multi = findings.find(
      (f) =>
        f.affectedRanges.length >= 2 &&
        f.affectedRanges.some((r) => r.fixedVersion === null) &&
        f.affectedRanges.some((r) => r.fixedVersion !== null),
    );
    expect(multi).toBeDefined();
  });
});
