// Explicit Vite config for the VulnTriage frontend (issue #21).
//
// This replaces the app builder's shared Vite preset. Every plugin the app
// needs is named here. Render mode (issue #21, human decision 2026-10-19):
// plain TanStack Router + Vite, a client-only SPA built to `frontend/dist/`.
import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsConfigPaths from "vite-tsconfig-paths";
import { tanstackRouter } from "@tanstack/router-plugin/vite";

export default defineConfig(({ mode }) => {
  // Make VITE_* values available to `import.meta.env` in client and server code
  // (Vite only exposes them to the client by default).
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const envDefine = Object.fromEntries(
    Object.entries(env).map(([key, value]) => [`import.meta.env.${key}`, JSON.stringify(value)]),
  );

  // In development the frontend and backend share one origin: the Vite dev
  // server proxies the API paths to the backend (task 11 / #133), so no CORS is
  // involved and the vt_session cookie is first-party. In Compose and on AWS a
  // reverse proxy does the same. The target is overridable with VITE_API_TARGET
  // for a non-default backend address.
  const apiTarget = env["VITE_API_TARGET"] || "http://127.0.0.1:8000";
  const apiPaths = ["/auth", "/findings", "/assets", "/signals", "/scans", "/health"];

  return {
    define: envDefine,
    css: { transformer: "lightningcss" },
    server: {
      proxy: Object.fromEntries(
        apiPaths.map((path) => [path, { target: apiTarget, changeOrigin: true }]),
      ),
    },
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
      dedupe: [
        "react",
        "react-dom",
        "react/jsx-runtime",
        "react/jsx-dev-runtime",
        "@tanstack/react-query",
        "@tanstack/query-core",
      ],
    },
    optimizeDeps: {
      include: [
        "react",
        "react-dom",
        "react-dom/client",
        "react/jsx-runtime",
        "react/jsx-dev-runtime",
      ],
      ignoreOutdatedRequests: true,
    },
    plugins: [
      tailwindcss(),
      tsConfigPaths({ projects: ["./tsconfig.json"] }),
      tanstackRouter({ target: "react", autoCodeSplitting: true }),
      react(),
    ],
  };
});
