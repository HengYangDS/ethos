## Context

See [proposal.md](proposal.md). A read-only audit on 2026-10-13 compared the
accepted `4fa32c4b0` declarations with their native registries: `uv tree
--outdated` for Python, `npm outdated` for npm, `mise latest` for mise tools,
and the GitHub releases API for Actions, mise and uv.

## Goals / Non-Goals

**Goals:**

- Both locks hold the latest stable releases their declared ranges admit.

**Non-Goals:**

- Raising declared ranges or exact pins, or adopting pre-releases.
- Changing packages bundled inside npm, which follow the npm release.

## Decisions

Refresh with the native lock owners, `uv lock --upgrade` and `npm update
--package-lock-only`, rather than editing locks by hand, so each owner keeps
its resolution, integrity and marker semantics. The full repository proof then
re-runs the dependency audit and every gate against the refreshed locks.

## Risks / Trade-offs

- [A new release carries an advisory or behavior change] → The repository
  proof's dependency audit and test gates must pass before landing; a refusal
  keeps the accepted locks unchanged.
- [Releases keep arriving] → This Change refreshes to the releases available
  when it runs; it does not claim permanent currency.
