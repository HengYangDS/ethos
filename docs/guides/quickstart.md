---
subject: docs:guides
role: how-to
state: active
relations:
  canonical_for: first run
---

# Quickstart

Status: active.

Purpose: give a first-run path for forming or binding a repository, inspecting
its state, and reading proof without confusing preview with mutation.

See also: [Command Plane](../reference/command-plane.md) and
[Product Design Contract](../governance/product-design-contract.md).

## Product Repository

From the repository checkout, begin with the bounded reader:

```bash
uv run ethos status --json
```

Read `required_gaps`, singular `next_action`, derived `continuation`,
`missing_facts_or_evidence`, and `user_decision_required` before changing
tracked files. The schema-version-`2` result preserves `state` and
`required_gaps`. A readiness result is not executed proof, landing,
publication, or remote push. Follow only the selected boundary, not a fixed
status/plan/prove pipeline. When `continuation=done`, the requested observation
is complete; do not repeat it or create work merely to obtain another action.

## New Repository

With an installed ETHOS executable, preview an absent target using a stable
purpose, the actual Git identity and the creator's SSH signer. Review the
returned plan digest before applying the same request:

```bash
ethos adopt --create --root <absent-repo> \
  --purpose "<purpose>" --starter foundation \
  --author-name "<name>" --author-email "<email>" \
  --signing-key <public-key> --trust-anchor <allowed-signers> --json
ethos adopt --create --root <absent-repo> \
  --purpose "<purpose>" --starter foundation \
  --author-name "<name>" --author-email "<email>" \
  --signing-key <public-key> --trust-anchor <allowed-signers> \
  --apply --authorize --expect-plan-digest <reviewed-digest> --json
ethos status --root <absent-repo> --json
```

`python-library` is an optional native starter in place of `foundation`.
Creation forms the initial Git repository, candidate worktree, bindings and
Agent entry from installed package bytes; it does not select domain intent.
ETHOS runs Git without global configuration, so the absolute public key and
protected allowed-signers file are explicit: they sign the initial commit and
stay in the new repository's local configuration. Add `--signing-program` when
signing uses a program other than `ssh-keygen`.
A later starter update is a reviewed candidate, never an automatic rewrite.
If creation reports an unknown post-effect result, inspect the target before
retrying. Author the first Change with official OpenSpec in an admitted lane.

## Existing Repository

Preview binding of an unadopted repository; do not mutate it from this example:

```bash
ethos adopt --root <repo> --json
```

The plan names the adopter profile and official OpenSpec config. Preserve the
existing repository layout and conflicting content; apply only the reviewed
plan, then observe status. Initial binding does not certify prior history or
prove scaffold, migration, uninstall, or crash recovery.

When current status selects verification, choose the required evidence depth:

```bash
ethos prove --root <repo> --json
ethos prove --root <repo> --execute --full --expect-head <exact-head> --json
```

These are alternative readiness and execution requests, not automatic steps.

## Native Source Formatting

`ethos lane format` prepares native postimages for authored source without writing.
Exact path arguments are literal repository-relative files, not glob patterns.
Without paths it selects tracked and non-ignored new authored source through the
common ownership policy; generated output, dependency locks, retained originals
and official OpenSpec carriers keep their separate owners.

```bash
ethos lane format docs/guide.md --root <worktree> --json
ethos lane format docs/guide.md --check --root <worktree> --json
ethos lane format docs/guide.md --apply --authorize --expect-head <head> --root <worktree> --json
```

Preview and check never write source bytes. Check refuses formatting drift; apply
requires current Work Lane admission of the complete patch, unchanged HEAD, index,
source bytes and modes, and matching written bytes. Prettier uses width 100 and
preserved prose wrapping; TOML uses native Taplo and Python uses Ruff. Repository
increments cannot replace the common policy or create competing fixed points.
Unavailable tools, malformed input and stale bindings remain explicit non-pass
results. This command formats source; `ethos prove` still owns complete quality
evidence, release semantics and acceptance.

The installed console honors the target repository's selected immutable runtime.
Invoking a newer console does not upgrade that selection or make an unsupported
command available. Installation and public consumer qualification are separate
from source tests.

## Before a Tracked Write

Work only in an admitted Work Lane. Bind the exact checkout and target paths
immediately before editing:

```bash
uv run ethos lane prewrite <paths> --editor-root <worktree> --require-editor-root --json
```

OpenSpec lifecycle operations remain official native-tool operations; use
`openspec validate --all --strict --json` when the change requires strict
workspace validation.
