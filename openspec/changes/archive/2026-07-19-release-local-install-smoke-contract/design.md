## Context

Publication topology already names the local verification and installation
commands. Those names are release-policy claims, so a string alone is
insufficient: the declared owner must resolve to an executable tracked surface
inside the governed repository. The execution owner must then prove that built
packages install and run without importing the source checkout.

## Design

### Fail-closed command admission

`release_policy_report` validates the `publication_topology.local` command
fields. Each command must be a non-empty repository-relative path. Its resolved
path must remain under the repository root, exist as a regular file, and have
an executable bit. Failures use stable gap families for missing declarations,
path escape, missing/non-regular files, and non-executable files. Release policy
cannot remain ready while a declared owner is phantom or unusable.

### One local-install owner

`tools/ci/scripts/run-local-install-smoke.sh` is the sole execution owner. It
enters through the checkout-bound Python runtime, captures the current HEAD,
rebuilds workspace wheels under `build/artifacts/python/`, and creates a fresh
virtual environment under
`build/runtime/work/local-install-smoke/venv/`. Wheel installation runs with
network access disabled. The verification step runs outside the source tree,
requires both `ethos` and `ethos_core` origins to live under the fresh virtual
environment, and executes the installed `ethos --help` and `ethos --version`.

All disposable runtime state stays under
`build/runtime/work/local-install-smoke/**`. The durable local receipt is
`build/evidence/local-install/smoke.json`; it records the exact HEAD, wheel
digests, module origins, commands, and negative hosted/remote claims. An exit
trap rejects the receipt if HEAD changes during execution.

### Gate composition

Local CI invokes the owner before writing its fallback manifest. The tool
catalog declares one active release concern. The gate registry declares one
trust-bearing, file-writing, offline `local-install-smoke` package gate in
`product_full`, after and dependent on `build`. Default proof remains compact;
only `prove --full --execute` establishes execution of this gate.

## Alternatives

- Keep the topology string as documentation only: rejected because it already
  participates in release readiness and currently permits false-ready output.
- Put the command in a second `.ethos/release.toml` local block: rejected because
  compact topology already has one source owner and duplication would create
  drift.
- Install from the source workspace or reuse the development environment:
  rejected because either can hide missing wheel content and import leakage.
- Require hosted or registry delivery for this smoke: rejected because local
  installability, remote publication, hosted CI, and registry delivery are
  distinct evidence planes.

## Proof Strategy

1. RED release-policy tests for missing, non-executable, and escaping owners.
2. RED architecture tests for executable ownership, isolated paths, offline
   install, stable-HEAD evidence, package origins, CLI surfaces, and local-CI
   composition.
3. Focused tests plus a real owner-script execution.
4. Config, shell, release-policy, claims, lifecycle, parity, default proof, and
   full proof on stable committed HEADs.
5. Official archive, candidate land, accepted closeout, local readiness,
   separately authorized remote publication, exact-SHA hosted observation, and
   lane retirement remain distinct transitions.
