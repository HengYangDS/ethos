---
subject: ethos:evidence:productization-convergence
role: evidence
state: active
relations:
  evidence_refs: OpenSpec, pytest, Ruff, build, proof, shadow parity, expert committee
---

# Productization Convergence Evidence - 2026-07-01

## Scope

This evidence records the `ethos-productization-convergence` campaign slice.

The product question for this batch was not "add more governance surface." The
question was whether ETHOS can be read, adopted, proved, closed out, and
published as a product instead of as a half-migrated projection from advanced
adopter repositories.

The convergence target is:

- A single product judgment authority:
  `JudgmentSource -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle`.
- A first-hour adopter path that starts with profile selection, dry-run
  inspection, explicit apply criteria, generated-file rollback, and the command
  loop `status -> plan -> prove -> land -> publish`.
- `report` as a read-only scorecard, not a workflow transition.
- Maintainer/reference commands that remain reachable but do not pollute the
  adopter first-hour surface.
- Claims that bind evidence without turning digest-only evidence into semantic,
  hosted, publication, or domain parity proof.
- A typed authority graph read model that separates canonical docs from evidence
  references and reports drift through self-audit.
- External shadow parity that compares ETHOS command behavior against adopter
  repositories without claiming adopter domain closure.

## Implemented Changes

- Public command registry now exposes only the five workflow commands as public
  workflow commands. `report` is a scorecard command, setup/onboarding commands
  are separate from the transition loop, and advanced command roots are
  maintainer/reference commands.
- CLI help hides maintainer/reference subapps and root reference commands from
  first-hour help while keeping the commands callable.
- Adoption planning now records requested profile, detected profile, observed
  files, profile match, write plan, generated rollback list, apply criteria,
  conflict gaps, and next action. Apply is blocked when the requested profile
  does not match the repository shape.
- `init --apply` and `adopt --apply` require explicit authorization and
  expected Git HEAD binding. Non-Git apply is blocked with
  `git_repository_missing` instead of treating `untracked` as a valid mutable
  HEAD.
- `land --json` dry-run consumes closeout support and reports dirty Work Lane
  blockage instead of presenting local closeout as ready.
- Generated quickstart, skill, and contributing scaffold content teach the
  five-command loop plus `report`; they no longer route first-hour users through
  execution-only proof or quality subcommands.
- Kernel docs, OpenSpec specs, package README, and product docs now converge on
  the seven-term Judgment Source chain.
- `EvidenceClaim` requires typed evidence ids, binding, and verifier. Claim
  reporting applies digest-only overclaim checks to both active claim summary and
  binding text, rejecting semantic, hosted, publication, and domain closure
  wording without a semantic verifier.
- `ChronicleEvent` is constrained to decision, evidence, state-change, and
  supersession event types. Decision events require evidence, decision, and
  current-state delta fields; evidence, state-change, and supersession events
  require the payload fields relevant to that event type.
- Active claim TOML records now carry digest-only binding metadata compatible
  with the stricter claim schema.
- Authority graph validation now checks list fields, unique ids, relation type,
  doc refs, evidence refs, evidence location, and derived-view derivation.
- Parity freshness now includes current product HEAD in generic gaps, shadow
  parity, and closeout records; stale product-head records are rejected.
- Product report parity output explicitly states that generic command parity is
  not domain profile closure.

## Expert Committee Findings And Resolution

Five reviewers were used in the committee pass: Aquinas, Gibbs, Hypatia,
Laplace, and Pasteur. The initial pass blocked the batch.

Blocking findings and resolution:

- Public command leak: reviewers required the public transition path to be
  exactly `status -> plan -> prove -> land -> publish`, with `report` as a
  scorecard. The registry, docs checks, CLI help, README, Quickstart, and product
  design contract were updated around that split.
- Adoption first hour: reviewers required real dry-run/apply safety, profile
  mismatch reporting, write plan inspection, and generated scaffold updates. The
  planner and CLI apply path now report those fields and block unsafe apply.
- Kernel ontology: reviewers rejected the old vocabulary chain as canonical. The
  product chain is now the seven-term Judgment Source chain across code, specs,
  docs, and package README.
- Evidence and Chronicle constraints: reviewers found digest-bound claims and
  chronicle decisions underconstrained. The kernel model, JSON schemas, and claim
  report now enforce typed evidence ids, binding, verifier, active summary
  overclaim rejection, and event-type payload requirements.
- Authority graph: reviewers found docs masquerading as evidence. The read model
  now separates `doc_refs` from `evidence_refs` and validates evidence paths.
- Parity overclaim: reviewers required freshness checks and explicit caveats.
  Parity reports now bind current product HEAD and the product report states that
  command shadow parity does not close domain profile work.
- Batch closeout: reviewers required dated evidence, claim binding, and OpenSpec
  task closeout for this batch. This evidence file and its claim record are the
  closeout artifacts for that requirement.

## Verification

Commands run from `/Users/yheng/projects/ethos-work-productization-convergence`
on branch `work/productization-convergence`, product HEAD
`992b52a0cb7d0e70a2ecff1a92bfa36e3f9de5c3`.

```bash
uv run --group dev ruff check packages/ethos-repository/src/ethos_repository/planner.py tests/unit/test_kernel_contracts.py --fix
uv run --group dev ruff check .
uv run --group dev pytest tests/unit tests/architecture -q
uv run --group dev pytest -q
uv run openspec validate --all --strict --json
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos self audit --mode shape --json
uv run --package ethos ethos report --json
uv build --all-packages
uv run --package ethos ethos prove --expect-head "$(git rev-parse HEAD)" --json
uv run --package ethos ethos prove --full --execute --json
uv run --package ethos ethos parity gaps --json
uv run --package ethos ethos parity shadow --target /Users/yheng/projects/alphasim-dmgr-fix-b3 --execute --timeout-seconds 60 --json
uv run --package ethos ethos parity shadow --target /Users/yheng/projects/di-effect --execute --timeout-seconds 60 --json
uv run --group dev pytest tests/unit/test_command_registry_depth.py tests/unit/test_claims_governance.py tests/unit/test_kernel_contracts.py -q
uv run --group dev pytest tests/unit/test_adoption_profiles.py tests/unit/test_cli_contracts.py -q
uv run --package ethos ethos quality claims --json
```

Observed results:

- Ruff fixed two import-order issues, then full Ruff returned
  `All checks passed!`.
- Focused convergence regression suite returned `163 passed in 26.06s`.
- Reviewer-driven adoption safety regressions returned `79 passed in 28.81s`.
- Full pytest returned `300 passed in 56.49s`.
- OpenSpec strict validation returned `9` items passed, `0` failed.
- Schema quality returned `ok=true`, `state=clean`, `schema_count=23`, and no
  required gaps.
- Claim quality returned `ok=true`, `state=clean`, and no required gaps.
- Self audit returned `ok=true`, `state=clean`, and no required gaps.
- Product report returned `ok=true`, `state=ready`, score `15 / 15`, no product
  gaps, and no parity pending count.
- `uv build --all-packages` built wheel and sdist artifacts for all seven
  Python packages.
- HEAD-bound proof returned `state=proven`,
  `expected=current=992b52a0cb7d0e70a2ecff1a92bfa36e3f9de5c3`, no required
  gaps, and evidence digest
  `08ac42063c7ae86f73ea24d0b0c846fe5812220e7014f131ee73c8a96eeac62b`.
- Executed full proof returned `state=proven`, no required gaps, evidence
  digest `49dcec973134770959799e71332812c9406b4597826a9d4cfb9122bfe198ee4e`,
  and 8 passed gate runs: claims, docs-registry, ruff, schemas, self-audit,
  unit-architecture, build, and openspec. The unit-architecture gate returned
  `300 passed in 55.84s`.
- Generic parity gaps returned `ok=true`, `state=clean`, `gap_count=0`.
- alphasim-dmgr shadow returned `ok=true`, `state=matched`, and no required
  gaps for the ETHOS command comparison set.
- di-effect shadow returned `ok=true`, `state=matched`, and no command
  comparison required gaps for the same command set.
- Focused post-review regressions for command registry classification, active
  claim overclaim checks, and Chronicle event constraints returned
  `26 passed in 0.17s`.
- Post-review claim quality returned `ok=true`, `state=clean`, and no required
  gaps after active digest-only claim summaries were downgraded to
  evidence-record wording.

## External Shadow Boundaries

The alphasim-dmgr shadow run targeted
`/Users/yheng/projects/alphasim-dmgr-fix-b3` at target HEAD
`8b8bf19ef8df92b3096c0e651433cac74c15f7f1`. Its external `ethos status` output
reported branch `dev`, `dirty=false`, and `changed_path_count=0`.

The di-effect shadow run targeted `/Users/yheng/projects/di-effect` at target
HEAD `e9e474fe1e4a1b00d01d97b0e706235465cd21f6`. Its external `ethos status`
output reported branch `dev`, `dirty=true`, `changed_path_count=2`, and
`candidate_branch_missing`. Its publish comparison included
`local_publish_readiness_blocked` on the target side. The shadow still matched
because product ETHOS and the embedded/adopter command surface agreed on the
reported state.

These shadow results are command-surface evidence only. They do not claim
hosted CI, remote publication, adopter domain migration, backend retirement, or
dmgr raw/cache parity. dmgr-specific validation remains an adopter profile and
domain evidence problem, not an ETHOS product-core claim.

## Remaining Product Boundary

The Work Lane remains dirty until this batch is committed and landed through the
ETHOS lane mechanism. `ethos status --json` therefore reports closeout support
blocked by `work_lane_dirty` during this evidence-writing stage. That is a
workflow state, not a product audit gap.

## Post-Commit Closeout Addendum

This addendum supersedes the transient dirty-worktree note above for closeout
readiness. It records the code and contract state at
`49c78fdb895e5d53f887c8be9911888cd80eac8e`; the later metadata-only commits
refresh reader evidence, claim SHA, and tracked parity freshness without
changing runtime code.

Commands rerun from `/Users/yheng/projects/ethos-work-productization-convergence`
on branch `work/productization-convergence`:

```bash
git status --short --branch
uv run --package ethos ethos prove --expect-head 49c78fdb895e5d53f887c8be9911888cd80eac8e --json
uv run --group dev pytest -q
uv run --package ethos ethos prove --full --execute --json
uv run --package ethos ethos parity gaps --json
uv run --package ethos ethos report --json
uv run --package ethos ethos quality claims --json
uv run openspec validate --all --strict --json
uv run --package ethos ethos status --json
```

Observed results:

- Worktree status returned clean on `work/productization-convergence`.
- HEAD-bound proof returned `ok=true`, `state=proven`, expected and current HEAD
  `49c78fdb895e5d53f887c8be9911888cd80eac8e`, no required gaps, and evidence
  digest `329e80634fef76fd8aafa25d29a56128b852a455bde9b558006ed3581e7b226d`.
- Full pytest returned `302 passed in 77.03s`.
- Executed full proof returned `ok=true`, `state=proven`, no required gaps,
  evidence digest `e6ca90f8933604d655636433eb7d32f0e86a7119c8a6ae253d2cb38245f988f2`,
  and 8 passed gate runs: claims, docs-registry, ruff, schemas, self-audit,
  unit-architecture, build, and openspec. The unit-architecture gate returned
  `302 passed in 60.47s`.
- Generic parity gaps returned `ok=true`, `state=clean`, `gap_count=0`.
- Product report returned `ok=true`, `state=ready`, score `15 / 15`,
  `product_gap_count=0`, and `parity_pending_count=0`.
- Claim quality returned `ok=true`, `state=clean`, and no required gaps.
- OpenSpec strict validation returned 9 items passed and 0 failed.
- ETHOS status returned `ok=true`, `state=ready`, `dirty=false`,
  `changed_path_count=0`, and closeout support for `candidate/dev` with no
  required gaps.

Six independent committee reviewers returned `STATUS: APPROVED`. Their common
boundary condition remains unchanged: generic ETHOS command parity is not a
claim of hosted CI, remote publication, alphasim-dmgr raw/cache or domain
backend retirement parity, or di-effect publish readiness.

## Committee Fix Addendum: Canonical Governance Context

The final committee re-review at post-merge HEAD
`f41d1fe61079a3ad6eec124127fa5269187ba876` produced one
`STATUS: CHANGES_REQUIRED` finding. The reviewer identified that live
`governance_context` JSON still emitted the retired nine-term kernel chain and
classified `ethos report` with the transition loop.

The fix converges live command JSON, docs, specs, and glossary surfaces to the
canonical seven-term kernel:

```text
JudgmentSource -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

`governance_context.shared_commands` and `governance_context.transition_commands`
now both contain only the five transition commands:

```text
ethos status
ethos plan
ethos prove
ethos land
ethos publish
```

`governance_context.scorecard_commands` now carries `ethos report` as the
read-only scorecard surface. The product design contract, command-plane
reference, OpenSpec contracts, and glossary were updated to match that split.

Commands rerun from `/Users/yheng/projects/ethos-work-productization-convergence`
after the fix:

```bash
uv run --group dev pytest -q tests/unit/test_cli_contracts.py::test_self_audit_reports_product_shape tests/unit/test_cli_contracts.py::test_prove_uses_adopter_audit_for_non_product_repo
uv run --group dev pytest -q tests/architecture/test_product_design_contract.py::test_product_design_contract_defines_single_kernel_dual_posture tests/unit/test_cli_contracts.py::test_self_audit_reports_product_shape tests/unit/test_cli_contracts.py::test_prove_uses_adopter_audit_for_non_product_repo
uv run --group dev pytest -q tests/architecture/test_product_design_contract.py::test_glossary_uses_canonical_kernel_terms tests/architecture/test_product_design_contract.py::test_canonical_kernel_surfaces_do_not_promote_retired_chain_terms tests/unit/test_docs_registry.py
uv run --group dev pytest -q tests/unit/test_cli_contracts.py::test_self_audit_reports_product_shape tests/unit/test_cli_contracts.py::test_prove_uses_adopter_audit_for_non_product_repo tests/unit/test_cli_contracts.py::test_report_uses_adopter_scorecard_for_non_product_repo tests/unit/test_cli_contracts.py::test_report_scorecard_is_derived_from_governance_checks tests/architecture/test_product_design_contract.py tests/unit/test_kernel_contracts.py tests/unit/test_command_registry_depth.py tests/unit/test_docs_registry.py
uv run --group dev ruff check packages/ethos-contracts/src/ethos_contracts/governance_context.py packages/ethos-repository/src/ethos_repository/docs_registry.py tests/unit/test_cli_contracts.py tests/architecture/test_product_design_contract.py
uv run openspec validate ethos-productization-convergence --strict --json
uv run openspec validate ethos-contracts --strict --json
uv run openspec validate ethos-repository --strict --json
```

Observed results:

- Initial red tests failed on the retired kernel chain, `shared_commands`
  containing `ethos report`, and missing scorecard classification.
- Focused governance-context tests passed: `2 passed`, then `3 passed`.
- Glossary and docs registry focused tests passed: `10 passed`.
- Broader focused regression passed: `47 passed`.
- Ruff reported `All checks passed!`.
- OpenSpec strict validation passed for `ethos-productization-convergence`,
  `ethos-contracts`, and `ethos-repository`.

The boundary condition remains unchanged: this addendum fixes local product
contract semantics and candidate landing readiness. It does not claim hosted CI,
remote publication, alphasim-dmgr raw/cache or domain backend retirement parity,
or di-effect publish readiness.

## Committee Follow-Up Addendum: Adopter Schema Parity

The subsequent committee check found that external ETHOS applied the product
`capability-profile.schema.json` as a blocking live-instance contract to legacy
adopter `openspec/specs/*/capability.toml` files. That was too broad: product
capability profiles remain strict product contracts, but adopter-owned
capability profile metadata is advisory unless promoted into an ETHOS product
contract.

The fix records adopter live capability profile schema failures under
`advisory_gaps` instead of `required_gaps` while keeping product mode strict.
The same pass also normalized shadow parity projection for successful dry-run
`ethos prove --json`: external `state=ready` and legacy embedded proof-ready
state now compare as the same no-gap proof-readiness condition without changing
the public CLI payload.

Commands rerun from `/Users/yheng/projects/ethos-work-productization-convergence`
after the schema/parity fix at code HEAD
`5c8fed87ed47e311691752998f4aaec10246e514`:

```bash
uv run --group dev pytest -q tests/unit/test_schema_validation_and_gates.py::test_schema_validation_keeps_adopter_capability_profiles_advisory
uv run --group dev pytest -q tests/unit/test_parity_command.py::test_shadow_semantic_diff_normalizes_ready_prove_against_legacy_payload
uv run --group dev pytest -q tests/unit/test_schema_validation_and_gates.py tests/unit/test_parity_command.py::test_shadow_semantic_diff_normalizes_ready_prove_against_legacy_payload tests/unit/test_parity_command.py::test_shadow_semantic_diff_derives_state_for_legacy_status_payload tests/unit/test_parity_command.py::test_shadow_semantic_diff_derives_state_for_legacy_plan_payload tests/unit/test_parity_command.py::test_shadow_semantic_diff_derives_state_for_legacy_assistants_doctor_payload tests/unit/test_parity_command.py::test_shadow_semantic_diff_classifies_external_self_audit_gaps_for_legacy_payload tests/unit/test_parity_command.py::test_shadow_semantic_diff_preserves_external_non_self_audit_gaps tests/unit/test_cli_contracts.py::test_default_proof_reports_readiness_not_proven tests/unit/test_cli_contracts.py::test_prove_uses_adopter_audit_for_non_product_repo tests/unit/test_cli_contracts.py::test_report_uses_adopter_scorecard_for_non_product_repo
uv run --group dev ruff check packages/ethos-repository/src/ethos_repository/schema_validation.py packages/ethos-adapters/src/ethos_adapters/shadow.py tests/unit/test_schema_validation_and_gates.py tests/unit/test_parity_command.py
uv run --package ethos ethos parity shadow --target /Users/yheng/projects/alphasim-dmgr-fix-b3 --execute --timeout-seconds 60 --json
uv run --package ethos ethos parity gaps --json
uv run --package ethos ethos parity gaps --adopter alphasim-dmgr --json
uv run --group dev pytest -q tests/unit/test_parity_command.py
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos quality docs --json
```

Observed results:

- The adopter capability profile test failed before the implementation and
  passed after the mode-aware advisory split.
- The shadow prove-state normalization test failed before the adapter change
  and passed after projection normalization.
- Focused schema, parity projection, and adopter CLI regression set returned
  `35 passed`.
- Ruff on the changed implementation and test files returned
  `All checks passed!`.
- Fresh alphasim-dmgr shadow parity returned `ok=true`, `state=matched`, and no
  required gaps.
- Generic parity gaps returned `ok=true`, `state=clean`, `gap_count=0`.
- alphasim-dmgr parity gaps returned `ok=true`, `state=clean`, `gap_count=0`.
- Full parity command tests returned `43 passed`.
- Claim, schema, and docs quality gates all returned `ok=true` with no required
  gaps.

Tracked parity freshness now binds both parity records to product code HEAD
`5c8fed87ed47e311691752998f4aaec10246e514`. The alphasim-dmgr record is backed
by the fresh matched shadow run above. The generic record remains the product
parity-gaps freshness record used by product report and closeout; it is not a
new embedded-shadow execution claim.

The boundary condition remains unchanged: this addendum does not claim hosted
CI, remote publication, alphasim-dmgr raw/cache parity, alphasim-dmgr domain
backend retirement parity, or di-effect publish readiness.
