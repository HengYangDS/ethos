# Design

## Context

- The owner's decision of 2026-11-12: OpenSpec 2.0 in ETHOS and every governed repository, before
  the 24-hour age, with breaking changes allowed. OpenSpec 2.0.0 was published at
  2026-11-11T22:41:44Z (GitHub releases API), and the lock records the integrity that the npm
  registry publishes for it.
- ETHOS embeds OpenSpec as an npm dependency and loads nine of its internal modules through two
  Node bridges (`adapters/openspec/batch.mjs:21-23`, `adapters/openspec/configuration.mjs:13-22`).
  Comparing the 1.17.0 and 2.0.0 packages byte for byte, eight are identical;
  `utils/task-progress.js` now joins a wrapped task's continuation lines into its description.
  ETHOS parses task lines one at a time (`adapters/openspec/relocation.mjs:136-137`) and counts
  them, so neither result changes.
- 2.0.0's dependency ranges equal 1.17.0's.
- OpenSpec 2.0 records the tools it set up, and the `openspec-*` skills it must keep as the user's,
  in `.agents/skills/.openspec-target`, and decides ownership only from that record
  (`dist/core/shared-skill-target.d.ts`: "guessing from skill wording never decides whose a skill
  is").
- ETHOS's portfolio reports each unrouted `*/SKILL.md` under the Skills root
  (`assistants/skills/portfolio.py:132-151`).

## Goals / Non-Goals

Goals:

- ETHOS runs OpenSpec 2.0.0 everywhere it runs OpenSpec, and verifies that version as it does now.
- A repository may let OpenSpec 2.0 install its skills in `.agents/skills/` without an ETHOS
  activation record for each of them.

Non-Goals:

- ETHOS does not install or update OpenSpec's tool files; `openspec init` and `openspec update` stay
  the owner's commands.
- No reader for OpenSpec 1.x per-tool skill or command copies.
- No other dependency moves before its 24-hour age.

## Decisions

1. **One version, verified as today.** `package.json` pins `2.0.0` exactly. The lock is regenerated
   with a full `npm install` and `npm update` in a scratch copy, as for every lock move, with every
   other package held to the 24-hour cutoff, and every resolved URL is checked to be the public
   registry. The bridge's existing check, that the loaded package's name and version and
   `program.version()` equal the locked version, stays the guard.
2. **Ownership comes from OpenSpec's record, read by OpenSpec, as an observation.** The
   configuration bridge, which already loads OpenSpec's modules after that version check, also
   reports OpenSpec's skill ownership through `core/shared-skill-target.js`: whether the record
   names a tool, and which `openspec-*` skills it keeps as the user's. The portfolio stays pure,
   since the repository layer that reaches it imports no adapter: it takes the owned names as a
   parameter, and the gate runner supplies them by parameter name, as it supplies retained
   origins, while the status audit and the plan pass them too. OpenSpec is asked only when its
   record exists. ETHOS parses no record of its own and guesses from no skill text.
3. **Everything else is unchanged.** A kept package, a package in a repository without the record
   and any non-OpenSpec package still need an activation record or report
   `skill_package_unregistered`.
4. **The supply image follows the lock.** The CI supply image is rebuilt from the moved lock and
   bound in `.config/ci/pipeline.cue`, as `supply-move-1112` did.

## Risks / Trade-offs

- The exception takes a release younger than ETHOS's age rule; the byte comparison above and the
  full proof are the mitigation, and the exception lapses within hours.
- If a later OpenSpec release changes the record's meaning, the version check refuses the
  mismatched package before any ownership is read.
- The status edge to the configuration adapter joins the domain contract's declared exceptions,
  which the typed Facts of 0.3.0 retire with the others.

## Migration Plan

1. This Change lands and ships in beta.9.
2. Each governed repository bumps its ETHOS pin in its own Change; repositories with their own
   `@fission-ai/openspec` move it to 2.0.0, and a repository with 1.x skill copies runs
   `openspec update` once.
