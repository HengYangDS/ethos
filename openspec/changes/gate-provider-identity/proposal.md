# Proposal

## Why

A review of the release diff for 0.2.0-beta.11 (every change since `v0.2.0-beta.10`; the tag is
planned for 2026-11-21) returned four leads about two vocabularies that this release adds: the gate
provider catalog and the gap-code registry. A regression reproduced each one before any change:

- A gate could name one provider twice, by its catalog ID and by the legacy name of that ID. The
  gate contract compared the two references as text and accepted the declaration, and the provider
  ran twice. For the source-integrity provider the join then met two reports, kept neither and
  refused with `source_integrity_unproven:<path>`, which names an artifact and not the
  declaration.
- The gate schema held `providers` to the reference form and to unique items, and held
  `verification_providers` to neither. The gate model holds both lists to both.
- The gap registry handed a reader the cached row. A reader that changed the row changed every
  later read in the process.
- The gap registry counts a code as registered when it begins with a family prefix, so an
  undeclared literal under a broad prefix passes without a row.

## What Changes

- A gate declaration that names one provider twice, by one text or by an ID with its legacy name,
  is refused as an invalid gate executor where the declaration is validated, before any gate runs.
- The gate schema holds a verification provider reference to the form and the unique items of a
  provider reference.
- The gap registry returns a copy of a row.
- The family prefixes stay as they are. At the positions that the static test reads, 14 complete
  codes are registered only through a family. In the whole tree, 92 whole literals without a row
  are gap codes by a reading of their sites, and 80 of them stand where the static test does not
  read. That is more than a defect repair before a release holds, so the draft Change
  `gap-code-literals` records the measurement and the next action.

Not breaking: the catalog and the registry ship first in this release, so no released build
accepts a declaration that this Change refuses. The schema's new constraints on a verification
provider are the ones that it already applies to a provider.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: the new requirement `A gate names each provider once`.

The gap registry's copy of a row changes no stated requirement: the kernel's requirement states
which codes are registered and says nothing about a row that the loader returns. The regression
holds the behavior.

## Impact

`src/ethos/contracts/gates.py`, `src/ethos/contracts/codes/gaps.py`,
`system/schemas/kernel/gate.schema.json`, their three test modules, `CHANGELOG.md` and the draft
`openspec/changes/gap-code-literals/`.
