---
subject: ethos:decision:docs-kernel-invariance-and-adopter-parity-locus
role: decision
state: canonical
relations:
  depends_on: DR-0004
  informs: docs topology gate, external adopter parity evidence locus
---

# DR-0007: Docs Kernel Form-Invariance and Adopter-Parity Evidence Locus

Status: accepted.

Purpose: record two investigated non-problems as durable rulings so they are not
re-opened — (1) the documentation required-path kernel is deliberately repository-form
invariant and must not become lifecycle-conditional, and (2) real external-adopter
parity evidence lives in the adopter repository, never in the ETHOS product core; the
product's only tracked parity artifact is the generic self-shadow.

See also: [Decision Records](../README.md), [Decision Index](../decision-index.md),
and [Accepted Decisions](README.md).

## Record

| Field | Value |
| --- | --- |
| Status | accepted |
| Class | architecture / documentation |
| Scope | Docs required-path kernel invariance; locus and cost profile of adopter parity evidence. |
| Supersedes | none |
| Depends on | DR-0004 (native documentation topology contract) |

## Context

Two roadmap items were queued as work ("make docs required-paths vary by repository
form so an empty adopter is not blocked"; "the generic parity shadow is self-referential
and proves nothing — point it at a real adopter"). Investigation against the live code
showed both premises were false. Recording the findings prevents the work from being
re-queued.

### Finding 1 — docs required-path kernel is intentionally form-invariant

`ethos_core/contracts/docs/topology.py` declares `repository_form_invariant: True`: one
12-path kernel (`docs/README.md`; `reference/`, `evidence/`, `history/` READMEs; and the
eight `decisions/*` records) is required identically for single-repository, monorepo, and
multi-repository forms. The rationale is in the contract itself: a shared skeleton means
humans and agents recover the same lanes in any governed repository without relearning
its layout.

The "empty adopter is blocked by required READMEs that have no artifacts yet" scenario
does not occur: `ethos adopt` scaffolds the whole kernel. Verified empirically — a fresh
`ethos adopt --apply` followed by `ethos quality docs-topology` reports `state=clean`,
`gaps=[]`. The one dimension that genuinely varies per adopter (legacy time-state roots /
state-metadata form) is already handled by the profile-driven
`_profile_docs_topology_policy`.

### Finding 2 — adopter parity evidence is adopter-side by design

`evidence/parity/generic-shadow.json` recording `target: "<repo>"` is correct, not a
defect: `shadow/routing.py` returns the `<repo>` placeholder precisely when
`adopter == "generic"` and the target is the product's own repository — this is ETHOS
proving its own governance is self-consistent (a self-shadow).

Real external-adopter parity is a separate, supported path: the target is recorded as the
redacted `<target-repo>` placeholder (HEAD/digest-bound, no workstation path leak) and the
evidence is written to and read from the ADOPTER repository, not the product core.
`parity_evidence_repository_root` states the rule directly: "Evidence for a distinct
adopter Git repository is written and read from that adopter target so the product core
does not accumulate adopter-specific tracked artifacts." Verified: a real run of
`ethos parity shadow --adopter <adopter-id> --target <target-repo> --execute` matched
clean (eight substantive command comparisons, external-vs-embedded, zero semantic diff,
zero false negatives), and the adopter already carries its own
`docs/evidence/parity/<adopter-id>-shadow.json`.

## Decision

1. **The docs required-path kernel stays repository-form invariant.** It must not be made
   lifecycle-conditional ("required once the first artifact of that class exists").
   Trading a clean, learnable, form-invariant skeleton for lifecycle branching is
   anti-ISP and contradicts DR-0004's minimal-kernel intent. Genuine adopter variation is
   expressed through the existing profile docs-topology policy, not by weakening the
   kernel.

2. **Real external-adopter parity evidence lives in the adopter repository.** The ETHOS
   product core tracks only the generic self-shadow (`generic-shadow.json`). A committed
   `<adopter-id>-shadow.json` inside ETHOS is disallowed: it would make the product core
   accumulate adopter-specific artifacts and hardcode a particular adopter, violating the
   generic-product principle. The prove-time evidence-freshness gate defaults to the
   `generic` adopter, so adopter-side evidence imposes no freshness burden on the product.

3. **"Adoptability" is proven by the machinery plus adopter-side evidence, not by a
   product-core artifact.** The parity command running equivalently against a real foreign
   adopter, with the adopter holding its own shadow evidence, is the proof — there is no
   additional ETHOS-side deliverable to add.

## Consequences

- Two roadmap items close as investigated non-problems; no code change ships for either
  (如非必要勿增实体).
- The docs kernel and the parity-evidence locus each have an explicit, citable ruling, so
  a future contributor who rediscovers the surface reads the rationale instead of
  re-litigating it.
- If a manual (non-`ethos adopt`) onboarding of a pre-existing repository is ever a real
  friction, the sanctioned fix is a clearer error pointing at `ethos adopt`, NOT a
  contract change to the kernel.
- Keeping adopter parity evidence stale-tolerant on the product side (freshness keyed on
  `generic`) is intentional: an adopter refreshes its own shadow in its own lane; ETHOS
  does not track or gate on it.

## Proof Or Evidence

- `packages/ethos-core/src/ethos_core/contracts/docs/topology.py` (`repository_form_invariant`,
  `DOCS_ROOT_REQUIRED_PATHS`, `DECISION_RECORD_REQUIRED_PATHS`).
- `packages/ethos/src/ethos/repository/evidence/shadow/routing.py`
  (`REPOSITORY_TARGET`, `EXTERNAL_REPOSITORY_TARGET`, `parity_evidence_repository_root`,
  `tracked_target_identity`).
- `packages/ethos/src/ethos/repository/evidence/parity/core.py` (`parity_gaps_report`
  defaults to the generic adopter).
- Empirical: fresh `ethos adopt` → `docs-topology` clean; `ethos parity shadow` against a
  real adopter matched with zero semantic diff.

## Revisit Trigger

Revisit Finding 1 only if a governed repository form emerges whose users genuinely cannot
recover a lane the kernel names (not merely "have not populated it yet"). Revisit Finding
2 only if ETHOS gains a first-party, non-adopter-specific reason to track cross-adopter
parity centrally (e.g. a fleet dashboard) — and even then the artifact must remain
adopter-neutral.
