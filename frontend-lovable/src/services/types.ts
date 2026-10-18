export type Tier = "P1" | "P2" | "P3" | "P4";
export type FindingStatus = "open" | "risk_accepted" | "fixed" | "withdrawn";
export type Criticality = "low" | "medium" | "high" | "critical";
export type ScanStatus = "scanned" | "scan_error" | "not_scanned";

export interface User {
  id: string;
  name: string;
  email: string;
}

export interface Asset {
  id: string;
  name: string;
  owner: string | null;
  criticality: Criticality;
  internetFacing: boolean;
  repositoryUrl: string;
  scanStatus: ScanStatus;
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
  owner: string;
  criticality: Criticality;
  internetFacing: boolean;
  repositoryUrl: string;
}

/** Every backend call the app makes goes through this interface. */
export interface Services {
  login(username: string, password: string): Promise<User>;
  listFindings(): Promise<FindingWithAsset[]>;
  getFinding(id: string): Promise<FindingWithAsset | null>;
  acceptRisk(id: string, reason: string, user: User): Promise<FindingWithAsset>;
  listAssets(): Promise<Asset[]>;
  registerAsset(input: NewAssetInput): Promise<Asset>;
}

export const STATUS_LABEL: Record<FindingStatus, string> = {
  open: "open",
  risk_accepted: "risk accepted",
  fixed: "fixed",
  withdrawn: "withdrawn",
};
