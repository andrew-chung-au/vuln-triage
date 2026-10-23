# Dev-container app image (issue #31, T3).
#
# A Compose-based dev container so Postgres can run as a sibling service the
# agent reaches by hostname but cannot control (no Docker socket). The app
# service is built from this image; the toolchain install stays in setup.sh
# (postCreateCommand), unchanged from the single-image recipe.
#
# Same base as the former `image:` line in devcontainer.json.
FROM mcr.microsoft.com/devcontainers/python:3.12
