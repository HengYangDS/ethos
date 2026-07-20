## Context

The current adoption planner is intentionally safe: a nonempty differing
scaffold target is a conflict. That is correct for the default full scaffold,
but a real repository already has high-authority agent guidance, contributor
guidance, documentation, OpenSpec, and hosted CI files. Treating all of those
as overwrite-or-block makes the documented promise to reference existing
adopter surfaces unachievable.

An isolated external-adopter pilot at a fixed local source revision demonstrates
this without changing the source checkout: its detected `gitlab` profile found
16 protected conflicts, including an AGENTS entrypoint, OpenSpec workspace,
documentation topology, and `.gitlab-ci.yml`.

## Goals / Non-Goals

**Goals:**

- Preserve strict full-scaffold admission by default.
- Add a deliberately requested overlay path for repositories that already own
  their governance surfaces.
- Make preserved surface identity visible in machine output through stable
  content digests.
- Create only missing ETHOS-owned binding and projection surfaces.
- Exercise the behavior against the isolated real adopter clone.

**Non-Goals:**

- Merge or rewrite an adopter's prose, OpenSpec semantics, CI, skills, or
  branch policy.
- Infer semantic compatibility from a matching filename.
- Require a provider account, `yheng-agent-ethos`, remote availability, key,
  or independent-verification receipt.
- Publish any branch or mutate the source external-adopter checkout.

## Decisions

### Explicit `--overlay`, not a changed default

`ethos adopt` remains strict unless callers provide `--overlay`. This retains
the current fail-closed behavior for normal scaffolding and makes the authority
decision reviewable in command JSON. A silent "keep existing" default would
hide whether ETHOS actually installed a usable binding.

### Narrow preserved-surface allowlist

Overlay mode preserves only adopter-owned high-level surfaces: root guidance,
contributor/release prose, `docs/**`, `openspec/**`, and the selected hosted CI
projection (`.gitlab-ci.yml` or `.github/**`). Existing `.ethos/**`,
`.config/ethos/**`, ETHOS skill packages, and schema placeholders remain
ETHOS-owned; a differing file there remains a blocking conflict.

This separates adopter authority from ETHOS binding authority. It also leaves
the normal `.gitignore` additive merge unchanged.

### Preserve evidence is observable, not authoritative

For every preserved file, the plan records path and SHA-256 of current bytes.
That proves what was deliberately not modified; it does not validate the
adopter's semantics or mint compatibility truth. Subsequent `status`, `report`,
and profile-appropriate proof remain the admission evidence.

## Risks / Trade-offs

- **Existing surface may be incompatible with ETHOS expectations** → overlay
  records it as preserved, never as validated; downstream commands surface
  their own gaps.
- **Allowlist becomes too broad** → limit it to clear adopter-owned prefixes
  and retain conflicts for ETHOS-owned locations.
- **A target's CI is overwritten** → selected provider projections are
  explicitly preserved in overlay mode and covered by tests.
- **Pilot data is mistaken for a hosted adoption** → retain all pilot evidence
  locally; remote publication and hosted CI remain unclaimed.

## Migration Plan

1. Add the explicit CLI and planner mode with strict mode unchanged.
2. Add unit and CLI tests for preservation, digest reporting, and retained
   conflicts under ETHOS-owned paths.
3. Update adoption documentation.
4. Run the isolated external-adopter clone through overlay dry-run and apply.
5. Record bounded local evidence; rollback the pilot by deleting its isolated
   clone, never by modifying the source checkout.
