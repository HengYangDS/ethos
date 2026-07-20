## Design

The helper boundary is deliberately narrow: it creates literal test topology
and commits literal test files. It does not parse, classify, normalize, or
assert product payloads. Each test continues to own its command invocation and
public contract assertions.

The workspace-status sample is already the canonical full valid envelope. A
negative UI-projection test copies that literal sample and adds only the
forbidden field; this keeps the negative case focused on the relevant schema
constraint instead of maintaining a second stale complete fixture.

Formatter-clean scoped ELOC is the measure. The lane will retain only a net
source deletion across its changed test surfaces after all lifecycle carriers
are included.

## Risks and rollback

A broad helper could hide command-specific setup. The helper is restricted to
stable topology and commit mechanics; focused tests retain the behavioral
assertions. Revert this lane if those focused tests or full proof regress.
