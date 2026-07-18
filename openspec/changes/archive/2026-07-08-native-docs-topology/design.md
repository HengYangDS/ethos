# Design

## Boundary

Documentation topology is a projection over repository truth. It must help
humans and agents find authority, decisions, evidence, reference vocabulary, and
history without pretending that a directory name proves lifecycle state.

The common kernel is therefore minimal:

```text
docs/README.md
docs/decisions/
docs/evidence/
docs/history/
docs/reference/
```

Product roots such as architecture, concepts, governance, plans, research, and
start are extensions. They are not common-kernel obligations for every governed
repository.

## Mechanism

- `ethos_core.contracts.docs.topology` owns the required paths and extension
  root set.
- `ethos adopt` scaffolds the same minimal semantic kernel for adopters.
- `ethos quality docs-topology --json` audits the required kernel and rejects
  unsupported docs `state` values such as `current` and `future`.
- Generated artifact policy denies tracked generated drift under governed docs
  generically instead of naming retired lifecycle roots.
- Command-surface policy uses `governed_docs` and `governed_doc_globs` for the
  active selector vocabulary.

## Net Gain

This deletes misleading entities instead of renaming them. Present repository
truth is bound to HEAD and evidence; intent is carried by OpenSpec, plans,
research, and revisit triggers; documentation directories remain navigation and
boundary surfaces.
