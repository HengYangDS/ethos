# Design

## Context

See the [proposal](proposal.md). The skills.sh installer (`vercel-labs/skills`, default branch read
on 2026-11-12) treats a Skill as internal when its `metadata.internal` is `true`, `"true"` or `"1"`,
and skips it unless `INSTALL_INTERNAL_SKILLS=1` is set or the caller names that Skill. It walks
`.agents/skills/` among its standard containers, and when it collects no Skill there, it searches
the whole repository. The Agent Skills standard defines `metadata` as a map of strings.

The `product-form-plan` design keeps one owner of a repository's Skill (Non-Goals) and defers any
discovery channel to a pointer that owns no guidance (decision 8, owner decision D4).

## Goals / Non-Goals

Goals:

- skills.sh discovery offers no ETHOS Skill until a pointer exists.
- A Skill added to the repository later cannot be offered by accident.

Non-Goals:

- The pointer plugin, which waits for a named consumer.
- Any change to how agents load the packaged Skill: they read the path that `ethos status` reports.

## Decisions

1. Each tracked `SKILL.md` gains `metadata:` with `internal: "true"`, a string so the frontmatter
   stays within the standard. ETHOS's own frontmatter checks read only `name` and `description`.
2. The packaged `ethos-repository-work` Skill is marked too, beyond the four that item N6 names: the
   installer's fallback search would otherwise offer it from the default branch.
3. Each maintainer package's `expected_digest` is recomputed with
   `compute_skill_package_digest`; the packaged Skill has no recorded digest.
4. An architecture test reads every tracked `SKILL.md` and requires the flag, so the rule binds new
   Skills.

## Risks / Trade-offs

- A caller who names a Skill explicitly, or sets `INSTALL_INTERNAL_SKILLS=1`, can still install it.
  That is a deliberate choice, and the README says why it is not supported.
- An agent client that hid internal Skills from its own loader would hide this guidance too. The
  installer is the only reader of the flag that this Change found.
