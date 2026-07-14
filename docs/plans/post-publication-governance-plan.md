---
subject: governance:post-publication-plan
role: plan
state: canonical
relations:
  canonical_for: local closeout, remote publication tail, Work Lane residue, no-compat hardening
---

# Post-Publication Governance Plan

Status: canonical.

Purpose: define the next operating plan after local accepted-root closeout when
remote availability, remote publication, and foreign Work Lanes must remain
separate governed facts.

## Non-Negotiable Boundaries

Do not mutate, retire, reset, stash, or clean another Work Lane.
The operational rule is: do not mutate, retire, reset, stash, or clean another Work Lane.

- A default `ethos publish --json` does not probe or push a remote. It MUST
  report `remote_availability_state = "not_probed"`, rather than infer that a
  remote is unavailable. `--probe-remote` observes availability without
  publishing.
- An unavailable, reachable, synchronized, or divergent remote does not itself
  establish remote publication. Keep `origin/dev` state visible and record a
  separately admitted provider observation before any hosted claim.
- Use local fallback evidence instead of hosted-CI or remote-publication claims:
  run `tools/ci/scripts/run-local-ci.sh`, then run HEAD-bound `ethos prove
  --execute --expect-head <HEAD> --json`.
- Do not mutate, retire, reset, stash, or clean another Work Lane. Visible
  foreign Work Lanes are coordination signals only unless the owner hands them
  off or a maintainer records break-glass evidence.
- Keep local closeout, candidate convergence, accepted-root convergence, local
  fallback proof, remote publication, hosted CI, and release/tag publication as
  separate states.

## Phase 0: Local Publication Tail Before a Remote Decision

Target state:

- `dev == candidate/dev` for the local accepted-root train.
- The configured GitLab primary may be unknown until an explicit read-only
  probe; this does not change local readiness.
- A configured GitHub mirror is observed separately. During primary outage it
  may carry update and distribution, never a GitLab-primary publication claim.
- `ethos publish --json` reports `local_publish_ready`, `remote_push =
  not_performed`, `remote_publication_state = "deferred"`, and a local
  fallback-evidence next action that distinguishes `not_probed` from
  unavailable.

Required evidence:

1. `git status --short --branch` shows a clean accepted root.
2. `git rev-parse HEAD dev candidate/dev origin/dev` is recorded in the handoff.
3. `ethos status --json`, `ethos report --json`, and `ethos parity gaps --json`
   have no required gaps.
4. `tools/ci/scripts/run-local-ci.sh` writes
   `build/evidence/local-ci/fallback.json` for the current HEAD.
5. `ethos prove --execute --expect-head <HEAD> --json` proves the same HEAD.

Stop condition: HEAD moves during local CI or proof. Discard that evidence and
rerun on the new HEAD.

## Phase 1: Work Lane Residue Without Intrusion

Classify, but do not alter, foreign lanes:

- active owned lanes;
- landed clean residue;
- landed dirty residue;
- diverged lanes;
- missing-lease lanes;
- unknown-scope lanes.

Allowed actions for foreign lanes are observe, report, and request owner handoff.
Forbidden actions are write, land, retire, reset, stash, clean, or branch deletion.
Do not mutate, retire, reset, stash, or clean another Work Lane without owner handoff.
Dirty residue must be preserved until the owner or maintainer records the
intended disposition.

## Phase 2: No-Compatibility-Residue Gate

No-compatibility-residue gate is part of the product proof floor. It blocks
production-source compatibility residue such as compatibility shims, deprecated
surfaces, retired wrappers, dynamic export forwarding, and import-path shells.

This gate complements module-layout checks. Module layout blocks facades and
import aliases; no-compat blocks semantic cutover residue that would otherwise
survive as named production code.

## Phase 3: Isomorphic Governance Kernel

The same kernel is varied only by profiles and adapters, not product cloning.

ETHOS continues to govern itself and adopted repositories with the same kernel,
not product cloning. Profiles and adapters may change admission checks, tool owners, and proof depth,
but they do not create a second lifecycle.

Stable command chain:

```text
status -> plan -> prove -> land -> publish
```

Stable kernel chain:

```text
Authority -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

## Phase 4: Dual-Remote Synchronization and Publication Admission

Only after an explicit provider decision authorizes publication:

1. Run `ethos publish --probe-remote --json`. Record local readiness, GitLab
   primary availability, GitHub mirror availability, and their tracking states
   as separate facts.
2. For GitLab primary publication, re-check
   `git rev-list --left-right --count origin/dev...dev`, confirm `origin/dev`
   is an ancestor of `dev`, and push without force only after the distinct
   primary-publication admission.
3. If GitLab is unavailable and GitHub is available, GitHub may carry the
   separately admitted update and distribution transition. It must not be
   described as GitLab primary publication or GitLab hosted CI.
4. Fetch and confirm exact ref equality for whichever remote was actually
   transitioned. Record provider, actor, ref transition, and hosted observation
   as provider facts; do not recast them as local proof.

## Phase 5: Release Planning

Remote publication is not release. Release requires version, changelog, tag,
distribution artifacts, SBOM/attestation, and release evidence to agree under
release governance. Do not infer release readiness from local closeout or remote
branch publication alone.

## See Also

See also: [Product Design Contract](../governance/product-design-contract.md), [Release Governance](../governance/release-governance.md), and [Terminal Governance Product Design](terminal-governance-product-design.md).
