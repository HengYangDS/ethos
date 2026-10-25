# Design

## Context

See [proposal.md](proposal.md).

- **How the build resolves offline.**
  - `uv run --locked --offline` installs the fixture project, so it builds it in an isolated environment.
  - The lock pins the runtime and development dependencies, but not `build-system.requires`.
  - Offline, uv resolves the build requirements against the cached index. It fails when the newest listed release of any of them has no cached wheel.
- **One shared cache.** Every uv command on the host shares the default uv cache. An online command refreshes index entries without downloading every listed release.
- **The bundled backend.** uv ships the `uv_build` backend inside its executable. Observed with uv 0.13.5 on 2026-10-25:
  - When the running uv satisfies the `uv_build` requirement, uv builds with the bundled backend, and an offline build from an empty cache succeeds.
  - A requirement that excludes the running uv falls back to the registry, and then fails offline the way hatchling does.
- **CI detection in mise.** Observed with mise 2026.10.19 on 2026-10-25:
  - `mise --cd <fresh root> trust --show` reports the root trusted while any CI marker is set, whatever its value, even `CI=false`.
  - The markers include `CI`, `CONTINUOUS_INTEGRATION`, `BUILD_NUMBER`, `RUN_ID`, `GITHUB_ACTIONS`, `GITLAB_CI`, `TF_BUILD`, `BUILDKITE` and `CIRCLECI`; `JENKINS_URL` alone is not one.
  - ETHOS asks native mise under the caller's own environment, so on a hosted runner the root is trusted and an untrusted case cannot refuse.

## Goals / Non-Goals

**Goals:**

- Offline fixture builds depend only on the locked fixture supply and the uv that runs them.
- The trust regressions for an untrusted configuration give the same verdict on a developer host and on a hosted runner.

**Non-Goals:**

- Changing how ETHOS builds itself, or how the Python quality gate treats adopters' build backends.
- Changing the fixture's dependencies or its lock.
- Changing resolution: native mise's CI policy stays one of the caller's trust inputs.

## Decisions

- **`uv_build` instead of warming.** Warming the cache would only move the race, because a later index refresh can still list a release that nobody downloaded. With the bundled backend there is no build requirement to resolve.
- **One requirement that every supported uv satisfies.**
  - The fixture runs under ETHOS's locked uv. In the relocated-mise case it runs under the operator's uv on `PATH`.
  - `uv_build>=0.13,<1` keeps both on the bundled backend across minor releases, so a host uv update cannot bring a download back.
- **The module keeps its name.** `[tool.uv.build-backend] module-name = "sample"` keeps `src/sample`, and the hatch target section goes away.
- **The regression is an offline build from an empty cache.**
  - It builds every tracked fixture project with ETHOS's locked uv, under `--offline`, `--no-config` and an empty `UV_CACHE_DIR`.
  - Any backend that needs a download fails it.
- **Hide the hosts' markers, then require the native precondition.**
  - `tests/support/mise_host.outside_ci` removes the generic markers and those of the hosts that run these tests: GitHub, GitLab and Azure.
  - It then requires `trust --show` to report the root untrusted.
  - A complete vendor list would copy mise's detection into ETHOS. The native check covers any marker it misses, and fails with a message that names the cause.

## Risks / Trade-offs

- [A future uv 1.0 falls outside the range] → The regression fails at that supply refresh, before any offline proof.
- [A host sets a CI marker that the helper does not hide] → The native precondition fails and names the cause, instead of a regression passing or failing for the wrong reason.
- [`uv_build` lays out the editable install differently from hatchling] → Before landing, the fixture tests that import `sample` and measure its coverage run on the new backend.
