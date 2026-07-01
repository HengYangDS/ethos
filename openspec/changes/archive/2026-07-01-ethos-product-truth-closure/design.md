# Design: Product Truth Closure

## Package Ontology

`ethos-contracts` owns the provider-neutral package ontology contract. Runtime
self-audit reads that contract instead of duplicating package lists in
governance code. This keeps target package homes, migration-host packages,
distribution adapters, lifecycle labels, and migration dispositions aligned.

Physical target homes are not the same as completed migration. ETHOS reports:

```text
physical_target_homes_present = true
migration_status = in_progress
migration_complete = false
```

until migration hosts are moved, frozen, or retired through parity evidence.

## Command Example Governance

Command examples remain part of current docs governance. The command-example
checker distinguishes:

- retired root commands;
- unknown non-ETHOS roots;
- unknown `ethos ...` subcommands;
- missing required product examples.

This makes public command-plane drift visible without turning historical
evidence into current workflow requirements.

## Scaffold DX

`ethos init --apply` and `ethos adopt --apply` should behave as users read
them: explicit apply performs writes. `--dry-run` remains useful for planned
mode, but it must not override explicit apply.

Generated scaffolds include enough governance files for immediate diagnosis:
AGENTS, CONTRIBUTING, CHANGELOG, `.ethos/`, official OpenSpec records,
repo-local skills, docs, claims, evidence placeholders, and ignored local state.

Fresh directories may not yet be Git repositories. `ethos status --root` returns
schema-valid JSON with `git_repository_missing` rather than raising a subprocess
exception. This keeps the user in the ETHOS command plane for the next action.

## Proof Semantics

`ethos prove --full` is a release-grade path and must not claim proof from
planned gate rows alone. It reports `full_proof_requires_execute` unless
`--execute` is provided.

Daily proof can remain fast and planned where appropriate; full proof carries
the stronger evidence requirement.

## Worktree Safety

The implementation happens in `work/product-truth-closure`. Other linked
Work Lanes are observed only through git worktree metadata. ETHOS must not
read, clean, retire, or mutate foreign Work Lane contents as part of this
change.
