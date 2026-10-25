// Wire shapes follow _docs/openapi.yaml (issue #45, D4 in _docs/api.md).
export type Tier = "P1" | "P2" | "P3" | "P4";
export type FindingStatus = "open" | "risk accepted" | "fixed" | "withdrawn";
export type Criticality = "low" | "medium" | "high" | "critical";
export type ScanStatus =
  | "not yet scanned"
  | "scan failed"
  | "scanned, findings"
  | "scanned, incomplete"
  | "scanned, clean";
export type ScanFailureReason =
  | "feed unavailable"
  | "lockfile parse error"
  | "repository unavailable"
  | "no dependency files"
  | "internal error";
export type KevValue = "KEV: listed" | "KEV: not listed" | "KEV: n/a (no CVE)";
export type UserRole = "security lead" | "asset owner";
export type BriefStatus = "available" | "unavailable" | "pending";
export type Ecosystem = "PyPI" | "npm";

export type ServiceErrorCode = "validation" | "not_found" | "conflict" | "unauthenticated" | "forbidden";

/** Every rejection from the services layer is one of these. */
export class ServiceError extends Error {
  readonly code: ServiceErrorCode;

  constructor(code: ServiceErrorCode, message: string) {
    super(message);
    this.name = "ServiceError";
    this.code = code;
  }
}

export interface User {
  id: string;
  username: string;
  displayName: string;
  email: string;
  role: UserRole;
}

/** True for a complete current-shape User; a value stored by an older build is not one. */
export function isUser(value: unknown): value is User {
  if (typeof value !== "object" || value === null) return false;
  const u = value as Partial<Record<keyof User, unknown>>;
  return (
    typeof u.id === "string" &&
    typeof u.username === "string" &&
    typeof u.displayName === "string" &&
    typeof u.email === "string" &&
    (u.role === "security lead" || u.role === "asset owner")
  );
}

export interface ScanWarning {
  kind: string;
  file: string;
  line: number | null;
  message: string;
}

export interface Asset {
  id: string;
  name: string;
  ownerName: string | null;
  ownerEmail: string | null;
  criticality: Criticality;
  internetFacing: boolean;
  repositoryUrl: string;
  scanStatus: ScanStatus;
  /** Null unless scanStatus is "scan failed". */
  scanFailureReason: ScanFailureReason | null;
  lastScanAt: string | null;
  lastCommitSha: string | null;
  scanWarnings: ScanWarning[];
}

/** An asset is ownerless only when neither owner field is set. */
export function isOwnerless(asset: Pick<Asset, "ownerName" | "ownerEmail">): boolean {
  return asset.ownerName === null && asset.ownerEmail === null;
}

export interface Dependency {
  version: string | null;
  sourceFile: string;
  direct: boolean;
}

export interface AffectedRange {
  range: string;
  fixedVersion: string | null;
}

export interface Brief {
  summary: string;
  impact: string;
  remediation: string;
  fixVersion: string | null;
  referenceLink: string;
}

export interface AuditEntry {
  id: string;
  /** A user id, "re-scan" or "system". */
  actor: string;
  /** Null for "re-scan" and "system". */
  actorDisplayName: string | null;
  createdAt: string;
  field: string;
  previousValue: string | null;
  newValue: string;
  /** Non-empty when newValue is "risk accepted"; otherwise nullable. */
  reason: string | null;
  source: string;
  restoresEntryId: string | null;
}

export interface Finding {
  id: string;
  vulnerabilityId: string;
  aliases: string[];
  cveId: string | null;
  tier: Tier;
  assetId: string;
  package: string;
  ecosystem: Ecosystem;
  dependencies: Dependency[];
  fixedVersion: string | null;
  affectedRanges: AffectedRange[];
  kev: KevValue;
  kevStale: boolean;
  epss: number | null;
  epssStale: boolean;
  status: FindingStatus;
  firstDetectedAt: string;
  fixedAt: string | null;
  stale: boolean;
  staleSince: string | null;
  signalsChanged: boolean;
  statusBeforeWithdrawal: FindingStatus | null;
  rankReason: string;
  briefStatus: BriefStatus;
  brief: Brief | null;
  auditTrail: AuditEntry[];
}

/** A finding joined with its asset, as returned by the services layer. */
export interface FindingWithAsset extends Finding {
  asset: Asset;
}

export interface NewAssetInput {
  name: string;
  ownerName: string | null;
  ownerEmail: string | null;
  criticality: Criticality;
  internetFacing: boolean;
  repositoryUrl: string;
}

/** Every backend call the app makes goes through this interface. */
export interface Services {
  login(username: string, password: string): Promise<User>;
  logout(): Promise<void>;
  currentUser(): Promise<User>;
  listFindings(): Promise<FindingWithAsset[]>;
  getFinding(id: string): Promise<FindingWithAsset>;
  acceptRisk(id: string, reason: string): Promise<FindingWithAsset>;
  listAssets(): Promise<Asset[]>;
  getAsset(id: string): Promise<Asset>;
  registerAsset(input: NewAssetInput): Promise<Asset>;
  /** POST /assets/{id}/rescan: 202, no body. The asset's scanStatus does not change here. */
  reScan(assetId: string): Promise<void>;
}

export const STATUS_LABEL: Record<FindingStatus, string> = {
  open: "open",
  "risk accepted": "risk accepted",
  fixed: "fixed",
  withdrawn: "withdrawn",
};

/** AuditEntry.source for a change made from the dashboard (architecture Data model). */
export const AUDIT_SOURCE_DASHBOARD = "dashboard";
