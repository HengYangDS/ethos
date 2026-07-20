---
subject: ethos:ownerless-skill-scripts-semantic-closeout-20260720
role: plan
state: active
relations:
  carrier: openspec/changes/ownerless-skill-scripts-semantic-closeout-20260720
  target_lane: work/skill-scripts-ruff-20260719
---

# Ownerless Skill-Script Semantic Closeout — 2026-07-20

Status: active, local-only authority carrier.

Purpose: absorb the useful current quality hardening from one exact dirty,
lease-free Work Lane into the current baseline, then allow only its native
preserve-retire resolution after local lifecycle proof and accepted closeout.
No preservation package is a substitute for the absorption.

## Exact target and semantic absorption

The sole source is `work/skill-scripts-ruff-20260719` at
`87911a89faeb01d97a29afce1c24e0fc5ed94f2a`. It is linked, lease-free,
accepted-ancestor, and has four uncommitted helper-script deltas. The current
Ruff policy rejects their remaining `print` calls. This carrier absorbs that
useful behavior with direct `sys.stdout`/`sys.stderr` routing in the four
advertised skill scripts and refreshes the four package digests that make those
scripts repository-truth packages.

The historical dirty delta also contains stale quality-audit assumptions
(`json_syntax`, legacy package invocation, and a removed root-Ruff owner
requirement). Those assumptions conflict with the current accepted quality
contract and focused tests, so they are deliberately not replayed. This is
semantic absorption, not a branch merge.

## Native transition boundary

After this carrier has a committed HEAD-bound proof, candidate land, and local
accepted closeout, a fresh accepted Chronicle decision may invoke native
`lane resolution decide` and `lane resolution apply` with `preserve-retire` for
this exact source. The resolver must re-observe the exact branch, source head,
dirty paths, missing lease, current accepted control refs, and evidence digest;
it must preserve the remaining historical recovery material before retiring only
this source worktree/ref and emitting its receipt.

## Boundary

This authority excludes `candidate/dev` movement owned by
`work/rogue-accepted-forward-recovery-20260720`, every other Work Lane, raw
Git/SQLite deletion, source-wide merge or rebase, remote push, GitLab, GitHub
hosted CI, and publication claims.

See also: [Mutation Rules](../../rules/mutation.md),
[Runner and Mutation](../architecture/runner-and-mutation.md), and
[Repository Governance OpenSpec](../../openspec/specs/repository-governance/spec.md).
