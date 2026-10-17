# Linux ARM64 execution supply only; source and policy are read from the CI checkout.
FROM ghcr.io/astral-sh/uv:0.13.1-python3.14-trixie-slim@sha256:112f89760bd54b63c84d140151ea5f3d849278e54f6f939f2c40a57f3e33d895 AS base

ENV UV_CACHE_DIR=/opt/ethos-supply/uv-cache \
    NPM_CONFIG_CACHE=/opt/ethos-supply/npm-cache \
    ETHOS_CI_TOOL_CACHE_DIR=/opt/ethos-supply/tool-cache \
    MISE_DATA_DIR=/opt/ethos-supply/mise-data \
    MISE_CACHE_DIR=/opt/ethos-supply/mise-cache \
    UV_PYTHON_INSTALL_DIR=/opt/ethos-supply/python \
    UV_PYTHON_PREFERENCE=only-managed
WORKDIR /opt/ethos-supply

RUN apt-get update && apt-get install -y --no-install-recommends \
    git=1:2.47.3-0+deb13u1 openssh-client=1:10.0p1-7+deb13u4 \
    procps=2:4.0.4-9 lsof=4.99.4+dfsg-2 libatomic1=14.2.0-19 \
    curl=8.14.1-2+deb13u7 ca-certificates=20250419 \
    xz-utils=5.8.1-1+deb13u2 coreutils=9.7-3 \
    && rm -rf /var/lib/apt/lists/*

FROM base AS prepare

COPY .config/mise/config.toml .config/mise/mise.lock .config/mise/
COPY .config/checks/ci-projection/policy.toml .config/checks/ci-projection/policy.toml
COPY .config/ci/supply/Dockerfile .config/ci/supply/Dockerfile.dockerignore .config/ci/supply/
COPY tools/ci/scripts/with-python-runtime.sh tools/ci/scripts/mise-install.sh tools/ci/scripts/
COPY tools/ci/toolchain/native.py tools/ci/toolchain/native.py
# Full import closure is build-only; it is removed before publishing the image.
COPY src/ethos src/ethos
COPY pyproject.toml uv.lock package.json package-lock.json ./
COPY tests/fixtures/quality-sample/pyproject.toml tests/fixtures/quality-sample/uv.lock tests/fixtures/quality-sample/

# Build-only Python is removed; the final image binds lock inputs and is revalidated at use.
RUN uv python install --no-bin "$(python3 -c 'import platform; print(platform.python_version())')" \
    && uv sync --locked --no-install-project --group dev \
    && mkdir -p /tmp/ethos-quality-sample/src/sample \
    && cp tests/fixtures/quality-sample/pyproject.toml tests/fixtures/quality-sample/uv.lock /tmp/ethos-quality-sample/ \
    && touch /tmp/ethos-quality-sample/src/sample/__init__.py \
    && uv --directory /tmp/ethos-quality-sample sync --locked --group dev \
    && rm -rf /tmp/ethos-quality-sample \
    && native_paths="$(PYTHONPATH=src .venv/bin/python tools/ci/toolchain/native.py --root . --mise gitleaks scc syft vale)" \
    && PATH="$native_paths:$PATH" PYTHONPATH=src .venv/bin/python -c 'import subprocess; from pathlib import Path; from ethos.adapters.repo.runtime.materialization.node.supply import NodeRuntime, NodeSupply; root = Path.cwd(); runtime = NodeRuntime.read(NodeSupply.read(root).installed_root(root), windows=False); subprocess.run([str(runtime.executable), str(runtime.npm), "ci", "--ignore-scripts", "--no-audit", "--no-fund"], stdin=subprocess.DEVNULL, timeout=120, check=True)' \
    && sha256sum .config/checks/ci-projection/policy.toml \
         .config/mise/config.toml .config/mise/mise.lock \
         .config/ci/supply/Dockerfile .config/ci/supply/Dockerfile.dockerignore \
         uv.lock package-lock.json tests/fixtures/quality-sample/uv.lock \
         tools/ci/scripts/with-python-runtime.sh tools/ci/scripts/mise-install.sh \
         > input.sha256 \
    && chown -R 65534:65534 /opt/ethos-supply \
    && rm -rf .venv node_modules src/ethos tools/ci/toolchain tools/ci/scripts tests/fixtures/quality-sample

# Only prepared supply crosses the stage boundary; source-bearing layers are not shipped.
FROM base
COPY --from=prepare --chown=65534:65534 /opt/ethos-supply /opt/ethos-supply

LABEL org.opencontainers.image.source="https://github.com/HengYangDS/ethos"
