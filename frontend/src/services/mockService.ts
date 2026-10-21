import { validateAssetName, validateOwnerEmail, validateRepositoryUrl, validateRiskReason } from "@/lib/validation";
import { DEMO_CREDENTIALS, DEMO_OWNER_CREDENTIALS, DEMO_OWNER_USER, DEMO_USER, seedAssets, seedFindings } from "./mockData";
import { AUDIT_SOURCE_DASHBOARD, ServiceError, isUser } from "./types";
import type { Asset, AuditEntry, Criticality, Finding, FindingWithAsset, Services, Tier, User } from "./types";

let assets: Asset[] = seedAssets();
let findings: Finding[] = seedFindings();

// The services layer owns the signed-in session so every implementation of
// Services behaves like the real API, not like the UI's local copy of a user.
const SESSION_KEY = "vulntriage-services-user";
let sessionUser: User | null = null;
let sessionLoaded = false;

/** A session stored by an older build (no role or displayName) counts as no session. */
function parseStoredUser(value: unknown): User | null {
  return isUser(value) ? value : null;
}

function loadSession() {
  if (sessionLoaded) return;
  sessionLoaded = true;
  if (typeof window === "undefined") return;
  try {
    const raw = window.sessionStorage.getItem(SESSION_KEY);
    sessionUser = raw ? parseStoredUser(JSON.parse(raw)) : null;
  } catch {
    sessionUser = null;
  }
}

function getSessionUser(): User | null {
  loadSession();
  return sessionUser;
}

function setSessionUser(user: User | null) {
  sessionLoaded = true;
  sessionUser = user;
  if (typeof window === "undefined") return;
  try {
    if (user) window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(user));
    else window.sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // Session storage can be unavailable; the in-memory session still works.
  }
}

function requireSession(): User {
  const user = getSessionUser();
  if (!user) throw new ServiceError("unauthenticated", "Sign in to continue.");
  return user;
}

/** Restore the in-memory data to its seed state (used by tests). */
export function resetMockData() {
  assets = seedAssets();
  findings = seedFindings();
}

/** Clear the services session, including the persisted copy (used by tests). */
export function resetMockSession() {
  setSessionUser(null);
}

const TIER_ORDER: Record<Tier, number> = { P1: 1, P2: 2, P3: 3, P4: 4 };
const CRIT_ORDER: Record<Criticality, number> = { critical: 4, high: 3, medium: 2, low: 1 };

/** Ranking the backend would apply: tier, EPSS desc (n/a last), criticality desc, oldest first. */
export function rankFindings(list: FindingWithAsset[]): FindingWithAsset[] {
  return [...list].sort((a, b) => {
    const t = TIER_ORDER[a.tier] - TIER_ORDER[b.tier];
    if (t) return t;
    if (a.epss !== b.epss) {
      if (a.epss === null) return 1;
      if (b.epss === null) return -1;
      return b.epss - a.epss;
    }
    const c = CRIT_ORDER[b.asset.criticality] - CRIT_ORDER[a.asset.criticality];
    if (c) return c;
    return a.firstDetectedAt.localeCompare(b.firstDetectedAt);
  });
}

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v));

function join(f: Finding): FindingWithAsset {
  const asset = assets.find((a) => a.id === f.assetId)!;
  return clone({ ...f, asset });
}

function nextAuditId(f: Finding): string {
  const used = new Set(f.auditTrail.map((a) => a.id));
  let n = f.auditTrail.length + 1;
  let id = `aud-${f.id}-${n}`;
  while (used.has(id)) {
    n += 1;
    id = `aud-${f.id}-${n}`;
  }
  return id;
}

const delay = () => new Promise((r) => setTimeout(r, 0));

export const mockServices: Services = {
  async login(username, password) {
    await delay();
    const name = username.trim().toLowerCase();
    const match = [
      { credentials: DEMO_CREDENTIALS, user: DEMO_USER },
      { credentials: DEMO_OWNER_CREDENTIALS, user: DEMO_OWNER_USER },
    ].find((c) => c.credentials.username === name && c.credentials.password === password);
    if (!match) {
      throw new ServiceError("unauthenticated", "Incorrect username or password.");
    }
    const user = clone(match.user);
    setSessionUser(user);
    return clone(user);
  },

  async logout() {
    await delay();
    setSessionUser(null);
  },

  async currentUser() {
    await delay();
    return clone(requireSession());
  },

  async listFindings() {
    await delay();
    requireSession();
    return rankFindings(findings.map(join));
  },

  async getFinding(id) {
    await delay();
    requireSession();
    const f = findings.find((x) => x.id === id);
    if (!f) throw new ServiceError("not_found", "Finding not found.");
    return join(f);
  },

  async acceptRisk(id, reason) {
    await delay();
    const user = requireSession();
    // Contract order: 401, 404, 403 (owner mismatch), 422, 409.
    const f = findings.find((x) => x.id === id);
    if (!f) throw new ServiceError("not_found", "Finding not found.");
    if (user.role === "asset owner") {
      const owner = assets.find((a) => a.id === f.assetId)?.ownerEmail ?? null;
      if (owner === null || owner.trim().toLowerCase() !== user.email.trim().toLowerCase()) {
        throw new ServiceError("forbidden", "You can only accept risk on findings for assets you own.");
      }
    }
    const err = validateRiskReason(reason);
    if (err) throw new ServiceError("validation", err);
    if (f.status !== "open") throw new ServiceError("conflict", "Only open findings can be risk accepted.");
    const entry: AuditEntry = {
      id: nextAuditId(f),
      actor: user.id,
      actorDisplayName: user.displayName,
      createdAt: new Date().toISOString(),
      field: "status",
      previousValue: f.status,
      newValue: "risk accepted",
      reason: reason.trim(),
      source: AUDIT_SOURCE_DASHBOARD,
      restoresEntryId: null,
    };
    f.auditTrail.push(entry);
    f.status = "risk accepted";
    return join(f);
  },

  async listAssets() {
    await delay();
    requireSession();
    return clone(assets);
  },

  async getAsset(id) {
    await delay();
    requireSession();
    const asset = assets.find((a) => a.id === id);
    if (!asset) throw new ServiceError("not_found", "Asset not found.");
    return clone(asset);
  },

  async registerAsset(input) {
    await delay();
    requireSession();
    const err = validateAssetName(input.name);
    if (err) throw new ServiceError("validation", err);
    const emailErr = validateOwnerEmail(input.ownerEmail);
    if (emailErr) throw new ServiceError("validation", emailErr);
    const urlErr = validateRepositoryUrl(input.repositoryUrl);
    if (urlErr) throw new ServiceError("validation", urlErr);
    const asset: Asset = {
      id: `a${Date.now()}-${assets.length + 1}`,
      name: input.name.trim(),
      ownerName: input.ownerName?.trim() || null,
      ownerEmail: input.ownerEmail?.trim() || null,
      criticality: input.criticality,
      internetFacing: input.internetFacing,
      repositoryUrl: input.repositoryUrl.trim(),
      scanStatus: "not yet scanned",
      scanFailureReason: null,
      lastScanAt: null,
      lastCommitSha: null,
      scanWarnings: [],
    };
    assets.push(asset);
    return clone(asset);
  },

  async reScan(assetId) {
    await delay();
    requireSession();
    if (!assets.some((a) => a.id === assetId)) throw new ServiceError("not_found", "Asset not found.");
    // The scan runs asynchronously: scanStatus changes only when it finishes, so the mock leaves it alone.
  },
};
