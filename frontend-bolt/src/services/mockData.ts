import type {
  Asset,
  AuditEntry,
  Finding,
  Tier,
  Criticality,
} from '../types';
import { TIER_ORDER, CRITICALITY_ORDER } from '../types';

// ---------------------------------------------------------------------------
// Ranking
//
// Findings are ranked by: tier (P1 first) -> EPSS (higher first, n/a after any
// score) -> asset criticality (higher first) -> oldest finding first.
// The services layer returns findings in this order; the dashboard does NOT
// re-sort.
// ---------------------------------------------------------------------------

function tierRank(tier: Tier): number {
  return TIER_ORDER.indexOf(tier);
}

function criticalityRank(c: Criticality): number {
  return CRITICALITY_ORDER.indexOf(c);
}

// EPSS: a real score (0..1) sorts before n/a. Higher score first.
function epssCompare(a: number | null, b: number | null): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1; // n/a after any score
  if (b == null) return -1;
  return b - a; // higher first
}

export function rankFindings(
  findings: Finding[],
  assetsById: Map<string, Asset>,
): Finding[] {
  return [...findings].sort((a, b) => {
    // Tier
    const t = tierRank(a.tier) - tierRank(b.tier);
    if (t !== 0) return t;

    // EPSS
    const e = epssCompare(a.epss, b.epss);
    if (e !== 0) return e;

    // Asset criticality (higher first)
    const ca = assetsById.get(a.assetId)?.criticality ?? 'low';
    const cb = assetsById.get(b.assetId)?.criticality ?? 'low';
    const c = criticalityRank(ca) - criticalityRank(cb);
    if (c !== 0) return c;

    // Oldest finding first (ascending createdAt)
    return a.createdAt.localeCompare(b.createdAt);
  });
}

// ---------------------------------------------------------------------------
// Mock assets
// ---------------------------------------------------------------------------

export const mockAssets: Asset[] = [
  {
    id: 'asset-payments-api',
    name: 'payments-api',
    owner: 'Dana Reyes',
    ownerEmail: 'dana.reyes@example.com',
    criticality: 'critical',
    internetFacing: true,
    repositoryUrl: 'https://repo.example.org/payments-api',
    scanState: 'ok',
  },
  {
    id: 'asset-checkout-web',
    name: 'checkout-web',
    owner: 'Priya Nair',
    ownerEmail: 'priya.nair@example.org',
    criticality: 'high',
    internetFacing: true,
    repositoryUrl: 'https://repo.example.org/checkout-web',
    scanState: 'ok',
  },
  {
    id: 'asset-inventory-svc',
    name: 'inventory-svc',
    owner: 'Marcus Lee',
    ownerEmail: 'marcus.lee@example.net',
    criticality: 'medium',
    internetFacing: false,
    repositoryUrl: 'https://repo.example.org/inventory-svc',
    scanState: 'ok',
  },
  {
    id: 'asset-reports-worker',
    name: 'reports-worker',
    owner: 'Sara Okafor',
    ownerEmail: 'sara.okafor@example.com',
    criticality: 'low',
    internetFacing: false,
    repositoryUrl: 'https://repo.example.org/reports-worker',
    scanState: 'ok',
  },
  {
    id: 'asset-batch-loader',
    name: 'batch-loader',
    owner: null,
    ownerEmail: null,
    criticality: 'medium',
    internetFacing: false,
    repositoryUrl: 'https://repo.example.org/batch-loader',
    scanState: 'ok',
  },
  {
    id: 'asset-legacy-billing',
    name: 'legacy-billing',
    owner: 'Tomás Vidal',
    ownerEmail: 'tomas.vidal@example.com',
    criticality: 'high',
    internetFacing: false,
    repositoryUrl: 'https://repo.example.org/legacy-billing',
    scanState: 'scan error',
  },
  {
    id: 'asset-edge-gateway',
    name: 'edge-gateway',
    owner: 'Wei Chen',
    ownerEmail: 'wei.chen@example.net',
    criticality: 'critical',
    internetFacing: true,
    repositoryUrl: 'https://repo.example.org/edge-gateway',
    scanState: 'not yet scanned',
  },
];

// ---------------------------------------------------------------------------
// Mock audit entries
// ---------------------------------------------------------------------------

function audit(
  id: string,
  who: string,
  when: string,
  field: string,
  previousValue: string,
  newValue: string,
  reason?: string,
): AuditEntry {
  return { id, who, when, field, previousValue, newValue, reason };
}

// ---------------------------------------------------------------------------
// Mock findings
//
// Coverage required by the spec:
//  - one finding in each tier P1, P2, P3, P4
//  - one finding whose only affected range has no fixed version
//  - one finding with two+ ranges, one of which has no fixed version
//  - one finding with at least two ids (GHSA + CVE alias), one with no aliases
//  - one finding with "brief unavailable"
//  - one "risk accepted" finding with its audit entry
//  - one "fixed" finding with a fixed timestamp
//  - one "withdrawn" finding with its audit entry
//  - one finding with "EPSS: n/a"
//  - one ownerless asset (asset-batch-loader), one scan error (legacy-billing),
//    one not yet scanned (edge-gateway)
// ---------------------------------------------------------------------------

export const mockFindings: Finding[] = [
  // P1 - KEV, high EPSS, critical asset. Two ids (CVE + GHSA).
  {
    id: 'finding-001',
    tier: 'P1',
    assetId: 'asset-payments-api',
    packageName: 'org.apache.logging.log4j:log4j-core',
    vulnerabilityId: 'CVE-2021-44228',
    aliases: ['GHSA-jfh8-c2jp-5v3q'],
    affectedRanges: [
      { id: 'r-001-a', range: '>=2.0-beta9 <2.3.0', fixedVersion: '2.3.0' },
      { id: 'r-001-b', range: '>=2.12.0 <2.12.3', fixedVersion: '2.12.3' },
    ],
    kev: true,
    epss: 0.9743,
    status: 'open',
    brief:
      'Remote code execution via JNDI lookup in the Log4j message lookup substitution. Exploited in the wild; listed in CISA KEV. Upgrade to a fixed version or remove the vulnerable lookup feature. Advisory: https://nvd.nist.gov/vuln/detail/CVE-2021-44228',
    structuredSummary:
      'JNDI injection in Log4j2 message lookup allows unauthenticated RCE when user input reaches a logged message.',
    createdAt: '2024-09-01T08:12:00Z',
    audit: [],
  },

  // P1 - KEV, high EPSS, internet-facing high asset. No aliases.
  {
    id: 'finding-002',
    tier: 'P1',
    assetId: 'asset-checkout-web',
    packageName: 'com.fasterxml.jackson.core:jackson-databind',
    vulnerabilityId: 'CVE-2022-42003',
    aliases: [],
    affectedRanges: [
      { id: 'r-002-a', range: '<2.13.4', fixedVersion: '2.13.4' },
      { id: 'r-002-b', range: '>=2.14.0-rc1 <2.14.0-rc2', fixedVersion: null },
    ],
    kev: true,
    epss: 0.9411,
    status: 'open',
    brief:
      'Jackson databind deserialization vulnerability allowing resource exhaustion via deeply nested objects. Patch available in 2.13.4; one pre-release range has no fixed version. Advisory: https://nvd.nist.gov/vuln/detail/CVE-2022-42003',
    structuredSummary:
      'Deserialization of nested UNWRAP_SINGLE_VALUE_ARRAYS can exhaust resources.',
    createdAt: '2024-09-03T10:30:00Z',
    audit: [],
  },

  // P2 - no KEV, moderate EPSS, medium asset, not internet-facing.
  {
    id: 'finding-003',
    tier: 'P2',
    assetId: 'asset-inventory-svc',
    packageName: 'org.springframework:spring-web',
    vulnerabilityId: 'CVE-2024-22243',
    aliases: ['GHSA-7hgv-m8x3-2x44'],
    affectedRanges: [
      { id: 'r-003-a', range: '<6.0.6', fixedVersion: '6.0.6' },
    ],
    kev: false,
    epss: 0.00421,
    status: 'open',
    brief:
      'URL parsing inconsistency in Spring Web can lead to incorrect authorization decisions when relying on parsed host information. Advisory: https://nvd.nist.gov/vuln/detail/CVE-2024-22243',
    structuredSummary:
      'UriComponentsBuilder parses URLs in a way that can differ from downstream parsers, enabling authorization bypass.',
    createdAt: '2024-09-05T14:05:00Z',
    audit: [],
  },

  // P2 - EPSS n/a (no score published). Ownerless asset.
  {
    id: 'finding-004',
    tier: 'P2',
    assetId: 'asset-batch-loader',
    packageName: 'io.netty:netty-codec-http',
    vulnerabilityId: 'CVE-2023-44487',
    aliases: ['GHSA-qpgw-q5hj-5r3x'],
    affectedRanges: [
      { id: 'r-004-a', range: '<4.1.100.Final', fixedVersion: '4.1.100.Final' },
    ],
    kev: false,
    epss: null,
    status: 'open',
    brief:
      'HTTP/2 rapid reset can be used to cause a denial of service. No EPSS score has been published for this advisory at the time of triage. Advisory: https://nvd.nist.gov/vuln/detail/CVE-2023-44487',
    structuredSummary:
      'A client can rapidly send and cancel streams, exhausting server resources.',
    createdAt: '2024-09-07T09:18:00Z',
    audit: [],
  },

  // P3 - risk accepted with an audit entry that includes the reason.
  {
    id: 'finding-005',
    tier: 'P3',
    assetId: 'asset-reports-worker',
    packageName: 'com.google.guava:guava',
    vulnerabilityId: 'CVE-2020-8908',
    aliases: [],
    affectedRanges: [
      { id: 'r-005-a', range: '<30.0', fixedVersion: '30.0' },
    ],
    kev: false,
    epss: 0.00071,
    status: 'risk accepted',
    brief:
      'Guava TemporaryDirectory permissions allow read access by other users on the same host. Low real-world impact for this worker which runs in an isolated pod. Advisory: https://nvd.nist.gov/vuln/detail/CVE-2020-8908',
    structuredSummary:
      'Default permissions on createTempDir are overly broad.',
    createdAt: '2024-09-09T11:42:00Z',
    audit: [
      audit(
        'aud-005-1',
        'Dana Reyes',
        '2024-09-12T16:20:00Z',
        'status',
        'open',
        'risk accepted',
        'Worker runs in an isolated pod with no co-tenant users; fix planned for next quarter.',
      ),
    ],
  },

  // P3 - fixed with a fixed timestamp and audit entry.
  {
    id: 'finding-006',
    tier: 'P3',
    assetId: 'asset-inventory-svc',
    packageName: 'commons-io:commons-io',
    vulnerabilityId: 'CVE-2024-47554',
    aliases: ['GHSA-3h7h-r4h5-2xq2'],
    affectedRanges: [
      { id: 'r-006-a', range: '<2.14.0', fixedVersion: '2.14.0' },
    ],
    kev: false,
    epss: 0.00112,
    status: 'fixed',
    fixedAt: '2024-09-18T09:00:00Z',
    brief:
      'Path traversal in XmlStreamReader can be triggered by untrusted input. Resolved by upgrading commons-io. Advisory: https://nvd.nist.gov/vuln/detail/CVE-2024-47554',
    structuredSummary:
      'XmlStreamReader processes external entities from untrusted input without sanitization.',
    createdAt: '2024-09-10T07:25:00Z',
    audit: [
      audit(
        'aud-006-1',
        'Marcus Lee',
        '2024-09-18T09:00:00Z',
        'status',
        'open',
        'fixed',
      ),
    ],
  },

  // P4 - withdrawn with an audit entry and a note. Brief unavailable.
  {
    id: 'finding-007',
    tier: 'P4',
    assetId: 'asset-reports-worker',
    packageName: 'org.yaml:snakeyaml',
    vulnerabilityId: 'CVE-2022-1471',
    aliases: ['GHSA-mjmj-j483-5g5g'],
    affectedRanges: [
      { id: 'r-007-a', range: '<2.0', fixedVersion: '2.0' },
    ],
    kev: false,
    epss: 0.00031,
    status: 'withdrawn',
    withdrawnNote:
      'The advisory was withdrawn from the upstream feed: the reported behavior was deemed expected functionality by the maintainer.',
    brief: null,
    structuredSummary:
      'SnakeYAML SafeConstructor was reported as allowing arbitrary class construction; maintainer assessment is that this is documented behavior.',
    createdAt: '2024-09-11T13:10:00Z',
    audit: [
      audit(
        'aud-007-1',
        'feed-sync',
        '2024-09-15T06:00:00Z',
        'status',
        'open',
        'withdrawn',
        'Advisory left its feed.',
      ),
    ],
  },

  // P4 - lowest priority, no fixed version on its only range.
  {
    id: 'finding-008',
    tier: 'P4',
    assetId: 'asset-batch-loader',
    packageName: 'com.h2database:h2',
    vulnerabilityId: 'CVE-2022-23221',
    aliases: [],
    affectedRanges: [
      { id: 'r-008-a', range: '>=1.1.106 <2.1.210', fixedVersion: null },
    ],
    kev: false,
    epss: 0.00017,
    status: 'open',
    brief:
      'H2 Console can be abused for remote code execution when the console is exposed. The affected range has no fixed version yet in this feed. Advisory: https://nvd.nist.gov/vuln/detail/CVE-2022-23221',
    structuredSummary:
      'JNDI lookup in the H2 Console leads to RCE when the console endpoint is reachable.',
    createdAt: '2024-09-12T15:48:00Z',
    audit: [],
  },
];
