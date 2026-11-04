# The arena's Codex lane (skynetv2.md → D18): OpenAB's image of the comics agent's build, whose Codex
# CLI the lane runs, with Python and a few tools for the agents under test. doco-cd builds it on
# docker-dmz at each deploy (`docker compose up --build`; cached until this file changes).
FROM ghcr.io/openabdev/openab:nightly-20261103-41653922154.1-codex@sha256:52b5afb9b369dbc92e72b7e713e05f2cdf3f135c73367a17ce8b91dc2dc8ff16
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-venv jq sqlite3 \
    && rm -rf /var/lib/apt/lists/*
USER node
