import { describe, expect, it } from 'vitest';
import { mockServices } from '../services/mockServices';

describe('risk acceptance reason validation', () => {
  function findOpen() {
    return mockServices
      .listFindings()
      .find((f) => f.status === 'open')!;
  }

  it('rejects an empty reason and leaves the status unchanged', () => {
    mockServices.signIn({
      email: 'dana.reyes@example.com',
      password: 'triage-demo',
    });
    const before = findOpen();
    const beforeStatus = before.status;

    const res = mockServices.acceptRisk({ findingId: before.id, reason: '' });
    expect(res.ok).toBe(false);
    expect(res.error).toBeTruthy();

    const after = mockServices.getFinding(before.id);
    expect(after?.status).toBe(beforeStatus);
    expect(after?.status).toBe('open');
  });

  it('rejects a whitespace-only reason and leaves the status unchanged', () => {
    mockServices.signIn({
      email: 'dana.reyes@example.com',
      password: 'triage-demo',
    });
    const before = findOpen();
    const beforeStatus = before.status;
    const beforeAuditLen = before.audit.length;

    const res = mockServices.acceptRisk({
      findingId: before.id,
      reason: '   \t  \n  ',
    });
    expect(res.ok).toBe(false);
    expect(res.error).toBeTruthy();

    const after = mockServices.getFinding(before.id);
    expect(after?.status).toBe(beforeStatus);
    expect(after?.audit.length).toBe(beforeAuditLen);
  });
});
