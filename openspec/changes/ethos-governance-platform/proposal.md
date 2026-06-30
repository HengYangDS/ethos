## Why

ETHOS must govern other repositories as a product, not as a local script set.
The previous shape had working release basics but still lacked complete adopter
scaffolding, repo-local skills, fleet/adopter inspection, MECE OpenSpec
families, schema instance validation, and command registry scans over current
documentation.

## What Changes

- Rename the internal project adoption package to `ethos-project`.
- Make `ethos init/adopt` scaffold complete adopter governance surfaces.
- Add `ethos playbooks` for repo-local skills and `ethos fleet inspect` for
  external adopter inspection.
- Split canonical OpenSpec specs into MECE product families.
- Add distribution governance for the npm launcher adapter.
- Strengthen self-audit with playbook, OpenSpec family, command registry,
  claim, and schema instance checks.
- Upgrade standards adapters with lifecycle, input/output contracts, fallback,
  and retirement semantics.

## Capabilities

### Modified Capabilities

- `ethos-kernel`
- `ethos-project`
- `ethos-governance`
- `ethos-workspace`
- `ethos-agent`
- `ethos-distribution`

## Impact

Affected areas include package topology, CLI commands, adoption scaffold,
playbook projection, fleet inspection, governance checks, OpenSpec records,
docs, tests, and release metadata.
