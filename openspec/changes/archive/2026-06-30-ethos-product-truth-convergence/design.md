## Design

ETHOS now distinguishes three product states:

1. Target product homes: buildable packages that define the future ontology.
2. Migration hosts: existing implementation packages that remain active until
   parity-driven migration is complete.
3. Adopter profiles: repository-specific governance such as adopter adopter-domain storage and
   reference-adopter compatibility, which must not enter product core.

The public command plane gains `ethos parity` as a product migration control
surface. The command emits the capability ledger, reports remaining migration
gaps, and plans adopter shadow parity without executing risky mutation.

Self-audit has a shallow OpenSpec shape mode and a deep official OpenSpec mode.
Daily `ethos prove` and `ethos report` use shape mode; `ethos self audit`,
`ethos self openspec`, and full proof retain deep official validation.

Internal ETHOS proof gates run in-process when the gate command is
`python -m ethos.cli ... --json`. External providers still execute through the
subprocess adapter.

## Safety

- Migration hosts remain in place; no embedded/adopter implementation is
  deleted automatically.
- Provider execution is forbidden in semantic target packages by architecture
  tests.
- Adopter names are forbidden from product Python code except the explicit
  parity contract ledger.
- Deep OpenSpec validation remains an explicit gate and is not removed.
