import type { Asset, Brief, Finding, User } from "./types";

export const DEMO_CREDENTIALS = { username: "analyst@example.com", password: "triage-demo" };

/** A security lead: may accept risk on any finding. */
export const DEMO_USER: User = {
  id: "u1",
  username: "analyst@example.com",
  displayName: "Jordan Vale",
  email: "analyst@example.com",
  role: "security lead",
};

/** An asset owner whose email matches the payments-api asset (a1). Not shown on the login screen. */
export const DEMO_OWNER_CREDENTIALS = { username: "payments-team@example.com", password: "triage-demo" };

export const DEMO_OWNER_USER: User = {
  id: "u2",
  username: "payments-team@example.com",
  displayName: "Payments team",
  email: "payments-team@example.com",
  role: "asset owner",
};

const clean = (): Pick<Asset, "scanFailureReason" | "scanWarnings"> => ({ scanFailureReason: null, scanWarnings: [] });

export function seedAssets(): Asset[] {
  return [
    { id: "a1", name: "payments-api", ownerName: "Payments team", ownerEmail: "payments-team@example.com", criticality: "critical", internetFacing: true, repositoryUrl: "https://github.com/acme/payments-api", scanStatus: "scanned, findings", ...clean(), lastScanAt: "2026-10-20T02:00:00Z", lastCommitSha: "3f9c2a1d7be84c0a9d5e6f7a8b9c0d1e2f3a4b5c" },
    { id: "a2", name: "customer-portal", ownerName: "Web team", ownerEmail: "web-team@example.org", criticality: "high", internetFacing: true, repositoryUrl: "https://github.com/acme/customer-portal", scanStatus: "scanned, findings", ...clean(), lastScanAt: "2026-10-20T02:10:00Z", lastCommitSha: "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678" },
    { id: "a3", name: "reporting-worker", ownerName: "Data engineering", ownerEmail: "data-eng@example.net", criticality: "medium", internetFacing: false, repositoryUrl: "https://github.com/acme/reporting-worker", scanStatus: "scanned, findings", ...clean(), lastScanAt: "2026-10-20T02:20:00Z", lastCommitSha: "0123456789abcdef0123456789abcdef01234567" },
    { id: "a4", name: "internal-wiki", ownerName: null, ownerEmail: null, criticality: "low", internetFacing: false, repositoryUrl: "https://github.com/acme/internal-wiki", scanStatus: "scanned, findings", ...clean(), lastScanAt: "2026-10-20T02:30:00Z", lastCommitSha: "89abcdef0123456789abcdef0123456789abcdef" },
    { id: "a5", name: "legacy-billing", ownerName: "Finance IT", ownerEmail: "finance-it@example.com", criticality: "high", internetFacing: false, repositoryUrl: "https://github.com/acme/legacy-billing", scanStatus: "scan failed", scanFailureReason: "lockfile parse error", scanWarnings: [], lastScanAt: "2026-10-20T02:40:00Z", lastCommitSha: null },
    { id: "a6", name: "mobile-bff", ownerName: "Mobile team", ownerEmail: "mobile-team@example.org", criticality: "medium", internetFacing: true, repositoryUrl: "https://github.com/acme/mobile-bff", scanStatus: "not yet scanned", ...clean(), lastScanAt: null, lastCommitSha: null },
    { id: "a7", name: "docs-site", ownerName: "Docs team", ownerEmail: "docs@example.net", criticality: "low", internetFacing: true, repositoryUrl: "https://github.com/acme/docs-site", scanStatus: "scanned, clean", ...clean(), lastScanAt: "2026-10-20T02:50:00Z", lastCommitSha: "fedcba9876543210fedcba9876543210fedcba98" },
    {
      id: "a8", name: "batch-scheduler", ownerName: "Platform team", ownerEmail: "platform@example.com", criticality: "medium", internetFacing: false,
      repositoryUrl: "https://github.com/acme/batch-scheduler", scanStatus: "scanned, incomplete", scanFailureReason: null,
      scanWarnings: [{ kind: "unparsed dependency entry", file: "requirements.txt", line: 14, message: "Line 14 could not be read as a pinned dependency." }],
      lastScanAt: "2026-10-20T03:00:00Z", lastCommitSha: "1122334455667788990011223344556677889900",
    },
  ];
}

const brief = (summary: string, impact: string, remediation: string, fixVersion: string | null, id: string): Brief => ({
  summary,
  impact,
  remediation,
  fixVersion,
  referenceLink: `https://osv.dev/vulnerability/${id}`,
});

// Intentionally stored out of order: the mock service ranks before returning.
export function seedFindings(): Finding[] {
  return [
    {
      id: "f8", vulnerabilityId: "GHSA-9c4r-colr-p4n2", aliases: ["CVE-2026-40112"], cveId: "CVE-2026-40112", tier: "P4", assetId: "a4",
      package: "colorfmt", ecosystem: "npm",
      dependencies: [{ version: null, sourceFile: "package-lock.json", direct: false }],
      fixedVersion: "1.4.2",
      affectedRanges: [{ range: "< 1.4.2", fixedVersion: "1.4.2" }],
      kev: "KEV: not listed", kevStale: false, epss: null, epssStale: false, status: "open", firstDetectedAt: "2026-09-02T08:00:00Z", fixedAt: null,
      stale: false, staleSince: null, signalsChanged: false, statusBeforeWithdrawal: null,
      rankReason: "P4: no KEV listing and no EPSS score; ranked last in its tier.",
      briefStatus: "pending", brief: null, auditTrail: [],
    },
    {
      id: "f2", vulnerabilityId: "CVE-2026-31877", aliases: [], cveId: "CVE-2026-31877", tier: "P1", assetId: "a2",
      package: "tokenwise", ecosystem: "npm",
      dependencies: [{ version: "0.9.7", sourceFile: "package-lock.json", direct: true }],
      fixedVersion: null,
      affectedRanges: [{ range: ">= 0.1.0", fixedVersion: null }],
      kev: "KEV: listed", kevStale: false, epss: null, epssStale: false, status: "open", firstDetectedAt: "2026-10-10T11:20:00Z", fixedAt: null,
      stale: false, staleSince: null, signalsChanged: true, statusBeforeWithdrawal: null,
      rankReason: "P1: listed in KEV on an internet-facing asset; EPSS n/a, so ranked after scored P1 findings.",
      briefStatus: "available",
      brief: brief("JWT signature check can be bypassed with the 'none' algorithm.", "Attackers can forge session tokens for any portal user. Listed in KEV.", "No fixed version yet. Pin algorithms explicitly in verifier config or replace the library.", null, "CVE-2026-31877"),
      auditTrail: [],
    },
    {
      id: "f4", vulnerabilityId: "GHSA-c5vk-lite-88qd", aliases: ["CVE-2026-28810"], cveId: "CVE-2026-28810", tier: "P2", assetId: "a3",
      package: "csvkit-lite", ecosystem: "PyPI",
      dependencies: [{ version: "2.0.1", sourceFile: "requirements.txt", direct: true }],
      fixedVersion: "2.0.5",
      affectedRanges: [{ range: "< 2.0.5", fixedVersion: "2.0.5" }],
      kev: "KEV: not listed", kevStale: true, epss: 0.41, epssStale: false, status: "risk accepted", firstDetectedAt: "2026-08-14T09:00:00Z", fixedAt: null,
      stale: false, staleSince: null, signalsChanged: false, statusBeforeWithdrawal: null,
      rankReason: "P2: EPSS 0.41 on an internal asset with medium criticality.",
      briefStatus: "available",
      brief: brief("Formula injection when exporting CSV.", "Exported reports may execute formulas when opened in spreadsheet tools.", "Upgrade to 2.0.5 or sanitise leading = + - @ characters.", "2.0.5", "GHSA-c5vk-lite-88qd"),
      auditTrail: [
        { id: "aud-f4-1", actor: "u1", actorDisplayName: "Jordan Vale", createdAt: "2026-09-01T14:32:00Z", field: "status", previousValue: "open", newValue: "risk accepted", reason: "Exports are only consumed by an internal pipeline that never opens them in spreadsheet software. Revisit Q1.", source: "dashboard", restoresEntryId: null },
      ],
    },
    {
      id: "f1", vulnerabilityId: "GHSA-7x2q-ym4h-r9vf", aliases: ["CVE-2026-30451"], cveId: "CVE-2026-30451", tier: "P1", assetId: "a1",
      package: "yamlish", ecosystem: "PyPI",
      dependencies: [{ version: "3.2.1", sourceFile: "poetry.lock", direct: true }],
      fixedVersion: "3.2.4",
      affectedRanges: [{ range: ">= 3.0.0, < 3.2.4", fixedVersion: "3.2.4" }],
      kev: "KEV: listed", kevStale: false, epss: 0.94, epssStale: false, status: "open", firstDetectedAt: "2026-10-03T07:45:00Z", fixedAt: null,
      stale: false, staleSince: null, signalsChanged: false, statusBeforeWithdrawal: null,
      rankReason: "P1: listed in KEV on an internet-facing critical asset; EPSS 0.94.",
      briefStatus: "available",
      brief: brief("Unsafe deserialisation allows remote code execution.", "Untrusted YAML in webhook payloads can execute code on the payments API. Actively exploited (KEV).", "Upgrade yamlish to 3.2.4 and switch to safe_load.", "3.2.4", "GHSA-7x2q-ym4h-r9vf"),
      auditTrail: [],
    },
    {
      id: "f6", vulnerabilityId: "GHSA-mdt1-3hq7-wx5c", aliases: ["CVE-2026-22094"], cveId: "CVE-2026-22094", tier: "P3", assetId: "a4",
      package: "markdown-tidy", ecosystem: "npm",
      dependencies: [{ version: "5.1.0", sourceFile: "package-lock.json", direct: true }],
      fixedVersion: "5.1.3",
      affectedRanges: [{ range: "< 5.1.3", fixedVersion: "5.1.3" }],
      kev: "KEV: not listed", kevStale: false, epss: 0.08, epssStale: false, status: "fixed", firstDetectedAt: "2026-07-21T10:00:00Z", fixedAt: "2026-08-05T16:12:00Z",
      stale: false, staleSince: null, signalsChanged: false, statusBeforeWithdrawal: null,
      rankReason: "P3: EPSS 0.08 on a low-criticality internal asset.",
      briefStatus: "available",
      brief: brief("Stored XSS via link titles.", "Wiki editors could inject scripts into pages.", "Upgrade to 5.1.3.", "5.1.3", "GHSA-mdt1-3hq7-wx5c"),
      auditTrail: [
        { id: "aud-f6-1", actor: "re-scan", actorDisplayName: null, createdAt: "2026-08-05T16:12:00Z", field: "status", previousValue: "open", newValue: "fixed", reason: null, source: "OSV", restoresEntryId: null },
      ],
    },
    {
      id: "f3", vulnerabilityId: "GHSA-hr3l-pp9k-2zt6", aliases: ["CVE-2026-29933", "OSV-2026-1187"], cveId: "CVE-2026-29933", tier: "P2", assetId: "a1",
      package: "http-relay", ecosystem: "npm",
      dependencies: [{ version: "2.0.4", sourceFile: "package-lock.json", direct: true }],
      fixedVersion: null,
      affectedRanges: [
        { range: ">= 1.0.0, < 1.8.3", fixedVersion: "1.8.3" },
        { range: ">= 2.0.0, < 2.1.0", fixedVersion: null },
      ],
      kev: "KEV: not listed", kevStale: false, epss: 0.61, epssStale: true, status: "open", firstDetectedAt: "2026-09-18T13:00:00Z", fixedAt: null,
      stale: true, staleSince: "2026-10-19T03:00:00Z", signalsChanged: false, statusBeforeWithdrawal: null,
      rankReason: "P2: EPSS 0.61 (last refresh failed, value is stale) on an internet-facing critical asset.",
      briefStatus: "available",
      brief: brief("Request smuggling through ambiguous Transfer-Encoding headers.", "Requests could bypass upstream auth checks on the payments edge.", "1.x: upgrade to 1.8.3. 2.x: no fixed version yet; downgrade to 1.8.3 or reject duplicate TE headers at the load balancer.", null, "GHSA-hr3l-pp9k-2zt6"),
      auditTrail: [],
    },
    {
      id: "f7", vulnerabilityId: "GHSA-lgrt-55v2-k0jm", aliases: [], cveId: null, tier: "P4", assetId: "a3",
      package: "log-rotate-js", ecosystem: "npm",
      dependencies: [{ version: "0.3.2", sourceFile: "package-lock.json", direct: false }],
      fixedVersion: "0.3.5",
      affectedRanges: [{ range: "< 0.3.5", fixedVersion: "0.3.5" }],
      kev: "KEV: n/a (no CVE)", kevStale: false, epss: 0.02, epssStale: false, status: "withdrawn", firstDetectedAt: "2026-06-30T12:00:00Z", fixedAt: null,
      stale: false, staleSince: null, signalsChanged: false, statusBeforeWithdrawal: "open",
      rankReason: "P4: no CVE, so no KEV value; EPSS 0.02.",
      briefStatus: "available",
      brief: brief("Symlink following during log rotation.", "Local users could overwrite files writable by the worker.", "Upgrade to 0.3.5.", "0.3.5", "GHSA-lgrt-55v2-k0jm"),
      auditTrail: [
        { id: "aud-f7-1", actor: "system", actorDisplayName: null, createdAt: "2026-07-15T03:00:00Z", field: "status", previousValue: "open", newValue: "withdrawn", reason: null, source: "OSV", restoresEntryId: null },
      ],
    },
    {
      id: "f5", vulnerabilityId: "GHSA-imgr-4w8p-zz31", aliases: ["CVE-2026-27765"], cveId: "CVE-2026-27765", tier: "P3", assetId: "a2",
      package: "imgresize", ecosystem: "PyPI",
      dependencies: [{ version: "4.7.0", sourceFile: "requirements.txt", direct: true }],
      fixedVersion: "4.7.2",
      affectedRanges: [{ range: ">= 4.0.0, < 4.7.2", fixedVersion: "4.7.2" }],
      kev: "KEV: not listed", kevStale: false, epss: 0.12, epssStale: false, status: "open", firstDetectedAt: "2026-09-25T15:30:00Z", fixedAt: null,
      stale: false, staleSince: null, signalsChanged: false, statusBeforeWithdrawal: null,
      rankReason: "P3: EPSS 0.12 on an internet-facing high-criticality asset.",
      briefStatus: "unavailable", brief: null,
      auditTrail: [],
    },
  ];
}
