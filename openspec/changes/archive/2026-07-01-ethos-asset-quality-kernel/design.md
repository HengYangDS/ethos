## Design

`ethos-quality` is a semantic package, not an executor. It owns asset classes,
gate descriptors, docs quality profiles, proof-state lattice, and tool adapter
profiles. Execution remains in adapters, repository lifecycle remains in
`ethos-repository`, and provider-neutral contracts remain in `ethos-contracts`.

The package depends only on `ethos-core` and `ethos-contracts`. It must not
import repository lifecycle, adapters, CLI, subprocess, SQLite, or adopter
domain terms.

## Boundaries

- `ethos-quality`: quality meaning and policy shape.
- `ethos-repository`: lifecycle orchestration and mutation admission.
- `ethos-contracts`: schema and provider-neutral record shapes.
- `ethos-adapters`: mature tool execution and provider translation.
- `ethos-test`: conformance, parity, and shadow fixtures.

## Migration

Existing repository gate registry remains temporarily callable from
`ethos-repository` for compatibility, but it delegates gate descriptors to
`ethos-quality`. New quality commands compose reports from `ethos-quality`.
