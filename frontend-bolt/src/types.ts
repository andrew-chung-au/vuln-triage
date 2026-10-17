// Domain types for VulnTriage.
// The services layer and the UI both speak these types.

export type Tier = 'P1' | 'P2' | 'P3' | 'P4';

export type FindingStatus = 'open' | 'risk accepted' | 'fixed' | 'withdrawn';

export type Criticality = 'low' | 'medium' | 'high' | 'critical';

export type AssetScanState = 'ok' | 'scan error' | 'not yet scanned';

export interface Asset {
  id: string;
  name: string;
  owner: string | null;
  ownerEmail: string | null;
  criticality: Criticality;
  internetFacing: boolean;
  repositoryUrl: string | null;
  scanState: AssetScanState;
}

export interface AffectedRange {
  id: string;
  // Human-readable version range, e.g. ">=1.2.0 <2.0.0"
  range: string;
  // null means "no fixed version" for this range
  fixedVersion: string | null;
}

export interface AuditEntry {
  id: string;
  who: string;
  when: string; // ISO timestamp
  field: string;
  previousValue: string;
  newValue: string;
  // Free-form detail, e.g. the risk-acceptance reason.
  reason?: string;
}

export interface Finding {
  id: string;
  tier: Tier;
  assetId: string;
  packageName: string;
  // Primary vulnerability id, e.g. "CVE-2024-1234"
  vulnerabilityId: string;
  // Other ids this finding is also known as, e.g. GHSA aliases
  aliases: string[];
  affectedRanges: AffectedRange[];
  kev: boolean;
  // null/undefined means "EPSS: n/a"
  epss: number | null;
  status: FindingStatus;
  // Present only when status === 'fixed'
  fixedAt?: string;
  // Present only when status === 'withdrawn'
  withdrawnNote?: string;
  // AI brief. null means the brief was rejected; the structured finding
  // is still shown with a "brief unavailable" marker.
  brief: string | null;
  // Structured finding shown when the brief is unavailable (or alongside it).
  structuredSummary: string;
  createdAt: string; // ISO timestamp, used as a tie-breaker in ranking
  audit: AuditEntry[];
}

export interface User {
  id: string;
  name: string;
  email: string;
}

export interface AssetInput {
  name: string;
  owner: string | null;
  ownerEmail: string | null;
  criticality: Criticality;
  internetFacing: boolean;
  repositoryUrl: string | null;
}

// Ordered ranking helpers. Higher index = higher priority.
export const TIER_ORDER: Tier[] = ['P1', 'P2', 'P3', 'P4'];
export const CRITICALITY_ORDER: Criticality[] = [
  'critical',
  'high',
  'medium',
  'low',
];
