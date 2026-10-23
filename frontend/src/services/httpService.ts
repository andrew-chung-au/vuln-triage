// Real backend-backed implementation of the Services interface (task 11 / #133).
//
// Transport only: the backend returns the wire shapes defined in types.ts
// (which follow _docs/openapi.yaml), so no field remapping happens here.
//
// Contract (_docs/openapi.yaml, _docs/api.md):
// - Same origin as the dashboard (server base "/"). In dev the Vite server
//   proxies these paths to the backend; in Compose and on AWS a reverse proxy
//   does. So requests are relative and never carry an absolute origin.
// - cookieAuth: the vt_session cookie is sent with every request
//   (credentials: "include").
// - CSRF: every cookie-authenticated non-GET except login and logout sends
//   the header X-Requested-With: XMLHttpRequest (A30).
// - Errors: the backend renders { code, message }; each code maps to a
//   ServiceError code.
import { ServiceError } from "./types";
import type {
  Asset,
  FindingWithAsset,
  NewAssetInput,
  ServiceErrorCode,
  Services,
  User,
} from "./types";

const CSRF_HEADER = "X-Requested-With";
const CSRF_VALUE = "XMLHttpRequest";

// The API lives under /api on the same origin so the SPA can own `/`,
// `/findings` and `/assets` for client-side routing without colliding with the
// API. The reverse proxy (nginx in Compose, the Vite dev server in dev) routes
// /api/* to the backend and strips this prefix, so the backend still sees
// `/findings`, `/assets`, etc. Every per-call path below stays relative; this
// is the single place the prefix is applied.
const API_BASE = "/api";

const SERVICE_ERROR_CODES: ReadonlySet<string> = new Set<ServiceErrorCode>([
  "validation",
  "not_found",
  "conflict",
  "unauthenticated",
  "forbidden",
]);

/** The contract Error shape: { code, message }. */
interface WireError {
  code: string;
  message: string;
}

function isWireError(value: unknown): value is WireError {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return typeof record["code"] === "string" && typeof record["message"] === "string";
}

/** Map a non-2xx response to a ServiceError, reading the { code, message } body. */
async function toServiceError(response: Response): Promise<ServiceError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // No JSON body; fall through to a status-derived code.
  }
  if (isWireError(body) && SERVICE_ERROR_CODES.has(body.code)) {
    return new ServiceError(body.code as ServiceErrorCode, body.message);
  }
  // A response without a recognised { code, message } body (e.g. a proxy or
  // gateway error) still becomes a typed ServiceError so callers never see a
  // raw HTTP failure.
  const fallback: ServiceErrorCode =
    response.status === 401
      ? "unauthenticated"
      : response.status === 403
        ? "forbidden"
        : response.status === 404
          ? "not_found"
          : response.status === 409
            ? "conflict"
            : "validation";
  return new ServiceError(fallback, `Request failed (${response.status}).`);
}

type Method = "GET" | "POST" | "PATCH";

interface RequestOptions {
  method?: Method;
  body?: unknown;
  /** Login and logout are the only cookie non-GET operations without CSRF. */
  csrf?: boolean;
}

async function request(path: string, options: RequestOptions = {}): Promise<Response> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = {};
  const init: RequestInit = {
    method,
    // Send and accept the vt_session cookie on the same origin.
    credentials: "include",
    headers,
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }
  // CSRF header on every cookie non-GET except where csrf is explicitly false.
  if (method !== "GET" && options.csrf !== false) {
    headers[CSRF_HEADER] = CSRF_VALUE;
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch {
    // Network-level failure (backend down, proxy unreachable). Surface a typed
    // error rather than a raw TypeError.
    throw new ServiceError("validation", "Could not reach the server.");
  }
  if (!response.ok) {
    throw await toServiceError(response);
  }
  return response;
}

async function requestJson<T>(path: string, options?: RequestOptions): Promise<T> {
  const response = await request(path, options);
  return (await response.json()) as T;
}

export const httpServices: Services = {
  login(username, password) {
    // Login sets the cookie and is exempt from the CSRF header.
    return requestJson<User>("/auth/login", {
      method: "POST",
      body: { username, password },
      csrf: false,
    });
  },

  async logout() {
    // Logout is idempotent and exempt from the CSRF header; it returns 204.
    await request("/auth/logout", { method: "POST", csrf: false });
  },

  currentUser() {
    return requestJson<User>("/auth/me");
  },

  listFindings() {
    // The backend returns FindingWithAsset[] in server rank order; never re-sorted here.
    return requestJson<FindingWithAsset[]>("/findings");
  },

  getFinding(id) {
    return requestJson<FindingWithAsset>(`/findings/${encodeURIComponent(id)}`);
  },

  acceptRisk(id, reason) {
    return requestJson<FindingWithAsset>(
      `/findings/${encodeURIComponent(id)}/risk-acceptance`,
      { method: "POST", body: { reason } },
    );
  },

  listAssets() {
    return requestJson<Asset[]>("/assets");
  },

  getAsset(id) {
    return requestJson<Asset>(`/assets/${encodeURIComponent(id)}`);
  },

  registerAsset(input: NewAssetInput) {
    return requestJson<Asset>("/assets", { method: "POST", body: input });
  },

  async reScan(assetId) {
    // 202, no body.
    await request(`/assets/${encodeURIComponent(assetId)}/rescan`, { method: "POST" });
  },
};
