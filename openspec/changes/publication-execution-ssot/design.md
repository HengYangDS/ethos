# Design

## Decision

`[publication].peers` remains the sole declaration owner. The command observes
each declared remote independently and compiles one immutable remote
publication effect into the existing `TransitionPlan` semantic kernel. A
content-addressed request is stored under the existing repository-local request
root. Apply loads that exact request, rechecks HEAD, repository common directory,
target refs, and push admission, then executes peer-local exact-CAS pushes.

The candidate role is the common integration boundary. Local-first proceeds
candidate to accepted and synchronizes accepted refs. Proposal/MR-first proceeds
candidate to `proposal/*`; the forge merges that proposal into accepted, and
local accepted refs then synchronize from the remote result. Requiring proposal
publication from accepted would collapse these two paths and make review occur
after acceptance, so the command rejects any proposal source other than the
configured candidate branch.

The effect contract owns immutable target coordinates; the mutation adapter
owns observation, request persistence, execution, and attestation; the CLI owns
argument binding and result projection only. No layer recompiles another
layer's policy. Providers are descriptive metadata, not cardinality keys, so
several independent peers may use the same provider when peer IDs and Git
remotes remain unique.

Failure after one peer succeeds is reported as a partial effect. Replaying the
same receipt observes an already-matching peer as complete and continues the
remaining peers. ETHOS does not claim distributed atomicity.

DRY, SSOT, MECE, and SOLID are applied as deletion tests: the model base class,
single-peer result aliases, publication-specific attestation store, duplicate
local-command validator, and one-test owner file are removed or absorbed. The
remaining contract, adapter, repository compiler, domain reducer, and CLI each
retain one distinct authority or reason to change.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `repository-governance:Proposal publication is receipt-bound exact CAS` | `1.1` | `test_publish_proposal_dry_run_and_apply_share_one_plan_and_attestation` |
| `repository-governance:Independent peer effects remain recoverable` | `1.3` | `test_publish_proposal_preflights_all_peers_and_retry_converges` |
| `repository-governance:Publication semantics have one owner per layer` | `2.1` | `test_publish_projects_declared_peer_collections_without_single_remote_aliases` |
