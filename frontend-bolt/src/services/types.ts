import type {
  Asset,
  AssetInput,
  Finding,
  FindingStatus,
  User,
} from '../types';

// ---------------------------------------------------------------------------
// Services layer
//
// One small typed function per read or write. The app never talks to a
// backend directly; it goes through these. Today the implementation is mock
// and in-memory, but each function maps 1:1 onto a future API call.
// ---------------------------------------------------------------------------

export interface SignInInput {
  email: string;
  password: string;
}

export interface SignInResult {
  ok: boolean;
  user?: User;
  error?: string;
}

export interface AcceptRiskInput {
  findingId: string;
  reason: string;
}

export interface AcceptRiskResult {
  ok: boolean;
  finding?: Finding;
  error?: string;
}

export interface RegisterAssetResult {
  ok: boolean;
  asset?: Asset;
  error?: string;
}

export interface VulnTriageServices {
  // auth
  signIn(input: SignInInput): SignInResult;
  signOut(): void;
  currentUser(): User | null;

  // findings
  listFindings(): Finding[];
  getFinding(id: string): Finding | null;
  acceptRisk(input: AcceptRiskInput): AcceptRiskResult;

  // assets
  listAssets(): Asset[];
  getAsset(id: string): Asset | null;
  registerAsset(input: AssetInput): RegisterAssetResult;
}

export const FINDING_STATUS_VALUES: FindingStatus[] = [
  'open',
  'risk accepted',
  'fixed',
  'withdrawn',
];
