# Design

## Context

See [proposal.md](proposal.md). `_native_hook_configuration` projects the repository's Gitleaks and
Ruff carriers, and their include closure, from the index or `HEAD` into a temporary directory.
`_check_staged_python_format` then returns without a check when that directory holds no Ruff
carrier. The `format_check` gate reads its policy through `native_configurations`, which always
includes the shipped Ruff policy and adds the repository's carrier as a separate check.

## Goals / Non-Goals

**Goals:**

- A repository that keeps no Ruff carrier gets its staged Python checked with the shipped settings.
- A repository that keeps one is checked exactly as before.

**Non-Goals:**

- Running the shipped policy beside a repository's own carrier. The paradigm already requires that
  carrier to keep the shipped settings, and the gate still checks both.
- Applying the format gate's ownership selection to staged paths, or changing secret scanning, which
  has no shipped policy.

## Decisions

- **The repository's carrier, else the shipped policy.** One policy per staged check keeps the hook
  to one Ruff run per path. Checking a commit that changes ETHOS's own Ruff settings against the
  installed runtime's older shipped copy as well would refuse that commit until the runtime moves.
- **One helper selects a shipped input.** `shipped_resource` in
  `src/ethos/repository/release/resources.py` returns the source's own file beside a source runner
  and otherwise the packaged file verified against the distribution's record, the selection that
  `native_configurations` already makes. The hook and `native_configurations` both call it, so a
  modified installed policy blocks the hook with `product_resource_integrity_invalid` instead of
  checking against altered settings.

## Risks / Trade-offs

- [Adopters without a carrier start getting a staged format check] → It refuses only Python that
  their `format_check` gate already refuses, and the repository's `fix` verb formats it.
