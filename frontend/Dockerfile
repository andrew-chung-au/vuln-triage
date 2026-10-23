# Frontend image (issue #137, task 15): multi-stage, non-root.
#
# Stage 1 builds the SPA with the pinned Node version; stage 2 serves the built
# dist/ with nginx and proxies the API paths to the backend, so the browser
# sees one origin (as task 11's real Services assumes). nginx runs unprivileged
# (the nginx-unprivileged image listens on 8080 as a non-root user).

# --- build stage -----------------------------------------------------------
FROM node:24.22.0-bookworm-slim AS build

WORKDIR /app

# Install from the lockfile first (cached layer).
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- runtime stage ---------------------------------------------------------
# Unprivileged nginx: runs as a non-root user and listens on 8080.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

# Replace the default server block with the SPA + API-proxy config.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# The built SPA.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
