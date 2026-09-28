# Linux ARM64 execution supply only; source and policy are read from the CI checkout.
FROM ghcr.io/astral-sh/uv:0.12.16-python3.14-trixie-slim@sha256:768543c09cfe47d3d08c3cbfffadead2029a96d19c3c05285c8b6c6f637aa3a8

ENV UV_CACHE_DIR=/opt/ethos-supply/uv-cache \
    NPM_CONFIG_CACHE=/opt/ethos-supply/npm-cache \
    ETHOS_CI_TOOL_CACHE_DIR=/opt/ethos-supply/tool-cache \
    MISE_DATA_DIR=/opt/ethos-supply/mise-data \
    MISE_CACHE_DIR=/opt/ethos-supply/mise-cache \
    UV_PYTHON_INSTALL_DIR=/opt/ethos-supply/python \
    UV_PYTHON_PREFERENCE=only-managed
WORKDIR /opt/ethos-supply

COPY .config/checks/node/runtime.toml .config/checks/node/runtime.toml
COPY .config/mise/config.toml .config/mise/mise.lock .config/mise/
COPY .config/checks/ci/templates.toml .config/checks/ci/templates.toml
COPY .config/ci/supply/Dockerfile .config/ci/supply/Dockerfile.dockerignore .config/ci/supply/
COPY tools/ci/scripts/install-node.sh tools/ci/scripts/download-file.sh \
    tools/ci/scripts/with-python-runtime.sh tools/ci/scripts/mise-install.sh tools/ci/scripts/
COPY tools/ci/toolchain/native.py tools/ci/toolchain/native.py
COPY src/ethos/__init__.py src/ethos/__init__.py
COPY src/ethos/adapters/__init__.py src/ethos/adapters/process.py src/ethos/adapters/
COPY src/ethos/adapters/toolchain/__init__.py src/ethos/adapters/toolchain/mise.py src/ethos/adapters/toolchain/
COPY pyproject.toml uv.lock package.json package-lock.json ./
COPY distributions/npm/package.json distributions/npm/package.json
COPY tests/fixtures/quality-sample/pyproject.toml tests/fixtures/quality-sample/uv.lock tests/fixtures/quality-sample/

RUN apt-get update && apt-get install -y --no-install-recommends \
    git=1:2.47.3-0+deb13u1 openssh-client=1:10.0p1-7+deb13u4 \
    procps=2:4.0.4-9 lsof=4.99.4+dfsg-2 libatomic1=14.2.0-19 \
    curl=8.14.1-2+deb13u5 ca-certificates=20250419 \
    xz-utils=5.8.1-1+deb13u1 coreutils=9.7-3 \
    && rm -rf /var/lib/apt/lists/*

RUN for version in $(python3 -c 'import tomllib; print(" ".join(tomllib.load(open(".config/checks/node/runtime.toml", "rb"))["compatibility_versions"]))'); do \
      NODE_VERSION="$version" tools/ci/scripts/install-node.sh; \
    done
# Build-only Python is removed; the final image binds lock inputs and is revalidated at use.
RUN uv python install --no-bin "$(python3 -c 'import platform; print(platform.python_version())')" \
    && uv sync --locked --no-install-project --group dev \
    && mkdir -p /tmp/ethos-quality-sample/src/sample \
    && cp tests/fixtures/quality-sample/pyproject.toml tests/fixtures/quality-sample/uv.lock /tmp/ethos-quality-sample/ \
    && touch /tmp/ethos-quality-sample/src/sample/__init__.py \
    && uv --directory /tmp/ethos-quality-sample sync --no-config --locked --group dev \
    && rm -rf /tmp/ethos-quality-sample \
    && npm ci --ignore-scripts \
    && PYTHONPATH=src .venv/bin/python tools/ci/toolchain/native.py --root . --mise gitleaks scc syft \
    && sha256sum .config/checks/node/runtime.toml .config/checks/ci/templates.toml \
         .config/mise/config.toml \
         .config/mise/mise.lock .config/ci/supply/Dockerfile \
         .config/ci/supply/Dockerfile.dockerignore pyproject.toml uv.lock \
         package.json package-lock.json distributions/npm/package.json \
         tests/fixtures/quality-sample/pyproject.toml tests/fixtures/quality-sample/uv.lock \
         tools/ci/scripts/install-node.sh tools/ci/scripts/download-file.sh \
         tools/ci/scripts/with-python-runtime.sh tools/ci/scripts/mise-install.sh \
         > input.sha256 \
    && chown -R 65534:65534 /opt/ethos-supply \
    && rm -rf .venv node_modules src/ethos tools/ci/toolchain tools/ci/scripts tests/fixtures/quality-sample

LABEL org.opencontainers.image.source="https://github.com/HengYangDS/ethos"
