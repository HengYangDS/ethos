---
subject: ethos:gate-runner
role: reference
state: canonical
relations:
  canonical_for: proof execution
---

# Gate Runner

ETHOS proof is an action graph plus evidence, not a shell-script alias.

`ethos quality gates --json` exposes the available gate registry. `ethos prove
--execute --gate self-audit --gate claims --json` executes selected gates through
the workspace runner and returns a digest-bound evidence set.

Default execute gates are intentionally local and deterministic: self audit,
claims, docs registry, and schema validation. Full verification can add tests,
Ruff, and package build gates without changing the proof contract.

Each gate declares a profile and toolchain. Product gates use the `product`
profile and the `ethos` toolchain. The current repository's test, lint, and
build gates use the `self-hosting` profile and `uv-python` toolchain so local
proof evidence can name the current tools without making those tools product
semantics.
