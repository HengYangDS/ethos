# Proposal

## Why

Since result schema 3 (0.2.0-beta.6) every result carries `next`, the typed form of `next_action`:
its `kind`, the exact ETHOS `argv` of a command, its effects and the authorization it needs. The
readers have not moved. The product Skill `ethos-repository-work`, the repository Skill
`ethos-repository-governance` and the quickstart tell agents to read the text `next_action`, and
four readers in the delivery acceptance tools split that text with `shlex` and run what they parsed.
A reader that parses prose or a template runs something no producer declared. The 2026-11-07 expert
committee's operation-catalog design (R10) moves every reader to `next` before the producers emit
typed steps.

## What Changes

- The two Skills and the quickstart read `next`: run `next.argv` only when `next.kind` is
  `command`, wait for the person on a `decision`, read an `instruction` as prose, and stop on
  `done`. `next_action` stays the human rendering.
- The delivery acceptance readers take a top-level continuation only from `next.argv`, through one
  helper that refuses a result without a typed step of the expected kind. Continuations nested in
  `data`, which have no typed form yet, keep their text until their producers type them.
- A test shows that the helper refuses a text-only continuation and returns the typed argv.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The result contract already defines `next`; `skip_specs: true` applies.

## Impact

- `src/ethos/resources/skills/ethos-repository-work/SKILL.md`,
  `.agents/skills/ethos-repository-governance/SKILL.md` and its package digest,
  `docs/guides/quickstart.md`.
- `tools/ci/delivery/acceptance/invocation.py`, `journey.py`, `lane.py` and `merge.py`, with their
  tests.
