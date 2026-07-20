## Context

`status` and `orient` are bounded readers by default. Their coordination payload
may legitimately report `detail_state=deferred` when foreign Work Lane path
scopes are not inspected. A full or isolated observation may instead report
`detail_state=exact`. The hosted proof failure came from a test fixture that
encoded the first valid mode as the only valid mode.

## Goals / Non-Goals

**Goals:**

- Preserve the existing vendor-neutral Work Lane coordination model.
- Make product tests validate the relationship between summary and observed
  coordination payload rather than a repository-shape-specific value.
- Cover an exact-detail isolated repository observation.

**Non-Goals:**

- Changing lease authority, handoff, retirement, or foreign-lane permissions.
- Adding provider, forge, runner, or Codex-specific branches.
- Making bounded readers enumerate foreign Work Lane details.

## Decisions

- Treat `detail_state` as an observed read-model value. Tests assert equality
  between projections and then assert the nullability contract for dependent
  detail counts.
- Add an isolated repository test with no foreign Work Lanes; it proves that
  `exact` is a valid output without depending on this repository's mutable
  worktree inventory.
- Modify the existing repository-governance requirement rather than introducing
  a provider-specific capability because the contract already owns bounded and
  exact coordination observations.

## Risks / Trade-offs

- [A dynamic assertion could weaken coverage] -> The isolated exact-state test
  retains a concrete assertion, while projection tests retain their equality and
  nullability checks.
- [The live repository can change during test runs] -> The tests do not derive
  a fixed state from host inventory; only the actual payload supplies the state.
