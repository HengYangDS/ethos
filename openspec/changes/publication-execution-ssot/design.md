# Design

## Decision

`[publication].peers` remains the sole declaration owner. The command observes
each declared remote independently and compiles one immutable remote
publication effect into the existing `TransitionPlan` semantic kernel. A
content-addressed request is stored under the existing repository-local request
root. Apply loads that exact request, rechecks HEAD, repository common directory,
target refs, and push admission, then executes peer-local exact-CAS pushes.

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
| `repository-governance:proposal publication uses one admitted exact-CAS plan` | `1.1` | `test_publish_proposal_dry_run_and_apply_share_one_plan_and_attestation` |
| `repository-governance:declared peers have no mandatory provider cardinality` | `1.2` | `test_release_topology_allows_multiple_peers_from_one_provider` |
| `repository-governance:partial peer effects are retryable and attested` | `1.3` | `test_publish_proposal_preflights_all_peers_and_retry_converges` |
| `repository-governance:publication projections have one owner` | `2.1` | `test_publish_projects_declared_peer_collections_without_single_remote_aliases` |
| `quality:public regression budget is calibrated without reducing coverage` | `3.1` | `test_product_design_contract` and exact-HEAD full proof |
