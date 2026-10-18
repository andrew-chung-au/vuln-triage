import { validateAssetName, validateRiskReason } from "@/lib/validation";
import { DEMO_CREDENTIALS, DEMO_USER, seedAssets, seedFindings } from "./mockData";
import type { Asset, Criticality, Finding, FindingWithAsset, Services, Tier } from "./types";

let assets: Asset[] = seedAssets();
let findings: Finding[] = seedFindings();

/** Restore the in-memory data to its seed state (used by tests). */
export function resetMockData() {
  assets = seedAssets();
  findings = seedFindings();
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
    return a.firstSeen.localeCompare(b.firstSeen);
  });
}

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v));

function join(f: Finding): FindingWithAsset {
  const asset = assets.find((a) => a.id === f.assetId)!;
  return clone({ ...f, asset });
}

const delay = () => new Promise((r) => setTimeout(r, 0));

export const mockServices: Services = {
  async login(username, password) {
    await delay();
    if (username.trim().toLowerCase() === DEMO_CREDENTIALS.username && password === DEMO_CREDENTIALS.password) {
      return clone(DEMO_USER);
    }
    throw new Error("Incorrect username or password.");
  },

  async listFindings() {
    await delay();
    return rankFindings(findings.map(join));
  },

  async getFinding(id) {
    await delay();
    const f = findings.find((x) => x.id === id);
    return f ? join(f) : null;
  },

  async acceptRisk(id, reason, user) {
    await delay();
    const err = validateRiskReason(reason);
    if (err) throw new Error(err);
    const f = findings.find((x) => x.id === id);
    if (!f) throw new Error("Finding not found.");
    if (f.status !== "open") throw new Error("Only open findings can be risk accepted.");
    f.auditTrail.push({
      who: user.name,
      when: new Date().toISOString(),
      field: "status",
      previousValue: "open",
      newValue: "risk accepted",
      reason: reason.trim(),
    });
    f.status = "risk_accepted";
    return join(f);
  },

  async listAssets() {
    await delay();
    return clone(assets);
  },

  async registerAsset(input) {
    await delay();
    const err = validateAssetName(input.name);
    if (err) throw new Error(err);
    const asset: Asset = {
      id: `a${Date.now()}`,
      name: input.name.trim(),
      owner: input.owner.trim() || null,
      criticality: input.criticality,
      internetFacing: input.internetFacing,
      repositoryUrl: input.repositoryUrl.trim(),
      scanStatus: "not_scanned",
    };
    assets.push(asset);
    return clone(asset);
  },
};
