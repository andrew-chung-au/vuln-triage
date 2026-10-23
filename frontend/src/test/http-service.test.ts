// Real backend-backed service transport (task 11 / #133).
//
// Verifies the contract wiring with a stubbed fetch: every request sends the
// vt_session cookie (credentials: "include"), cookie non-GET operations send
// the CSRF header X-Requested-With except login and logout, and the backend's
// { code, message } error body maps to a typed ServiceError (403 -> forbidden).
import { afterEach, describe, expect, it, vi } from "vitest";
import { httpServices } from "@/services/httpService";
import { ServiceError } from "@/services/types";

interface Captured {
  url: string;
  init: RequestInit;
}

function stubFetch(responder: () => Response): Captured[] {
  const calls: Captured[] = [];
  vi.stubGlobal("fetch", (url: string, init: RequestInit = {}) => {
    calls.push({ url, init });
    return Promise.resolve(responder());
  });
  return calls;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function headerValue(init: RequestInit, name: string): string | undefined {
  const headers = (init.headers ?? {}) as Record<string, string>;
  return headers[name];
}

const DEMO_USER = {
  id: "u1",
  username: "lead",
  displayName: "Lead",
  email: "lead@example.com",
  role: "security lead" as const,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("httpServices transport", () => {
  it("sends the session cookie on every request", async () => {
    const calls = stubFetch(() => jsonResponse([]));
    await httpServices.listAssets();
    expect(calls[0].url).toBe("/assets");
    expect(calls[0].init.credentials).toBe("include");
  });

  it("sends the CSRF header on a cookie non-GET write", async () => {
    const calls = stubFetch(() => jsonResponse(DEMO_USER));
    await httpServices.acceptRisk("f1", "Mitigated by WAF");
    expect(calls[0].url).toBe("/findings/f1/risk-acceptance");
    expect(calls[0].init.method).toBe("POST");
    expect(headerValue(calls[0].init, "X-Requested-With")).toBe("XMLHttpRequest");
    expect(calls[0].init.credentials).toBe("include");
  });

  it("omits the CSRF header on login and logout", async () => {
    const loginCalls = stubFetch(() => jsonResponse(DEMO_USER));
    await httpServices.login("lead", "pw");
    expect(loginCalls[0].init.method).toBe("POST");
    expect(headerValue(loginCalls[0].init, "X-Requested-With")).toBeUndefined();
    vi.unstubAllGlobals();

    const logoutCalls = stubFetch(() => new Response(null, { status: 204 }));
    await httpServices.logout();
    expect(headerValue(logoutCalls[0].init, "X-Requested-With")).toBeUndefined();
  });

  it("maps a 403 body to a forbidden ServiceError", async () => {
    stubFetch(() => jsonResponse({ code: "forbidden", message: "Not allowed." }, 403));
    const err = await httpServices.acceptRisk("f1", "reason").catch((e) => e);
    expect(err).toBeInstanceOf(ServiceError);
    expect((err as ServiceError).code).toBe("forbidden");
    expect((err as ServiceError).message).toBe("Not allowed.");
  });

  it("maps a 403 with no recognised body to forbidden by status", async () => {
    stubFetch(() => new Response("gateway denied", { status: 403 }));
    const err = await httpServices.listAssets().catch((e) => e);
    expect(err).toBeInstanceOf(ServiceError);
    expect((err as ServiceError).code).toBe("forbidden");
  });

  it("surfaces a network failure as a typed ServiceError", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("Failed to fetch")));
    const err = await httpServices.currentUser().catch((e) => e);
    expect(err).toBeInstanceOf(ServiceError);
  });
});
