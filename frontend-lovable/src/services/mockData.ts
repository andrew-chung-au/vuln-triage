import type { Asset, Finding, User } from "./types";

export const DEMO_CREDENTIALS = { username: "analyst@example.com", password: "triage-demo" };

export const DEMO_USER: User = { id: "u1", name: "Jordan Vale", email: "analyst@example.com" };

export function seedAssets(): Asset[] {
  return [
    { id: "a1", name: "payments-api", owner: "payments-team@example.com", criticality: "critical", internetFacing: true, repositoryUrl: "https://git.example.com/acme/payments-api", scanStatus: "scanned" },
    { id: "a2", name: "customer-portal", owner: "web-team@example.org", criticality: "high", internetFacing: true, repositoryUrl: "https://git.example.com/acme/customer-portal", scanStatus: "scanned" },
    { id: "a3", name: "reporting-worker", owner: "data-eng@example.net", criticality: "medium", internetFacing: false, repositoryUrl: "https://git.example.com/acme/reporting-worker", scanStatus: "scanned" },
    { id: "a4", name: "internal-wiki", owner: null, criticality: "low", internetFacing: false, repositoryUrl: "https://git.example.com/acme/internal-wiki", scanStatus: "scanned" },
    { id: "a5", name: "legacy-billing", owner: "finance-it@example.com", criticality: "high", internetFacing: false, repositoryUrl: "https://git.example.com/acme/legacy-billing", scanStatus: "scan_error" },
    { id: "a6", name: "mobile-bff", owner: "mobile-team@example.org", criticality: "medium", internetFacing: true, repositoryUrl: "https://git.example.com/acme/mobile-bff", scanStatus: "not_scanned" },
    { id: "a7", name: "docs-site", owner: "docs@example.net", criticality: "low", internetFacing: true, repositoryUrl: "https://git.example.com/acme/docs-site", scanStatus: "scanned" },
  ];
}

const brief = (summary: string, impact: string, remediation: string, ghsa: string) => ({
  summary,
  impact,
  remediation,
  advisoryReference: `https://github.com/advisories/${ghsa}`,
});

// Intentionally stored out of order: the mock service ranks before returning.
export function seedFindings(): Finding[] {
  return [
    {
      id: "f8", vulnerabilityId: "GHSA-9c4r-colr-p4n2", aliases: ["CVE-2026-40112"], tier: "P4", assetId: "a4",
      packageName: "colorfmt", installedVersion: "1.4.0",
      affectedRanges: [{ range: "< 1.4.2", fixedVersion: "1.4.2" }],
      kev: false, epss: null, status: "open", firstSeen: "2026-09-02T08:00:00Z", fixedAt: null,
      briefStatus: "available",
      brief: brief("ReDoS in colour string parsing.", "Crafted colour strings can stall rendering of internal pages.", "Upgrade colorfmt to 1.4.2.", "GHSA-9c4r-colr-p4n2"),
      structuredSummary: "Regular-expression denial of service in colour parser.", auditTrail: [],
    },
    {
      id: "f2", vulnerabilityId: "CVE-2026-31877", aliases: [], tier: "P1", assetId: "a2",
      packageName: "tokenwise", installedVersion: "0.9.7",
      affectedRanges: [{ range: ">= 0.1.0", fixedVersion: null }],
      kev: true, epss: null, status: "open", firstSeen: "2026-10-10T11:20:00Z", fixedAt: null,
      briefStatus: "available",
      brief: brief("JWT signature check can be bypassed with the 'none' algorithm.", "Attackers can forge session tokens for any portal user. Listed in KEV.", "No fixed version yet. Pin algorithms explicitly in verifier config or replace the library.", "GHSA-tkwz-2m8v-q71p"),
      structuredSummary: "Authentication bypass via unsigned tokens.", auditTrail: [],
    },
    {
      id: "f4", vulnerabilityId: "GHSA-c5vk-lite-88qd", aliases: ["CVE-2026-28810"], tier: "P2", assetId: "a3",
      packageName: "csvkit-lite", installedVersion: "2.0.1",
      affectedRanges: [{ range: "< 2.0.5", fixedVersion: "2.0.5" }],
      kev: false, epss: 0.41, status: "risk_accepted", firstSeen: "2026-08-14T09:00:00Z", fixedAt: null,
      briefStatus: "available",
      brief: brief("Formula injection when exporting CSV.", "Exported reports may execute formulas when opened in spreadsheet tools.", "Upgrade to 2.0.5 or sanitise leading = + - @ characters.", "GHSA-c5vk-lite-88qd"),
      structuredSummary: "CSV formula injection in export path.",
      auditTrail: [
        { who: "Jordan Vale", when: "2026-09-01T14:32:00Z", field: "status", previousValue: "open", newValue: "risk accepted", reason: "Exports are only consumed by an internal pipeline that never opens them in spreadsheet software. Revisit Q1." },
      ],
    },
    {
      id: "f1", vulnerabilityId: "GHSA-7x2q-ym4h-r9vf", aliases: ["CVE-2026-30451"], tier: "P1", assetId: "a1",
      packageName: "yamlish", installedVersion: "3.2.1",
      affectedRanges: [{ range: ">= 3.0.0, < 3.2.4", fixedVersion: "3.2.4" }],
      kev: true, epss: 0.94, status: "open", firstSeen: "2026-10-03T07:45:00Z", fixedAt: null,
      briefStatus: "available",
      brief: brief("Unsafe deserialisation allows remote code execution.", "Untrusted YAML in webhook payloads can execute code on the payments API. Actively exploited (KEV).", "Upgrade yamlish to 3.2.4 and switch to safe_load.", "GHSA-7x2q-ym4h-r9vf"),
      structuredSummary: "Remote code execution via YAML tag constructors.", auditTrail: [],
    },
    {
      id: "f6", vulnerabilityId: "GHSA-mdt1-3hq7-wx5c", aliases: ["CVE-2026-22094"], tier: "P3", assetId: "a4",
      packageName: "markdown-tidy", installedVersion: "5.1.0",
      affectedRanges: [{ range: "< 5.1.3", fixedVersion: "5.1.3" }],
      kev: false, epss: 0.08, status: "fixed", firstSeen: "2026-07-21T10:00:00Z", fixedAt: "2026-08-05T16:12:00Z",
      briefStatus: "available",
      brief: brief("Stored XSS via link titles.", "Wiki editors could inject scripts into pages.", "Upgrade to 5.1.3.", "GHSA-mdt1-3hq7-wx5c"),
      structuredSummary: "Cross-site scripting in rendered link titles.",
      auditTrail: [
        { who: "scanner (lockfile rescan)", when: "2026-08-05T16:12:00Z", field: "status", previousValue: "open", newValue: "fixed" },
      ],
    },
    {
      id: "f3", vulnerabilityId: "GHSA-hr3l-pp9k-2zt6", aliases: ["CVE-2026-29933", "OSV-2026-1187"], tier: "P2", assetId: "a1",
      packageName: "http-relay", installedVersion: "2.0.4",
      affectedRanges: [
        { range: ">= 1.0.0, < 1.8.3", fixedVersion: "1.8.3" },
        { range: ">= 2.0.0, < 2.1.0", fixedVersion: null },
      ],
      kev: false, epss: 0.61, status: "open", firstSeen: "2026-09-18T13:00:00Z", fixedAt: null,
      briefStatus: "available",
      brief: brief("Request smuggling through ambiguous Transfer-Encoding headers.", "Requests could bypass upstream auth checks on the payments edge.", "1.x: upgrade to 1.8.3. 2.x: no fixed version yet; downgrade to 1.8.3 or reject duplicate TE headers at the load balancer.", "GHSA-hr3l-pp9k-2zt6"),
      structuredSummary: "HTTP request smuggling.", auditTrail: [],
    },
    {
      id: "f7", vulnerabilityId: "GHSA-lgrt-55v2-k0jm", aliases: [], tier: "P4", assetId: "a3",
      packageName: "log-rotate-js", installedVersion: "0.3.2",
      affectedRanges: [{ range: "< 0.3.5", fixedVersion: "0.3.5" }],
      kev: false, epss: 0.02, status: "withdrawn", firstSeen: "2026-06-30T12:00:00Z", fixedAt: null,
      briefStatus: "available",
      brief: brief("Symlink following during log rotation.", "Local users could overwrite files writable by the worker.", "Upgrade to 0.3.5.", "GHSA-lgrt-55v2-k0jm"),
      structuredSummary: "Insecure symlink handling.",
      auditTrail: [
        { who: "feed sync (GitHub Advisory)", when: "2026-07-15T03:00:00Z", field: "status", previousValue: "open", newValue: "withdrawn" },
      ],
    },
    {
      id: "f5", vulnerabilityId: "GHSA-imgr-4w8p-zz31", aliases: ["CVE-2026-27765"], tier: "P3", assetId: "a2",
      packageName: "imgresize", installedVersion: "4.7.0",
      affectedRanges: [{ range: ">= 4.0.0, < 4.7.2", fixedVersion: "4.7.2" }],
      kev: false, epss: 0.12, status: "open", firstSeen: "2026-09-25T15:30:00Z", fixedAt: null,
      briefStatus: "rejected", brief: null,
      structuredSummary: "Heap out-of-bounds read when decoding malformed TIFF images. Fixed in 4.7.2.",
      auditTrail: [],
    },
  ];
}
