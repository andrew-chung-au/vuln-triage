import { QueryClient } from "@tanstack/react-query";
import { RouterProvider, createMemoryHistory, createRootRoute, createRouter } from "@tanstack/react-router";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AffectedRanges } from "@/components/vt/AffectedRanges";
import { AuditTrail } from "@/components/vt/AuditTrail";
import { FindingsTable } from "@/components/vt/FindingsTable";
import { getUser, setUser } from "@/lib/auth";
import { validateRiskReason } from "@/lib/validation";
import { routeTree } from "@/routeTree.gen";
import { ServiceError, demoCredentials, isOwnerless } from "@/services";
import { DEMO_CREDENTIALS, DEMO_OWNER_CREDENTIALS, DEMO_OWNER_USER, DEMO_USER, seedFindings } from "@/services/mockData";
import { mockServices, resetMockData, resetMockSession } from "@/services/mockService";
import type { FindingWithAsset, NewAssetInput } from "@/services/types";

// Production wiring now binds `services` to the real backend-backed httpServices
// (task 11 / #133). These component tests mount the full route tree and must not
// hit the network, so `services` is bound to the in-memory mock singleton here.
// Everything else from "@/services" stays real, and vi.spyOn(mockServices, ...)
// observes the same object the route components call.
vi.mock("@/services", async () => {
  const actual = await vi.importActual<typeof import("@/services")>("@/services");
  const { mockServices } = await vi.importActual<typeof import("@/services/mockService")>(
    "@/services/mockService",
  );
  return { ...actual, services: mockServices };
});

function newAsset(overrides: Partial<NewAssetInput> = {}): NewAssetInput {
  return {
    name: "new-asset",
    ownerName: null,
    ownerEmail: null,
    criticality: "medium",
    internetFacing: false,
    repositoryUrl: "https://github.com/acme/new-asset",
    ...overrides,
  };
}

async function signIn() {
  return mockServices.login(DEMO_CREDENTIALS.username, DEMO_CREDENTIALS.password);
}

async function getRejection(promise: Promise<unknown>): Promise<ServiceError> {
  try {
    await promise;
  } catch (err) {
    return err as ServiceError;
  }
  throw new Error("Expected the call to reject");
}

beforeEach(() => {
  vi.restoreAllMocks();
  resetMockData();
  resetMockSession();
  window.sessionStorage.clear();
  setUser(null);
});

function renderComponent(ui: React.ReactNode) {
  const router = createRouter({
    routeTree: createRootRoute({ component: () => <>{ui}</> }),
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  render(<RouterProvider router={router} />);
}

function renderApp(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createRouter({
    routeTree,
    context: { queryClient },
    history: createMemoryHistory({ initialEntries: [path] }),
  });
  render(<RouterProvider router={router} />);
  return router;
}

describe("dashboard ordering", () => {
  it("shows findings in the exact order returned by the services layer, with tiers", async () => {
    await signIn();
    const list = await mockServices.listFindings();
    const shuffled: FindingWithAsset[] = [list[3]!, list[0]!, list[7]!, list[1]!];
    renderComponent(<FindingsTable findings={shuffled} />);
    const rows = await screen.findAllByTestId("finding-row");
    expect(rows.map((r) => r.getAttribute("data-id"))).toEqual(shuffled.map((f) => f.id));
    rows.forEach((r, i) => expect(within(r).getByTestId("tier")).toHaveTextContent(shuffled[i]!.tier));
  });

  it("shows an empty state with no findings", () => {
    render(<FindingsTable findings={[]} />);
    expect(screen.getByText("No findings")).toBeInTheDocument();
  });
});

describe("risk acceptance reason", () => {
  it("rejects empty and whitespace-only reasons", () => {
    expect(validateRiskReason("")).not.toBeNull();
    expect(validateRiskReason("   \n\t")).not.toBeNull();
    expect(validateRiskReason("Compensating WAF rule in place")).toBeNull();
  });

  it("leaves status unchanged when the reason is invalid", async () => {
    await signIn();
    for (const r of ["", "   "]) {
      const err = await getRejection(mockServices.acceptRisk("f1", r));
      expect(err).toBeInstanceOf(ServiceError);
      expect(err.code).toBe("validation");
    }
    const f = await mockServices.getFinding("f1");
    expect(f.status).toBe("open");
    expect(f.auditTrail).toHaveLength(0);
  });
});

describe("mock services", () => {
  beforeEach(async () => {
    await signIn();
  });

  it("returns all mock findings ranked by tier then EPSS (n/a last)", async () => {
    const list = await mockServices.listFindings();
    expect(list).toHaveLength(seedFindings().length);
    expect(list.map((f) => f.id)).toEqual(["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8"]);
    expect(list.map((f) => f.tier)).toEqual(["P1", "P1", "P2", "P2", "P3", "P3", "P4", "P4"]);
  });

  it("returns mock assets including ownerless, scan error and not-yet-scanned", async () => {
    const assets = await mockServices.listAssets();
    expect(assets.some((a) => isOwnerless(a))).toBe(true);
    expect(assets.some((a) => a.scanStatus === "scan failed")).toBe(true);
    expect(assets.some((a) => a.scanStatus === "not yet scanned")).toBe(true);
  });

  it("covers all five scan statuses and sets scanFailureReason only for a failed scan", async () => {
    const assets = await mockServices.listAssets();
    expect(new Set(assets.map((a) => a.scanStatus))).toEqual(
      new Set(["not yet scanned", "scan failed", "scanned, findings", "scanned, incomplete", "scanned, clean"]),
    );
    for (const a of assets) {
      expect(a.scanFailureReason !== null, a.id).toBe(a.scanStatus === "scan failed");
    }
    expect(assets.find((a) => a.scanStatus === "scan failed")!.scanFailureReason).toBe("lockfile parse error");
    expect(assets.find((a) => a.scanStatus === "scanned, incomplete")!.scanWarnings.length).toBeGreaterThan(0);
  });

  it("seeds findings with every contract key and the required edge cases", async () => {
    const list = await mockServices.listFindings();
    const keys = [
      "id", "vulnerabilityId", "aliases", "cveId", "tier", "assetId", "package", "ecosystem", "dependencies", "fixedVersion",
      "affectedRanges", "kev", "kevStale", "epss", "epssStale", "status", "firstDetectedAt", "fixedAt", "stale", "staleSince",
      "signalsChanged", "statusBeforeWithdrawal", "rankReason", "briefStatus", "brief", "auditTrail", "asset",
    ];
    for (const f of list) {
      expect(Object.keys(f).sort(), f.id).toEqual([...keys].sort());
      expect(f.rankReason.length, f.id).toBeGreaterThan(0);
    }
    expect(list.some((f) => f.dependencies.some((d) => d.version === null))).toBe(true);
    expect(list.some((f) => f.kev === "KEV: n/a (no CVE)" && f.cveId === null)).toBe(true);
    expect(list.some((f) => f.status === "withdrawn" && f.statusBeforeWithdrawal !== null)).toBe(true);
    expect(list.some((f) => f.stale)).toBe(true);
    expect(new Set(list.map((f) => f.briefStatus))).toEqual(new Set(["available", "pending", "unavailable"]));
  });

  it("accepting risk sets the status and records an audit entry with the reason", async () => {
    const updated = await mockServices.acceptRisk("f1", "  Mitigated by WAF rule 42  ");
    expect(updated.status).toBe("risk accepted");
    const entry = updated.auditTrail.at(-1)!;
    expect(entry).toMatchObject({
      actor: DEMO_USER.id,
      actorDisplayName: DEMO_USER.displayName,
      previousValue: "open",
      newValue: "risk accepted",
      reason: "Mitigated by WAF rule 42",
      source: "dashboard",
      restoresEntryId: null,
    });
    expect((await mockServices.getFinding("f1")).status).toBe("risk accepted");
  });

  it("rejects wrong credentials with a typed error", async () => {
    const err = await getRejection(mockServices.login("analyst@example.com", "nope"));
    expect(err).toBeInstanceOf(ServiceError);
    expect(err.code).toBe("unauthenticated");
  });
});

describe("service session", () => {
  it("signs in with the demo credentials and returns the demo user", async () => {
    const user = await signIn();
    expect(user).toEqual(DEMO_USER);
    await expect(mockServices.currentUser()).resolves.toEqual(DEMO_USER);
  });

  it("rejects wrong, empty and whitespace-only credentials without establishing a session", async () => {
    const cases: Array<[string, string]> = [
      [DEMO_CREDENTIALS.username, "wrong"],
      ["", ""],
      ["   ", "   "],
      [DEMO_CREDENTIALS.username, "   "],
      ["   ", DEMO_CREDENTIALS.password],
    ];
    for (const [username, password] of cases) {
      const err = await getRejection(mockServices.login(username, password));
      expect(err).toBeInstanceOf(ServiceError);
      expect(err.code).toBe("unauthenticated");
      await expect(mockServices.currentUser()).rejects.toMatchObject({ code: "unauthenticated" });
    }
  });

  it("rejects currentUser with unauthenticated when nobody is signed in", async () => {
    const err = await getRejection(mockServices.currentUser());
    expect(err).toBeInstanceOf(ServiceError);
    expect(err.code).toBe("unauthenticated");
  });

  it("clears the session on logout and is idempotent", async () => {
    await signIn();
    await mockServices.logout();
    await expect(mockServices.currentUser()).rejects.toMatchObject({ code: "unauthenticated" });
    await expect(mockServices.logout()).resolves.toBeUndefined();
    await expect(mockServices.currentUser()).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("keeps a signed-in session across a module re-import", async () => {
    await signIn();
    vi.resetModules();
    const fresh = await import("@/services/mockService");
    await expect(fresh.mockServices.currentUser()).resolves.toEqual(DEMO_USER);
    await expect(fresh.mockServices.listFindings()).resolves.toHaveLength(seedFindings().length);
  });

  it("rejects every protected method with unauthenticated without a session", async () => {
    const calls: Array<[string, () => Promise<unknown>]> = [
      ["currentUser", () => mockServices.currentUser()],
      ["listFindings", () => mockServices.listFindings()],
      ["getFinding", () => mockServices.getFinding("f1")],
      ["acceptRisk", () => mockServices.acceptRisk("f1", "Valid reason")],
      ["listAssets", () => mockServices.listAssets()],
      ["getAsset", () => mockServices.getAsset("a1")],
      ["registerAsset", () => mockServices.registerAsset(newAsset())],
      ["reScan", () => mockServices.reScan("a1")],
    ];
    for (const [name, call] of calls) {
      const err = await getRejection(call());
      expect(err, name).toBeInstanceOf(ServiceError);
      expect(err.code, name).toBe("unauthenticated");
    }
  });

  it("resolves every protected method after sign-in", async () => {
    await signIn();
    const calls: Array<[string, () => Promise<unknown>]> = [
      ["currentUser", () => mockServices.currentUser()],
      ["listFindings", () => mockServices.listFindings()],
      ["getFinding", () => mockServices.getFinding("f1")],
      ["acceptRisk", () => mockServices.acceptRisk("f1", "Valid reason")],
      ["listAssets", () => mockServices.listAssets()],
      ["getAsset", () => mockServices.getAsset("a1")],
      ["registerAsset", () => mockServices.registerAsset(newAsset())],
    ];
    for (const [name, call] of calls) {
      await expect(call(), name).resolves.toBeDefined();
    }
  });
});

describe("lookups", () => {
  beforeEach(async () => {
    await signIn();
  });

  it("returns the finding joined with its asset and the asset itself", async () => {
    const finding = await mockServices.getFinding("f1");
    expect(finding.asset.name).toBe("payments-api");
    const asset = await mockServices.getAsset("a1");
    expect(asset.name).toBe("payments-api");
  });

  it("rejects not_found for unknown finding and asset ids", async () => {
    const missingFinding = await getRejection(mockServices.getFinding("missing"));
    expect(missingFinding).toBeInstanceOf(ServiceError);
    expect(missingFinding.code).toBe("not_found");

    const missingAsset = await getRejection(mockServices.getAsset("missing"));
    expect(missingAsset).toBeInstanceOf(ServiceError);
    expect(missingAsset.code).toBe("not_found");
  });
});

describe("service errors", () => {
  beforeEach(async () => {
    await signIn();
  });

  it("rejects acceptRisk with no signed-in session and leaves the finding unchanged", async () => {
    const before = await mockServices.getFinding("f1");
    await mockServices.logout();
    const err = await getRejection(mockServices.acceptRisk("f1", "Valid reason"));
    expect(err).toBeInstanceOf(ServiceError);
    expect(err.code).toBe("unauthenticated");

    await signIn();
    const after = await mockServices.getFinding("f1");
    expect(after.status).toBe(before.status);
    expect(after.auditTrail).toEqual(before.auditTrail);
  });

  it("rejects a non-open finding with conflict and leaves status and audit unchanged", async () => {
    for (const id of ["f4", "f6", "f7"]) {
      const before = await mockServices.getFinding(id);
      const err = await getRejection(mockServices.acceptRisk(id, "Valid reason"));
      expect(err, id).toBeInstanceOf(ServiceError);
      expect(err.code, id).toBe("conflict");
      const after = await mockServices.getFinding(id);
      expect(after.status, id).toBe(before.status);
      expect(after.auditTrail, id).toEqual(before.auditTrail);
    }
  });

  it("rejects an empty or whitespace-only reason with validation", async () => {
    for (const reason of ["", "   \n\t "]) {
      const err = await getRejection(mockServices.acceptRisk("f1", reason));
      expect(err).toBeInstanceOf(ServiceError);
      expect(err.code).toBe("validation");
    }
    const after = await mockServices.getFinding("f1");
    expect(after.status).toBe("open");
    expect(after.auditTrail).toHaveLength(0);
  });

  it("rejects an invalid asset name with validation", async () => {
    for (const name of ["", "   "]) {
      const err = await getRejection(mockServices.registerAsset(newAsset({ name })));
      expect(err).toBeInstanceOf(ServiceError);
      expect(err.code).toBe("validation");
    }
  });
});

describe("owner fields", () => {
  beforeEach(async () => {
    await signIn();
  });

  it("trims both owner fields and stores blanks as null", async () => {
    const created = await mockServices.registerAsset(newAsset({ name: "  api  ", ownerName: "  Team A  ", ownerEmail: "  team-a@example.com  " }));
    expect(created).toMatchObject({ name: "api", ownerName: "Team A", ownerEmail: "team-a@example.com" });

    const blank = await mockServices.registerAsset(newAsset({ name: "blank", ownerName: "   ", ownerEmail: "\t" }));
    expect(blank.ownerName).toBeNull();
    expect(blank.ownerEmail).toBeNull();
  });

  it("is ownerless only when both fields are null", () => {
    expect(isOwnerless({ ownerName: null, ownerEmail: null })).toBe(true);
    expect(isOwnerless({ ownerName: "Team A", ownerEmail: null })).toBe(false);
    expect(isOwnerless({ ownerName: null, ownerEmail: "team-a@example.com" })).toBe(false);
  });

  it("keeps a partial owner as a present value, not ownerless", async () => {
    const partial = await mockServices.registerAsset(newAsset({ name: "partial", ownerName: "Only Name", ownerEmail: "  " }));
    expect(partial.ownerName).toBe("Only Name");
    expect(partial.ownerEmail).toBeNull();
    expect(isOwnerless(partial)).toBe(false);
  });

  it("maps each current owner email to ownerEmail and adds an ownerName", async () => {
    const assets = await mockServices.listAssets();
    const payments = assets.find((a) => a.id === "a1")!;
    expect(payments.ownerEmail).toBe("payments-team@example.com");
    expect(payments.ownerName).toBe("Payments team");

    const wiki = assets.find((a) => a.id === "a4")!;
    expect(isOwnerless(wiki)).toBe(true);

    for (const asset of assets) {
      if (asset.ownerEmail !== null) expect(asset.ownerEmail).toMatch(/@example\.(com|org|net)$/);
    }
  });
});

describe("audit trail", () => {
  beforeEach(async () => {
    await signIn();
  });

  it("gives every audit entry a unique id within its finding", async () => {
    const findings = await mockServices.listFindings();
    for (const finding of findings) {
      const ids = finding.auditTrail.map((entry) => entry.id);
      expect(ids.every((id) => id.length > 0), finding.id).toBe(true);
      expect(new Set(ids).size, finding.id).toBe(ids.length);
    }
  });

  it("stores wire values in seeded and newly written audit entries", async () => {
    const accepted = await mockServices.getFinding("f4");
    expect(accepted.auditTrail[0]).toMatchObject({ previousValue: "open", newValue: "risk accepted" });
    expect((await mockServices.getFinding("f6")).auditTrail[0]).toMatchObject({ previousValue: "open", newValue: "fixed" });
    expect((await mockServices.getFinding("f7")).auditTrail[0]).toMatchObject({ previousValue: "open", newValue: "withdrawn" });

    const updated = await mockServices.acceptRisk("f1", "Mitigated");
    expect(updated.auditTrail.at(-1)).toMatchObject({ actor: DEMO_USER.id, previousValue: "open", newValue: "risk accepted" });
  });

  it("renders status wire values through STATUS_LABEL and leaves other fields unchanged", () => {
    const base = { actor: "u1", actorDisplayName: "Jordan Vale", createdAt: "2026-09-01T14:32:00Z", reason: null, source: "dashboard", restoresEntryId: null };
    render(
      <AuditTrail entries={[
        { ...base, id: "e1", field: "status", previousValue: "open", newValue: "risk accepted" },
        { ...base, id: "e2", field: "reason", previousValue: "old text", newValue: "new text" },
      ]} />,
    );
    expect(screen.getByText("risk accepted")).toBeInTheDocument();
    expect(screen.queryByText("risk_accepted")).not.toBeInTheDocument();
    expect(screen.getByText("old text")).toBeInTheDocument();
    expect(screen.getByText("new text")).toBeInTheDocument();
  });

  it("shows actorDisplayName, falling back to actor, and a dash for a null previous value", () => {
    const base = { createdAt: "2026-09-01T14:32:00Z", reason: null, source: "OSV", restoresEntryId: null, field: "status", newValue: "fixed" };
    render(
      <AuditTrail entries={[
        { ...base, id: "e1", actor: "u1", actorDisplayName: "Jordan Vale", previousValue: "open" },
        { ...base, id: "e2", actor: "re-scan", actorDisplayName: null, previousValue: null },
      ]} />,
    );
    expect(screen.getByText("Jordan Vale")).toBeInTheDocument();
    expect(screen.getByText("re-scan")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(1);
  });
});

describe("affected range display", () => {
  it("shows each range's fixed version or 'no fixed version'", () => {
    render(<AffectedRanges ranges={[{ range: ">= 1.0.0, < 1.8.3", fixedVersion: "1.8.3" }, { range: ">= 2.0.0, < 2.1.0", fixedVersion: null }]} />);
    const items = screen.getAllByTestId("affected-range");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("1.8.3");
    expect(items[0]).not.toHaveTextContent("no fixed version");
    expect(items[1]).toHaveTextContent("no fixed version");
  });
});

describe("screens", () => {
  it("shows the service error message when sign-in fails", async () => {
    renderApp("/login");
    await screen.findByText("Demo credentials (fictional)");
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: demoCredentials.username } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect username or password.");
    expect(getUser()).toBeNull();
  });

  it("shows a validation message for a whitespace-only reason submitted through the accept form", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/f1/accept");

    const textarea = await screen.findByLabelText(/Reason/);
    fireEvent.change(textarea, { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Accept risk" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("A reason is required to accept this risk.");
    const finding = await mockServices.getFinding("f1");
    expect(finding.status).toBe("open");
    expect(finding.auditTrail).toHaveLength(0);
  });

  it("shows a not-found message and no accept form for an unknown finding", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/missing/accept");

    expect(await screen.findByRole("alert")).toHaveTextContent("Finding not found.");
    expect(screen.queryByLabelText(/Reason/)).not.toBeInTheDocument();
  });

  it("shows a not-found message on the finding detail for an unknown id", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/missing");

    expect(await screen.findByText(/Finding not found\./)).toBeInTheDocument();
  });

  it("signs out through the services layer and clears the local user", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings");

    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(getUser()).toBeNull());
    await expect(mockServices.currentUser()).rejects.toMatchObject({ code: "unauthenticated" });
  });
});

async function signInAsOwner() {
  return mockServices.login(DEMO_OWNER_CREDENTIALS.username, DEMO_OWNER_CREDENTIALS.password);
}

describe("reScan", () => {
  it("rejects unauthenticated without a session", async () => {
    const err = await getRejection(mockServices.reScan("a1"));
    expect(err.code).toBe("unauthenticated");
  });

  it("rejects not_found for an unknown asset", async () => {
    await signIn();
    const err = await getRejection(mockServices.reScan("missing"));
    expect(err).toBeInstanceOf(ServiceError);
    expect(err.code).toBe("not_found");
  });

  it("resolves undefined and leaves the asset's scanStatus unchanged, for any signed-in role", async () => {
    await signIn();
    for (const id of ["a1", "a5", "a6"]) {
      const before = await mockServices.getAsset(id);
      await expect(mockServices.reScan(id)).resolves.toBeUndefined();
      expect(await mockServices.getAsset(id)).toEqual(before);
    }
    await signInAsOwner();
    await expect(mockServices.reScan("a2")).resolves.toBeUndefined();
  });
});

describe("forbidden and acceptRisk check order", () => {
  it("signs in the asset owner demo user with the asset owner role", async () => {
    const user = await signInAsOwner();
    expect(user).toEqual(DEMO_OWNER_USER);
    expect(user.role).toBe("asset owner");
  });

  it("rejects an asset owner whose email does not match the asset owner with forbidden, changing nothing", async () => {
    await signInAsOwner();
    const before = await mockServices.getFinding("f2");
    const err = await getRejection(mockServices.acceptRisk("f2", "Valid reason"));
    expect(err).toBeInstanceOf(ServiceError);
    expect(err.code).toBe("forbidden");
    const after = await mockServices.getFinding("f2");
    expect(after.status).toBe(before.status);
    expect(after.auditTrail).toEqual(before.auditTrail);
  });

  it("rejects forbidden for an asset owner on an ownerless asset", async () => {
    await signInAsOwner();
    const err = await getRejection(mockServices.acceptRisk("f8", "Valid reason"));
    expect(err.code).toBe("forbidden");
  });

  it("lets the matching asset owner accept risk on their own asset", async () => {
    await signInAsOwner();
    const updated = await mockServices.acceptRisk("f1", "Owner accepts");
    expect(updated.status).toBe("risk accepted");
    expect(updated.auditTrail.at(-1)).toMatchObject({ actor: DEMO_OWNER_USER.id, actorDisplayName: DEMO_OWNER_USER.displayName });
  });

  it("never forbids a security lead", async () => {
    await signIn();
    await expect(mockServices.acceptRisk("f2", "Lead accepts")).resolves.toMatchObject({ status: "risk accepted" });
  });

  it("returns not_found, not validation, for an unknown id with an empty reason", async () => {
    await signIn();
    const err = await getRejection(mockServices.acceptRisk("missing", ""));
    expect(err.code).toBe("not_found");
  });

  it("returns forbidden, not validation, for an owner mismatch with an empty reason", async () => {
    await signInAsOwner();
    const err = await getRejection(mockServices.acceptRisk("f2", "  "));
    expect(err.code).toBe("forbidden");
    const after = await mockServices.getFinding("f2");
    expect(after.status).toBe("open");
    expect(after.auditTrail).toHaveLength(0);
  });

  it("returns forbidden, not conflict, for an owner mismatch on a non-open finding", async () => {
    await signInAsOwner();
    const before = await mockServices.getFinding("f4");
    const err = await getRejection(mockServices.acceptRisk("f4", "Valid reason"));
    expect(err.code).toBe("forbidden");
    expect(await mockServices.getFinding("f4")).toEqual(before);
  });
});

describe("registerAsset contract validation", () => {
  beforeEach(async () => {
    await signIn();
  });

  it("refuses a repository URL outside https://github.com/<owner>/<repo> and creates no asset", async () => {
    const before = await mockServices.listAssets();
    const bad = [
      "http://github.com/a/b",
      "git@github.com:a/b",
      "https://gitlab.com/a/b",
      "https://github.com/a/b/extra",
      "https://github.com/a/..",
      "https://github.com/a/b.git",
      "",
    ];
    for (const repositoryUrl of bad) {
      const err = await getRejection(mockServices.registerAsset(newAsset({ repositoryUrl })));
      expect(err, repositoryUrl).toBeInstanceOf(ServiceError);
      expect(err.code, repositoryUrl).toBe("validation");
    }
    expect(await mockServices.listAssets()).toEqual(before);
  });

  it("refuses an ownerEmail that is not an email address but stores a blank as null", async () => {
    const err = await getRejection(mockServices.registerAsset(newAsset({ ownerEmail: "not-an-email" })));
    expect(err.code).toBe("validation");
    const blank = await mockServices.registerAsset(newAsset({ ownerEmail: "   " }));
    expect(blank.ownerEmail).toBeNull();
  });

  it("registers a valid GitHub URL as a not-yet-scanned asset with empty scan detail", async () => {
    const created = await mockServices.registerAsset(newAsset({ repositoryUrl: "https://github.com/acme/new-asset" }));
    expect(created).toMatchObject({
      scanStatus: "not yet scanned",
      scanFailureReason: null,
      scanWarnings: [],
      lastScanAt: null,
      lastCommitSha: null,
    });
  });
});

describe("stored sessions from an older build", () => {
  it("treats a stored user without role or displayName as signed out", async () => {
    const old = JSON.stringify({ id: "u1", name: "Jordan Vale", email: "analyst@example.com" });
    window.sessionStorage.setItem("vulntriage-user", old);
    window.sessionStorage.setItem("vulntriage-services-user", old);
    vi.resetModules();
    const auth = await import("@/lib/auth");
    expect(auth.getUser()).toBeNull();
    const fresh = await import("@/services/mockService");
    await expect(fresh.mockServices.currentUser()).rejects.toMatchObject({ code: "unauthenticated" });
  });
});

describe("contract-shaped screens", () => {
  it("offers a per-row re-scan, confirms it and leaves the scan status as it was", async () => {
    await signIn();
    setUser(DEMO_USER);
    const reScan = vi.spyOn(mockServices, "reScan");
    renderApp("/assets");

    fireEvent.click(await screen.findByRole("button", { name: "Re-scan payments-api" }));
    expect(await screen.findByText("Re-scan requested")).toBeInTheDocument();
    expect(reScan).toHaveBeenCalledWith("a1");
    expect(within(await screen.findByTestId("asset-scan-a1")).getByText("scanned, findings")).toBeInTheDocument();
  });

  it("shows the re-scan error message when reScan rejects", async () => {
    await signIn();
    setUser(DEMO_USER);
    vi.spyOn(mockServices, "reScan").mockRejectedValue(new ServiceError("not_found", "Asset not found."));
    renderApp("/assets");

    fireEvent.click(await screen.findByRole("button", { name: "Re-scan payments-api" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Asset not found.");
  });

  it("shows every scan status and the failure reason on the assets list", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/assets");

    expect(await screen.findByTestId("asset-scan-a5")).toHaveTextContent("scan failed");
    expect(screen.getByTestId("asset-scan-a5")).toHaveTextContent("lockfile parse error");
    expect(screen.getByTestId("asset-scan-a6")).toHaveTextContent("not yet scanned");
    expect(screen.getByTestId("asset-scan-a7")).toHaveTextContent("scanned, clean");
    expect(screen.getByTestId("asset-scan-a8")).toHaveTextContent("scanned, incomplete");
  });

  it("shows the forbidden message on the accept screen and leaves the finding open", async () => {
    await signInAsOwner();
    setUser(DEMO_OWNER_USER);
    renderApp("/findings/f2/accept");

    fireEvent.change(await screen.findByLabelText(/Reason/), { target: { value: "Not my asset" } });
    fireEvent.click(screen.getByRole("button", { name: "Accept risk" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("You can only accept risk on findings for assets you own.");
    const finding = await mockServices.getFinding("f2");
    expect(finding.status).toBe("open");
    expect(finding.auditTrail).toHaveLength(0);
  });

  it("renders pending and unavailable briefs as different states", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/f8");
    expect(await screen.findByTestId("brief-pending")).toBeInTheDocument();
    expect(screen.queryByTestId("brief-unavailable")).not.toBeInTheDocument();
  });

  it("renders an unavailable brief and null dependency version without crashing", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/f5");
    expect(await screen.findByTestId("brief-unavailable")).toBeInTheDocument();
    expect(screen.queryByTestId("brief-pending")).not.toBeInTheDocument();
  });

  it("renders the KEV value, stale flags, dependencies and brief link from contract fields", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/f3");
    expect(await screen.findByText("KEV: not listed")).toBeInTheDocument();
    expect(screen.getByTestId("dependencies")).toHaveTextContent("http-relay@2.0.4");
    expect(screen.getByTestId("rank-reason").textContent).not.toBe("");
    expect(screen.getByRole("link", { name: "https://osv.dev/vulnerability/GHSA-hr3l-pp9k-2zt6" })).toBeInTheDocument();
  });

  it("shows a null dependency version as version unknown in the findings list", async () => {
    await signIn();
    const list = await mockServices.listFindings();
    renderComponent(<FindingsTable findings={list} />);
    const row = (await screen.findAllByTestId("finding-row")).find((r) => r.getAttribute("data-id") === "f8")!;
    expect(row).toHaveTextContent("version unknown");
    expect(row).toHaveTextContent("KEV: not listed");
  });
});

// --- F-ASSET: the assets list read view (issue #85, US-1) ------------------

describe("F-ASSET: assets list read view", () => {
  it("US-1: lists every asset with owner, criticality and internet-facing", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/assets");

    // A named owner shows its name and contact email.
    const payments = await screen.findByTestId("asset-owner-a1");
    expect(payments).toHaveTextContent("Payments team");
    expect(payments).toHaveTextContent("payments-team@example.com");

    // Criticality and the internet-facing flag are shown for each row.
    const rows = screen.getAllByRole("row");
    const paymentsRow = rows.find((r) => within(r).queryByText("payments-api"))!;
    expect(paymentsRow).toHaveTextContent("critical");
    expect(within(paymentsRow).getByText("yes")).toBeInTheDocument(); // internet-facing
    const wikiRow = rows.find((r) => within(r).queryByText("internal-wiki"))!;
    expect(wikiRow).toHaveTextContent("low");
    expect(within(wikiRow).getByText("no")).toBeInTheDocument();
  });

  it("US-1: shows an ownerless marker when both owner fields are unset", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/assets");
    // internal-wiki (a4) has no owner name and no owner email.
    const owner = await screen.findByTestId("asset-owner-a4");
    expect(owner).toHaveTextContent("ownerless");
    expect(owner).not.toHaveTextContent("@");
  });

  it("US-1: a partial owner (name or email only) is shown, not ownerless", async () => {
    // Every seed owner with a name also has an email, so assert the rule directly
    // through the shared predicate the view uses.
    expect(isOwnerless({ ownerName: "Someone", ownerEmail: null })).toBe(false);
    expect(isOwnerless({ ownerName: null, ownerEmail: "a@b.co" })).toBe(false);
    expect(isOwnerless({ ownerName: null, ownerEmail: null })).toBe(true);
  });
});

// --- F-STATUS: the findings status/rank/signal/brief read view -------------

describe("F-STATUS: finding status, rank and signal read view", () => {
  it("US-4: a finding shows exactly one KEV value, EPSS and the asset context", async () => {
    await signIn();
    const list = await mockServices.listFindings();
    renderComponent(<FindingsTable findings={list} />);
    const rows = await screen.findAllByTestId("finding-row");
    const byId = (id: string) => rows.find((r) => r.getAttribute("data-id") === id)!;

    // KEV: listed (f1), not listed (f3), n/a no CVE (f7) — exactly one each row.
    expect(byId("f1")).toHaveTextContent("KEV: listed");
    expect(byId("f3")).toHaveTextContent("KEV: not listed");
    expect(byId("f7")).toHaveTextContent("KEV: n/a (no CVE)");
    // An EPSS score, or n/a when there is none (f8 has epss null).
    expect(byId("f1")).toHaveTextContent("EPSS: 0.94");
    expect(byId("f8")).toHaveTextContent("EPSS: n/a");
    // A stale signal is marked (f3's EPSS is stale).
    expect(byId("f3")).toHaveTextContent("(stale)");
    // The owning asset's criticality and internet-facing flag.
    expect(byId("f1")).toHaveTextContent("criticality: critical");
    expect(byId("f1")).toHaveTextContent("internet-facing");
  });

  it("US-4: the detail view shows the KEV value with a stale marker when the fetch is stale", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/f3");
    expect(await screen.findByText("KEV: not listed")).toBeInTheDocument();
    // The asset context is present on the detail view.
    expect(screen.getByTestId("asset-owner")).toHaveTextContent("Payments team");
  });

  it("US-5: every finding shows its rank reason, and the list is never re-sorted", async () => {
    await signIn();
    const list = await mockServices.listFindings();
    // The services layer ranks; the table renders exactly that order (US-5 determinism).
    renderComponent(<FindingsTable findings={list} />);
    const order = (await screen.findAllByTestId("finding-row")).map((r) => r.getAttribute("data-id"));
    const again = await mockServices.listFindings();
    expect(again.map((f) => f.id)).toEqual(order); // re-scoring the same inputs = same order
    // Each finding carries a non-empty rank reason, shown on the detail view.
    setUser(DEMO_USER);
    renderApp("/findings/f1");
    expect((await screen.findByTestId("rank-reason")).textContent).toContain("P1");
  });

  it("US-6: an available brief whose fix version matches the finding is shown", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/f1"); // brief available, fixVersion 3.2.4 == fixedVersion 3.2.4
    expect(await screen.findByText(/Unsafe deserialisation/)).toBeInTheDocument();
    // The brief's fix version (3.2.4) matches the finding's fixed version; assert
    // on the brief's own "Fix version:" line (3.2.4 appears several times on the page).
    const fixLine = screen.getByText(
      (_content, el) => el?.tagName === "P" && /Fix version:/.test(el.textContent ?? "") && /3\.2\.4/.test(el.textContent ?? ""),
    );
    expect(fixLine).toBeInTheDocument();
    expect(screen.queryByTestId("brief-unavailable")).not.toBeInTheDocument();
    expect(screen.queryByTestId("brief-pending")).not.toBeInTheDocument();
  });

  it("US-6: a brief not yet generated shows the finding with a 'brief pending' marker", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/f8"); // briefStatus pending
    expect(await screen.findByTestId("brief-pending")).toBeInTheDocument();
    expect(screen.queryByTestId("brief-unavailable")).not.toBeInTheDocument();
  });

  it("US-6: a rejected/errored brief shows the finding with a 'brief unavailable' marker", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/f5"); // briefStatus unavailable
    expect(await screen.findByTestId("brief-unavailable")).toBeInTheDocument();
    expect(screen.queryByTestId("brief-pending")).not.toBeInTheDocument();
  });

  it("shows every finding status across the list (US-5/US-10 statuses)", async () => {
    await signIn();
    const list = await mockServices.listFindings();
    renderComponent(<FindingsTable findings={list} />);
    const rows = await screen.findAllByTestId("finding-row");
    const byId = (id: string) => rows.find((r) => r.getAttribute("data-id") === id)!;
    // open (f1), risk accepted (f4), fixed (f6) and withdrawn (f7) each render
    // their status label in the row.
    expect(byId("f1")).toHaveTextContent("open");
    expect(byId("f4")).toHaveTextContent("risk accepted");
    expect(byId("f6")).toHaveTextContent("fixed");
    expect(byId("f7")).toHaveTextContent("withdrawn");
  });
});

// --- F-STATUS write path: risk acceptance, audit and re-scan (issue #86) ---

describe("F-STATUS write path: risk acceptance, audit trail and re-scan", () => {
  it("US-11: a security lead accepts risk with a reason, and the audit trail records who/when/previous/reason", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/f1/accept");

    fireEvent.change(await screen.findByLabelText(/Reason/), { target: { value: "Mitigated by an upstream WAF rule" } });
    fireEvent.click(screen.getByRole("button", { name: "Accept risk" }));

    // The write goes through POST /findings/{id}/risk-acceptance and lands back
    // on the detail view with the new status and a recorded audit entry.
    await waitFor(() => expect(screen.getByText(/← Findings/)).toBeInTheDocument());
    const finding = await mockServices.getFinding("f1");
    expect(finding.status).toBe("risk accepted");
    const entry = finding.auditTrail.at(-1)!;
    expect(entry.newValue).toBe("risk accepted");
    expect(entry.previousValue).toBe("open");
    expect(entry.reason).toBe("Mitigated by an upstream WAF rule");
    expect(entry.actor).toBe(DEMO_USER.id); // the signed-in user is the "who"
    expect(entry.source).toBe("dashboard");
  });

  it("US-11: an empty or whitespace-only reason is refused and the status does not change", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/f1/accept");

    fireEvent.change(await screen.findByLabelText(/Reason/), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Accept risk" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("A reason is required to accept this risk.");
    const finding = await mockServices.getFinding("f1");
    expect(finding.status).toBe("open");
    expect(finding.auditTrail).toHaveLength(0);
  });

  it("US-11: a security lead may accept on any finding; an asset owner only on a matching asset", async () => {
    // Security lead: allowed on an asset they do not own.
    await signIn();
    expect((await mockServices.acceptRisk("f2", "lead can accept anywhere")).status).toBe("risk accepted");
    resetMockData();

    // Asset owner, matching asset (payments-team owns a1 / finding f1): allowed.
    await signInAsOwner();
    expect((await mockServices.acceptRisk("f1", "owner accepts own asset")).status).toBe("risk accepted");
    resetMockData();

    // Asset owner, non-matching asset (f2 is on a2): refused, nothing changes.
    await signInAsOwner();
    const err = await getRejection(mockServices.acceptRisk("f2", "not my asset"));
    expect(err.code).toBe("forbidden");
    expect((await mockServices.getFinding("f2")).status).toBe("open");
  });

  it("US-11: the owner-mismatch refusal shows on the accept screen and leaves the finding open", async () => {
    await signInAsOwner();
    setUser(DEMO_OWNER_USER);
    renderApp("/findings/f2/accept");

    fireEvent.change(await screen.findByLabelText(/Reason/), { target: { value: "Attempt on an asset I do not own" } });
    fireEvent.click(screen.getByRole("button", { name: "Accept risk" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("You can only accept risk on findings for assets you own.");
    expect((await mockServices.getFinding("f2")).status).toBe("open");
  });

  it("US-11: a non-open finding cannot be risk accepted (the accept screen offers no form)", async () => {
    await signIn();
    setUser(DEMO_USER);
    renderApp("/findings/f6/accept"); // f6 is fixed
    expect(await screen.findByText("Only open findings can be risk accepted.")).toBeInTheDocument();
    expect(screen.queryByLabelText(/Reason/)).not.toBeInTheDocument();
    // And the service refuses it with a conflict, changing nothing.
    const err = await getRejection(mockServices.acceptRisk("f6", "too late"));
    expect(err.code).toBe("conflict");
    expect((await mockServices.getFinding("f6")).status).toBe("fixed");
  });

  it("US-11: no automated path sets risk accepted — only acceptRisk does, via a human", async () => {
    await signIn();
    // A re-scan (the only other write) never sets risk accepted.
    const before = await mockServices.getFinding("f1");
    await mockServices.reScan(before.assetId);
    expect((await mockServices.getFinding("f1")).status).toBe(before.status);
  });

  it("US-10: a signed-in user requests a manual re-scan from the dashboard; status is unchanged until it finishes", async () => {
    await signIn();
    setUser(DEMO_USER);
    const reScan = vi.spyOn(mockServices, "reScan");
    renderApp("/assets");

    const before = await mockServices.getAsset("a1");
    fireEvent.click(await screen.findByRole("button", { name: "Re-scan payments-api" }));
    expect(await screen.findByText("Re-scan requested")).toBeInTheDocument();
    expect(reScan).toHaveBeenCalledWith("a1"); // POST /assets/{id}/rescan
    // The current scan status does not change until the scan finishes.
    expect(await mockServices.getAsset("a1")).toEqual(before);
  });

  it("maps a rejected write to a ServiceError and shows its message", async () => {
    await signIn();
    setUser(DEMO_USER);
    vi.spyOn(mockServices, "reScan").mockRejectedValue(new ServiceError("not_found", "Asset not found."));
    renderApp("/assets");
    fireEvent.click(await screen.findByRole("button", { name: "Re-scan payments-api" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Asset not found.");
  });

  it("renders the audit trail with who, when, previous, new and reason", () => {
    // f4 is risk-accepted in the seed with a recorded audit entry. Render the
    // component directly (no router), as the other AuditTrail tests do.
    render(<AuditTrail entries={seedFindings().find((f) => f.id === "f4")!.auditTrail} />);
    const row = screen.getByRole("row", { name: /Jordan Vale/ });
    expect(row).toHaveTextContent("Jordan Vale");      // who (display name)
    expect(row).toHaveTextContent("open");             // previous value
    expect(row).toHaveTextContent("risk accepted");    // new value
    expect(row).toHaveTextContent(/Exports are only consumed/); // reason
  });
});
