# Linux ARM64 execution supply only; source and policy are read from the CI checkout.
FROM ghcr.io/astral-sh/uv:0.12.16-python3.14-trixie-slim@sha256:768543c09cfe47d3d08c3cbfffadead2029a96d19c3c05285c8b6c6f637aa3a8

ENV UV_CACHE_DIR=/opt/ethos-supply/uv-cache \
    NPM_CONFIG_CACHE=/opt/ethos-supply/npm-cache \
    ETHOS_CI_TOOL_CACHE_DIR=/opt/ethos-supply/tool-cache \
    UV_PYTHON_INSTALL_DIR=/opt/ethos-supply/python \
    UV_PYTHON_PREFERENCE=only-managed
WORKDIR /opt/ethos-supply

COPY .config/checks/node/runtime.toml .config/checks/node/runtime.toml
COPY tools/ci/scripts/install-node.sh tools/ci/scripts/download-file.sh \
    tools/ci/scripts/with-python-runtime.sh tools/ci/scripts/
COPY pyproject.toml uv.lock VERSION README.md package.json package-lock.json ./
COPY distributions/npm/package.json distributions/npm/package.json

RUN apt-get update && apt-get install -y --no-install-recommends \
    git openssh-client procps lsof libatomic1 curl ca-certificates xz-utils coreutils \
    && rm -rf /var/lib/apt/lists/*

RUN for version in $(python3 -c 'import tomllib; print(" ".join(tomllib.load(open(".config/checks/node/runtime.toml", "rb"))["compatibility_versions"]))'); do \
      NODE_VERSION="$version" tools/ci/scripts/install-node.sh; \
    done
RUN uv python install --no-bin "$(python3 -c 'import platform; print(platform.python_version())')" \
    && uv sync --locked --no-install-project --group dev \
    && npm ci --ignore-scripts \
    && sha256sum .config/checks/node/runtime.toml pyproject.toml uv.lock \
         package.json package-lock.json > input.sha256 \
    && chown -R 65534:65534 /opt/ethos-supply \
    && rm -rf .venv node_modules

LABEL org.opencontainers.image.source="https://github.com/HengYangDS/ethos"
