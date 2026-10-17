import type {
  Asset,
  AssetInput,
  Finding,
  User,
} from '../types';
import type {
  AcceptRiskInput,
  AcceptRiskResult,
  RegisterAssetResult,
  SignInInput,
  SignInResult,
  VulnTriageServices,
} from './types';
import { mockAssets, mockFindings, rankFindings } from './mockData';

// Demo credentials (fictional). Shown on the login screen.
const DEMO_EMAIL = 'dana.reyes@example.com';
const DEMO_PASSWORD = 'triage-demo';
const DEMO_USER: User = {
  id: 'user-001',
  name: 'Dana Reyes',
  email: DEMO_EMAIL,
};

function assetsById(): Map<string, Asset> {
  return new Map(mockAssets.map((a) => [a.id, a]));
}

// In-memory mutable copies so risk acceptance persists for the session.
// We start from the mock data on first access.
let findingsStore: Finding[] | null = null;
let assetsStore: Asset[] | null = null;
let currentUser: User | null = null;

function ensureStores(): void {
  if (findingsStore === null) {
    findingsStore = mockFindings.map((f) => ({
      ...f,
      affectedRanges: f.affectedRanges.map((r) => ({ ...r })),
      aliases: [...f.aliases],
      audit: f.audit.map((a) => ({ ...a })),
    }));
  }
  if (assetsStore === null) {
    assetsStore = mockAssets.map((a) => ({ ...a }));
  }
}

function resetStores(): void {
  findingsStore = null;
  assetsStore = null;
}

export const mockServices: VulnTriageServices = {
  signIn(input: SignInInput): SignInResult {
    ensureStores();
    if (input.email === DEMO_EMAIL && input.password === DEMO_PASSWORD) {
      currentUser = DEMO_USER;
      return { ok: true, user: DEMO_USER };
    }
    return { ok: false, error: 'Invalid email or password.' };
  },

  signOut(): void {
    currentUser = null;
    // Reset stores so the next session sees fresh mock data.
    resetStores();
  },

  currentUser(): User | null {
    return currentUser;
  },

  listFindings(): Finding[] {
    ensureStores();
    return rankFindings(findingsStore!, assetsById());
  },

  getFinding(id: string): Finding | null {
    ensureStores();
    return findingsStore!.find((f) => f.id === id) ?? null;
  },

  acceptRisk(input: AcceptRiskInput): AcceptRiskResult {
    ensureStores();
    const idx = findingsStore!.findIndex((f) => f.id === input.findingId);
    if (idx === -1) {
      return { ok: false, error: 'Finding not found.' };
    }
    const finding = findingsStore![idx];

    // Validation: a reason that is empty or whitespace-only is rejected,
    // and the status does not change.
    const reason = input.reason?.trim() ?? '';
    if (reason === '') {
      return {
        ok: false,
        error: 'A reason is required to accept risk.',
      };
    }

    if (finding.status === 'withdrawn') {
      return {
        ok: false,
        error: 'A withdrawn finding cannot be risk accepted.',
      };
    }

    const previous = finding.status;
    const updated: Finding = {
      ...finding,
      status: 'risk accepted',
      audit: [
        ...finding.audit,
        {
          id: `aud-${finding.id}-${finding.audit.length + 1}`,
          who: currentUser?.name ?? 'unknown',
          when: new Date().toISOString(),
          field: 'status',
          previousValue: previous,
          newValue: 'risk accepted',
          reason,
        },
      ],
    };
    findingsStore![idx] = updated;
    return { ok: true, finding: updated };
  },

  listAssets(): Asset[] {
    ensureStores();
    return [...assetsStore!];
  },

  getAsset(id: string): Asset | null {
    ensureStores();
    return assetsStore!.find((a) => a.id === id) ?? null;
  },

  registerAsset(input: AssetInput): RegisterAssetResult {
    ensureStores();
    const name = input.name?.trim() ?? '';
    if (name === '') {
      return { ok: false, error: 'Asset name is required.' };
    }
    const asset: Asset = {
      id: `asset-${name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${Date.now()}`,
      name,
      owner: input.owner?.trim() ? input.owner.trim() : null,
      ownerEmail: input.ownerEmail?.trim() ? input.ownerEmail.trim() : null,
      criticality: input.criticality,
      internetFacing: input.internetFacing,
      repositoryUrl: input.repositoryUrl?.trim()
        ? input.repositoryUrl.trim()
        : null,
      // A newly registered asset has not been scanned yet.
      scanState: 'not yet scanned',
    };
    assetsStore!.push(asset);
    return { ok: true, asset };
  },
};

export const DEMO_CREDENTIALS = {
  email: DEMO_EMAIL,
  password: DEMO_PASSWORD,
};
