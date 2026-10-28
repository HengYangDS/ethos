# Proposal

## Why

The accepted requirement "Python reference observation respects binding and call site" is ahead of its owner. The observer still recognizes calls by spelling, and on accepted `dev` (`f699fa6cc`) it fails all four of its scenarios:

- `import subprocess as sp; sp.run([...])`, `from subprocess import run`, `import os as o; o.getenv(...)` and `os.environ[...]` are never observed, so an undeclared executable or input passes.
- A local or a parameter named `subprocess` invents an executable, and a module constant whose name ends in `COMMAND`, `CMD` or `TOOL` becomes a consumer even when nothing runs it.
- One file-wide constant table takes each name's last assignment, so `NAME = "A"; getenv(NAME); NAME = "B"` reads `B`, and a function's local `NAME` leaks into other scopes.
- `getattr(subprocess, name)(...)` is reported as evaluated.

The adopter counterexample that reached this owner (design revision 5.1, "Adopter counterexamples", row 2) has a second cause. A prewrite in alphasim was refused with `product_reference_not_admitted_at_baseline:value:ALPHASIMDMGR_IN_DOCKER_GATE`, although at its baseline (`03fc0661a`) `tools/ci/Dockerfile` declares `ENV ALPHASIMDMGR_IN_DOCKER_GATE=1` and `tools/ci/docker-compose.local-ci.yml` sets it in the service environment. The reference owner reads neither carrier. The archived proposal of `adopter-counterexample-repairs` called that refusal correct at its baseline; that statement was wrong, and this Change corrects it.

The observer also imports the product-boundary check (`repository.policy.boundary.product`), a verification-tier module, only to enumerate the product surface. That is one of the 35 violating tier edges of the design's map.

## What Changes

- **Bindings.** Python observation resolves each executor and environment read through the bindings that can hold at the call: imports and their aliases, assignments, parameters and definitions, with `global`, `nonlocal` and class bodies honoured. A binding holds after its statement; a read inside a loop sees every binding of its scope, and a nested scope sees all outer bindings.
- **Values at the call.** A name passed as the argv or the input name is followed to the literals that can reach the call. A parameter or a call result stays with its producer and invents nothing. A sink chosen by dynamic lookup makes its carrier UNKNOWN.
- **Heuristics removed.** Owner spelling and the `*_COMMAND`-name rule are deleted.
- **Container environment.** Dockerfile and Containerfile `ENV` and `ARG` names, and each Compose service's `environment`, own runtime values. A container build's `RUN` commands are not repository consumers.
- **Tier edge.** Product-surface enumeration moves from `repository/policy/boundary/` to `repository/policy/surfaces.py`, which both the boundary check and the observer read.
- **Specs.** repository-governance restates the binding requirement with its exact UNKNOWN boundary and adds the container environment requirement.
- **Documents.** The plan's convergence item and the semantics research note state the repaired observer.
- **CHANGELOG.** Entries under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: Python observation follows bindings with a bounded UNKNOWN; container environment declarations own runtime values.

## Impact

- One read-only diff against current checkouts:
  - ETHOS gains `PATH` (declared) and loses `python` and `nox`, which only the name rule produced. The proxy loses `python` and `pytest` the same way.
  - `ethos-introduction-film` gains one true consumer, `ffmpeg` in `src/container_metadata.py`, which no owner declares; its owner session was told on 2026-10-28.
  - No other governed repository changes, and none has a dynamic sink lookup.
  - The deferred families gain true consumers: alphasim `security`; di-effect `git`, `rsync` and GitLab's `CI`, `CI_MERGE_REQUEST_TITLE` and `CI_PIPELINE_SOURCE`. They lose `uv`, `pre-commit` and `repo`, which the name rule had seen only through first-party wrappers.
- The observer takes 1.2 to 1.3 s over ETHOS's 842 Python files, against 0.85 to 0.95 s before.
- `python_product` grows by about 125 effective lines. The product lane agreed that this Change lands after `surface-pruning` (−48) and is measured there.
- alphasim and di-effect are not changed. After a release carries this Change, their owners retry the refused prewrite. Task 10.11 of `quality-evidence-admission`, withdrawn by DR-0016, is restored here; its installed acceptance follows that release.
