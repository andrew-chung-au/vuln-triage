import { render, screen, within } from "@testing-library/react";
import { createMemoryHistory, createRootRoute, createRouter, RouterProvider } from "@tanstack/react-router";
import { beforeEach, describe, expect, it } from "vitest";
import { AffectedRanges } from "@/components/vt/AffectedRanges";
import { FindingsTable } from "@/components/vt/FindingsTable";
import { validateRiskReason } from "@/lib/validation";
import { DEMO_USER, seedFindings } from "@/services/mockData";
import { mockServices, resetMockData } from "@/services/mockService";
import type { FindingWithAsset } from "@/services/types";

beforeEach(() => resetMockData());

async function renderWithRouter(ui: React.ReactNode) {
  const router = createRouter({
    routeTree: createRootRoute({ component: () => <>{ui}</> }),
    history: createMemoryHistory({ initialEntries: ["/"] }),
  });
  render(<RouterProvider router={router} />);
  await screen.findByText(/Tier/);
}

describe("dashboard ordering", () => {
  it("shows findings in the exact order returned by the services layer, with tiers", async () => {
    const list = await mockServices.listFindings();
    const shuffled: FindingWithAsset[] = [list[3]!, list[0]!, list[7]!, list[1]!];
    await renderWithRouter(<FindingsTable findings={shuffled} />);
    const rows = screen.getAllByTestId("finding-row");
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
    for (const r of ["", "   "]) {
      await expect(mockServices.acceptRisk("f1", r, DEMO_USER)).rejects.toThrow();
    }
    const f = await mockServices.getFinding("f1");
    expect(f?.status).toBe("open");
    expect(f?.auditTrail).toHaveLength(0);
  });
});

describe("mock services", () => {
  it("returns all mock findings ranked by tier then EPSS (n/a last)", async () => {
    const list = await mockServices.listFindings();
    expect(list).toHaveLength(seedFindings().length);
    expect(list.map((f) => f.id)).toEqual(["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8"]);
    expect(list.map((f) => f.tier)).toEqual(["P1", "P1", "P2", "P2", "P3", "P3", "P4", "P4"]);
  });

  it("returns mock assets including ownerless, scan error and not-yet-scanned", async () => {
    const assets = await mockServices.listAssets();
    expect(assets.some((a) => a.owner === null)).toBe(true);
    expect(assets.some((a) => a.scanStatus === "scan_error")).toBe(true);
    expect(assets.some((a) => a.scanStatus === "not_scanned")).toBe(true);
  });

  it("accepting risk sets the status and records an audit entry with the reason", async () => {
    const updated = await mockServices.acceptRisk("f1", "  Mitigated by WAF rule 42  ", DEMO_USER);
    expect(updated.status).toBe("risk_accepted");
    const entry = updated.auditTrail.at(-1)!;
    expect(entry).toMatchObject({ who: DEMO_USER.name, previousValue: "open", newValue: "risk accepted", reason: "Mitigated by WAF rule 42" });
    expect((await mockServices.getFinding("f1"))?.status).toBe("risk_accepted");
  });

  it("rejects wrong credentials", async () => {
    await expect(mockServices.login("analyst@example.com", "nope")).rejects.toThrow();
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
