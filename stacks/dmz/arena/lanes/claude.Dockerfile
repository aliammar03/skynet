# The arena's Claude lane (skynetv2.md → D18): OpenAB's Claude image of the same build, whose Claude
# Code the lane runs, with Python and a few tools for the agents under test. doco-cd builds it on
# docker-dmz at each deploy (`docker compose up --build`; cached until this file changes).
FROM ghcr.io/openabdev/openab:nightly-20261103-41653922154.1-claude@sha256:992ebd27aeb653057353ea76bac0cce5189248e855777e160b2afb60a34c391b
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-venv jq sqlite3 \
    && rm -rf /var/lib/apt/lists/*
USER node
