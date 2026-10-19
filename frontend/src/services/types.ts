export type Tier = "P1" | "P2" | "P3" | "P4";
export type FindingStatus = "open" | "risk_accepted" | "fixed" | "withdrawn";
export type Criticality = "low" | "medium" | "high" | "critical";
export type ScanStatus = "scanned" | "scan_error" | "not_scanned";

export type ServiceErrorCode = "validation" | "not_found" | "conflict" | "unauthenticated";

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
  name: string;
  email: string;
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
}

/** An asset is ownerless only when neither owner field is set. */
export function isOwnerless(asset: Pick<Asset, "ownerName" | "ownerEmail">): boolean {
  return asset.ownerName === null && asset.ownerEmail === null;
}

export interface AffectedRange {
  range: string;
  fixedVersion: string | null;
}

export interface Brief {
  summary: string;
  impact: string;
  remediation: string;
  advisoryReference: string;
}

export interface AuditEntry {
  id: string;
  who: string;
  when: string;
  field: string;
  previousValue: string;
  newValue: string;
  reason?: string;
}

export interface Finding {
  id: string;
  vulnerabilityId: string;
  aliases: string[];
  tier: Tier;
  assetId: string;
  packageName: string;
  installedVersion: string;
  affectedRanges: AffectedRange[];
  kev: boolean;
  epss: number | null;
  status: FindingStatus;
  firstSeen: string;
  fixedAt: string | null;
  briefStatus: "available" | "rejected";
  brief: Brief | null;
  structuredSummary: string;
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
}

export const STATUS_LABEL: Record<FindingStatus, string> = {
  open: "open",
  risk_accepted: "risk accepted",
  fixed: "fixed",
  withdrawn: "withdrawn",
};
