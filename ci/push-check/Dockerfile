# Push-check image for VulnTriage (issue #112, follow-up to #32 and #74).
#
# Used through AGENT_PUSH_CHECK_IMAGE by the clean clone's pre-push script, which
# runs `make -C . install verify` inside a throwaway container from this image.
# Build:  docker build -t vulntriage-push-check:1 ci/push-check
# Use:    export AGENT_PUSH_CHECK_IMAGE=vulntriage-push-check:1
#
# Pinned versions (keep in step with #20, .github/workflows/verify.yml and the
# dev container; rebuild the image whenever any of them changes):
#   Node.js               24.22.0   (base image tag)
#   npm                   11.19.1   (installed below; the bundled npm may differ)
#   uv                    0.13.1    (same as verify.yml)
#   Python                3.12.15   (backend/pyproject.toml: requires-python >=3.12)
#   openapi-spec-validator 0.9.0    (Makefile openapi-validate; cache baked in)
#   pip-audit             2.10.1    (S2 security-scan; no use in verify yet)
#   Terraform             1.17.0    (S3 task 17; fmt and validate only, no use yet)
#   libpq-dev / libpq5    Debian bookworm package versions (S2 Postgres driver)
#
# This image holds no credentials, no AWS configuration and no Terraform backend,
# and it never uses the Docker socket. pre-push mounts only the read-only bundle.
# Not included on purpose: Docker/Compose, Postgres server, browsers, AWS CLI,
# linters (see issue #112, table c).
#
# VERIFY: every version below until the human has built the image and reported
# the `docker run --rm <tag> <tool> --version` output listed in issue #112.

# VERIFY: Docker Hub showed multi-arch digest
# sha256:925de64a85319052d6971ae81ef2417da956e8a3a2c4a0fac732327970f017f5 for this
# tag on 2026-10-23; add `@sha256:...` here if you want the base pinned by digest.
FROM node:24.22.0-bookworm

# Needed by `uv sync --locked`: never download another Python at push time, use
# only the Python baked in below. A pyproject asking for a newer Python then
# fails the install instead of passing.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_CACHE_DIR=/opt/uv-cache \
    UV_TOOL_DIR=/opt/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_LINK_MODE=copy

# Reason: libpq-dev (+ libpq5) lets a Postgres driver without a prebuilt wheel
# build in S2 (tasks 15-16); no server is installed. unzip is needed for the
# Terraform archive. git, make, bash, gcc and coreutils come from buildpack-deps
# (VERIFY in the built image).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev libpq5 unzip \
    && rm -rf /var/lib/apt/lists/*

# npm pinned (VERIFY: the npm bundled in node:24.22.0-bookworm may already be 11.19.1).
RUN npm install -g npm@11.19.1 \
    && npm cache clean --force

# uv 0.13.1 from the official Astral image, pinned by tag.
# VERIFY: ghcr.io/astral-sh/uv:0.13.1 exists; if not, use the 0.13.1 release
# tarball from github.com/astral-sh/uv with its published .sha256 file.
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/

# Python 3.12.15 (VERIFY: current 3.12 patch; uv verifies the archive hash from
# its own metadata). Downloads are allowed only for this one build step.
RUN UV_PYTHON_DOWNLOADS=automatic uv python install 3.12.15 \
    && ln -s "$(uv python find 3.12.15)" /usr/local/bin/python3.12

# Tools installed with exact versions into their own environments, and the uv
# cache kept in /opt/uv-cache so `uvx openapi-spec-validator==0.9.0` works from
# the cache (VERIFY: it still exits 0 with `--network none`).
RUN uv tool install pip-audit==2.10.1 \
    && uvx openapi-spec-validator==0.9.0 --help > /dev/null

# Terraform 1.17.0: fmt and validate only. SHA-256 values are from
# https://releases.hashicorp.com/terraform/1.17.0/terraform_1.17.0_SHA256SUMS
# (VERIFY: version, and re-check the sums when bumping).
ARG TARGETARCH
RUN case "$TARGETARCH" in \
      amd64) tf_sha=c168cab7c637a8769fdb90089ddd19de701bc6ff8aca64dc2e2185fe46f59f67 ;; \
      arm64) tf_sha=f32478134ffc6d710eec474bbd316652cdddc0f4e336973a3745e8d3a3309cdf ;; \
      *) echo "unsupported arch: $TARGETARCH" >&2; exit 1 ;; \
    esac \
    && curl -fsSLo /tmp/terraform.zip "https://releases.hashicorp.com/terraform/1.17.0/terraform_1.17.0_linux_${TARGETARCH}.zip" \
    && echo "${tf_sha}  /tmp/terraform.zip" | sha256sum -c - \
    && unzip -q /tmp/terraform.zip terraform -d /usr/local/bin \
    && rm /tmp/terraform.zip
