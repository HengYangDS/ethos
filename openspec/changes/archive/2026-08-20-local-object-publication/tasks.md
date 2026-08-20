## 1. Establish the failing public contract

- [x] 1.1 Add full-ref admission tests proving an annotated release tag is
  classified positively and candidate or Work Lane refs remain local only.
- [x] 1.2 Add bare-peer E2E proving one local commit and annotated tag retain
  exact object, peeled commit, and tree OIDs across two independent peers.
- [x] 1.3 Add zero-peer, one-peer, zero-OID creation, already-current,
  divergent-peer, peer-local atomic, and partial-effect replay cases.
- [x] 1.4 Add a proof-admission regression proving public publish and pre-push
  consume the same exact commit, tree, gate-set, and Attestation authority.

## 2. Replace branch-only publication ownership

- [x] 2.1 Introduce one typed local Git object and full-ref target contract for
  accepted, release, proposal, and annotated release-tag publication.
- [x] 2.2 Replace `publication_branch_admission` with one ref-kind to lifecycle
  role to allowed-effect resolver and remove branch-only output fields.
- [x] 2.3 Replace the proposal-only publication effect and plan with the generic
  exact-object target set without aliases, fallback readers, or dual schemas.

## 3. Execute and verify exact peer effects

- [x] 3.1 Derive repository object format and zero OID, compile explicit
  force-with-lease coordinates, and use peer-local atomic push for a declared
  multi-ref target set.
- [x] 3.2 Verify the local source signature through Git/OpenSSH before effect
  compilation and bind verifier principal, fingerprint, and trust-root digest.
- [x] 3.3 Re-read each peer and verify commit OID or tag object OID, peeled
  commit, and tree before recording complete or partial publication evidence.
- [x] 3.4 Bind the selected exact proof Attestation into the TransitionPlan and
  project one executable proof command from both CLI and hook failures.

## 4. Delete competing product-object paths

- [x] 4.1 Delete the public identity-repair command, suffix reconstruction,
  receipts, schemas, rules, documentation, fixtures, and tests.
- [x] 4.2 Delete peer-head reconciliation observations, environment receipts,
  remote-history merge semantics, continuation requirements, and tests.
- [x] 4.3 Remove provider publication identity and proposal-only aliases while
  preserving provider labels solely for transport or observation adapters.
- [x] 4.4 Prove repository-wide reference and wording closure for all retired
  symbols and semantics before adding further behavior.

## 5. Converge public commands and projections

- [x] 5.1 Make `ethos publish` compile readiness, immutable request, receipt
  apply, and exact parity projection from the replacement contract.
- [x] 5.2 Make pre-push forward the Git update envelope to the same target and
  proof admission owner without branch parsing or peer reconciliation.
- [x] 5.3 Update release declarations, rules, command reference, architecture,
  and Forge contract to distinguish object signing, transport authentication,
  provider presentation, and publication receipt.

## 6. Verify the bounded change

- [x] 6.1 Run focused contract, executor, hook, CLI, and bare-peer E2E tests and
  prove every initially failing scenario is green, including prepared ref
  intent validity until transaction closeout.
- [x] 6.2 Run official OpenSpec 1.9 strict validation, repository-wide retired
  reference searches, lint, type, architecture, source-budget, and full tests.
- [x] 6.3 Run exact-HEAD ETHOS proof and record the requirement-to-task-to-proof
  mapping before the public archive, land, accepted closeout, and lane retire.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| `command-plane:Publish is the sole remote Git object projection command` | `5.1` | `test_publish_branch_dry_run_and_apply_share_one_plan_and_attestation`, `test_publish_projects_one_signed_release_tag_through_the_full_ref_command` |
| `command-plane:Identity repair supports one receipt-bound linear suffix` | `4.1` | `test_retired_git_object_reconstruction_commands_are_absent` |
| `repository-governance:Declared publication peer topology` | `1.3` | `test_release_topology_supports_every_declared_peer_cardinality`, `test_release_topology_allows_multiple_peers_from_one_provider` |
| `repository-governance:Strict remote publication admission` | `1.1` | `test_release_topology_admits_only_positive_full_ref_roles`, `test_publication_rejects_lightweight_or_untrusted_release_tags` |
| `repository-governance:Independent peer effects remain recoverable` | `3.3` | `test_publish_branch_preflights_all_peers_and_retry_converges`, `test_publish_branch_retry_records_one_terminal_attestation_after_interruption` |
| `repository-governance:Publication semantics have one owner per layer` | `5.2` | `test_publish_and_pre_push_bind_the_same_exact_proof_attestation`, `test_publish_projects_declared_peer_collections_without_single_remote_aliases` |
| `repository-governance:Exact local Git object projection` | `1.2` | `test_publication_projects_one_trusted_annotated_tag_exactly_to_two_peers`, `test_publication_effect_owns_exact_full_ref_cas` |
| `repository-governance:Proposal publication is receipt-bound exact CAS` | `2.3` | `test_publish_proposal_target_requires_the_local_candidate_source`, `test_publish_branch_dry_run_and_apply_share_one_plan_and_attestation` |
| `repository-governance:Maintainer remote reconciliation preserves observed protected history` | `4.2` | `test_pre_push_rejects_retired_reconciliation_inputs` |
| `repository-governance:Remote reconciliation continuation preserves historical carrier boundaries` | `4.2` | `test_pre_push_rejects_retired_reconciliation_inputs`, repository-wide retired-reference closure |
