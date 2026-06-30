## Why

ETHOS product migration must stop treating current package folders as the final
ontology. The product repository and alphasim-dmgr embedded implementation have
different strengths, so ETHOS needs a design contract before further code
migration.

## What Changes

- Canonize the product design contract.
- Define the target MECE Python package ontology.
- Define the alphasim-dmgr convergence lifecycle.
- Add the initial capability parity ledger.
- Add the read-only `ethos intake status` and
  `ethos playbooks route --changed` surfaces needed by the design contract.

## Impact

Affected areas are docs, OpenSpec records, architecture tests, focused CLI
surfaces, and playbook routing behavior. This change does not migrate provider
implementations or perform the physical target package split.
