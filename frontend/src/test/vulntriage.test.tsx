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
import { DEMO_CREDENTIALS, DEMO_USER, seedFindings } from "@/services/mockData";
import { mockServices, resetMockData, resetMockSession } from "@/services/mockService";
import type { FindingWithAsset, NewAssetInput } from "@/services/types";

function newAsset(overrides: Partial<NewAssetInput> = {}): NewAssetInput {
  return {
    name: "new-asset",
    ownerName: null,
    ownerEmail: null,
    criticality: "medium",
    internetFacing: false,
    repositoryUrl: "https://git.example.com/acme/new-asset",
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
    expect(assets.some((a) => a.scanStatus === "scan_error")).toBe(true);
    expect(assets.some((a) => a.scanStatus === "not_scanned")).toBe(true);
  });

  it("accepting risk sets the status and records an audit entry with the reason", async () => {
    const updated = await mockServices.acceptRisk("f1", "  Mitigated by WAF rule 42  ");
    expect(updated.status).toBe("risk_accepted");
    const entry = updated.auditTrail.at(-1)!;
    expect(entry).toMatchObject({ who: DEMO_USER.name, previousValue: "open", newValue: "risk_accepted", reason: "Mitigated by WAF rule 42" });
    expect((await mockServices.getFinding("f1")).status).toBe("risk_accepted");
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
    expect(accepted.auditTrail[0]).toMatchObject({ previousValue: "open", newValue: "risk_accepted" });
    expect((await mockServices.getFinding("f6")).auditTrail[0]).toMatchObject({ previousValue: "open", newValue: "fixed" });
    expect((await mockServices.getFinding("f7")).auditTrail[0]).toMatchObject({ previousValue: "open", newValue: "withdrawn" });

    const updated = await mockServices.acceptRisk("f1", "Mitigated");
    expect(updated.auditTrail.at(-1)).toMatchObject({ who: DEMO_USER.name, previousValue: "open", newValue: "risk_accepted" });
  });

  it("renders status wire values through STATUS_LABEL and leaves other fields unchanged", () => {
    render(
      <AuditTrail entries={[
        { id: "e1", who: "Jordan Vale", when: "2026-09-01T14:32:00Z", field: "status", previousValue: "open", newValue: "risk_accepted" },
        { id: "e2", who: "Jordan Vale", when: "2026-09-01T14:32:00Z", field: "reason", previousValue: "old text", newValue: "new text" },
      ]} />,
    );
    expect(screen.getByText("risk accepted")).toBeInTheDocument();
    expect(screen.queryByText("risk_accepted")).not.toBeInTheDocument();
    expect(screen.getByText("old text")).toBeInTheDocument();
    expect(screen.getByText("new text")).toBeInTheDocument();
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
