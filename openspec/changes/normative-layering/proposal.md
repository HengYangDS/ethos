# Proposal

## Why

The owner decided D3 on 2026-10-27 for design revision 4.1, kept in revision 5.1: a document is normative only if it is a PDC carrier or a higher owner links it as a subject's owner. Eleven policy documents in `docs/governance/` (1,136 nonblank lines) declare `role: policy`, yet no higher owner names them. They restate the PDC, accepted specs and rules, and they drift from the code.

Read-only audits of 2026-10-28 placed each of their 412 statements:

- **Covered.** 313 already have a normative owner, so the document only repeats it.
- **Stale.** 22 are false today. Examples: a profile field for state roots, gate descriptors with output-shape and exit-semantics fields, the "four irreducible anchors", seven evidence classes, and a CI parity inventory that is not checked.
- **Unique.** 35 obligations still hold and have no other owner, and 19 statements of explanation, reference or procedure have no other home.
- **Dropped.** 23 are self-descriptions, or classifications that nothing reads.

`ethos context` serves sections of three of these documents to agents as product guidance (`src/ethos/repository/context.py`), so stale text reaches them. The carriers that explain the hierarchy are themselves out of date:

- the rules index names record fields that the eight rules do not use;
- `system/derivations.md` derives from principles that `system/axioms.md` does not contain;
- three `system/*.toml` headers cite TP tables that do not exist;
- the module layout rule names a retired gate and a module that never existed.

## What Changes

- **Eleven documents retire.** authority, product-boundary-convergence, standards-adoption-policy, skills, openspec-governance, independent-verification-adoption, forge-provider-contract, release-governance, repository-profile-contract, config-boundary-model and adopter-boundary-and-retirement each give back every statement:
  - a covered statement becomes a link to its owner;
  - a unique obligation moves to its owner;
  - explanation, reference and procedure move to an existing document or a new how-to;
  - a false statement is dropped, with its evidence.
- **Accepted specs gain the unique obligations.**
  - repository-governance: control-replacement predecessor binding, OpenSpec lifecycle applicability, CI runner and retained-step records, and the comparative-assurance contract of DR-0014;
  - distribution: version compatibility, prerelease stages and release-candidate rules;
  - adapters: Forge review coordinates;
  - quality: the isolated Python static target.
- **proof-hosts currency.** The proof-hosts spec drops the parity, claim-admission, promotion-target and migration-closure statements that describe removed behavior. Two requirements are replaced under true names, and its Purpose is corrected.
- **OpenSpec configuration.** `openspec/config.yaml` states the withdrawn-task form and moves durable design rulings to their owner before archive.
- **New how-tos.** Two guides: independent verification, and release and publication.
- **Existing documents.** command-plane, configuration, adoption-profiles, fleet-and-adopters, generated-artifact-topology, distribution, gate-runner, agent-projections and the glossary gain the moved explanation and reference text.
- **Consumers move in the same Change.** These are the context sources, the required-document list, the Skills rule contract, the wheel and sdist entries, the Skill activation routes, the decision records' `current_owner` pointers, CHANGELOG, CONTRIBUTING, `rules/release.md` and every incoming link.
- **Governance documents.** The Docs Registry takes `role: policy`, and the governance index lists the documents that remain.
- **Rules, system and metadata.** The rules index names the fields the rules use. `module-layout.md` drops its retired gate and wrong module paths. `system/derivations.md` is deleted. The axioms cite the PDC. The `system/*.toml` headers cite their current owners. The unused `rego` carrier goes, and so do four `.ethos/rules.toml` tables that nothing reads. The overdue retained history record retires by its exit condition, and the link-check configuration stops citing a retired principle.
- **CHANGELOG.** One entry under `[Unreleased]`.

Out of scope:

- mechanical reference checks, owned by `knowledge-checks`;
- the quality and repository-paradigm wording and the branch roles, owned by `shared-quality-obligations`; this Change only adds one quality requirement;
- `docs/architecture/runner-and-mutation.md`, owned by `one-proof-per-change`, except one link repaired with that owner's agreement;
- the kernel role set and the product defects the audits found (listed in the design), which go to the product lane.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: obligations from the retired policy documents become requirements.
- `distribution`: version, prerelease and release-candidate rules become requirements.
- `adapters`: Forge review observation coordinates become a requirement.
- `quality`: the isolated Python static check's declared target becomes a requirement.
- `proof-hosts`: requirements that describe removed parity and claim admission are corrected.

## Impact

- Python product code changes in three consumers (`repository/context.py`, `repository/audit.py`, `repository/policy/rules/compile.py`), with a net reduction of lines.
- The wheel and sdist ship five fewer documents. `ethos context` serves PDC and rule sections in their place, with the same reader roles.
- Adopter bindings do not change.
- Restores documentation-comprehension 12.3 and the ETHOS side of 12.3.3 (DR-0016). 12.4.1 moves to `knowledge-checks`.
