# Design

## Principle

Enterprise-readiness is an aggregate judgment. It reads repository policy,
status, report, parity, claims, generated artifacts, and release policy; it does
not own those facts. Therefore it belongs in the domain layer, not in the
repository layer.

## Minimal Mechanism

- Move `enterprise_readiness_report` to `ethos.domain.readiness.enterprise`.
- Point the CLI surface at the domain aggregator.
- Update unit tests to import the domain owner directly.
- Delete the obsolete repository readiness package rather than preserving a
  compatibility wrapper that would either break import-linter or create an
  unneeded facade.

## Kernel Binding

```text
Subject = quality gate architecture for the ETHOS repository
Commitment = surface -> domain -> adapters -> repository layer contract
Change = enterprise-readiness implementation placement
Evidence = import-linter, focused tests, Ruff, OpenSpec lifecycle, claims
Claim = digest-bound evidence record
Chronicle = this archived carrier and dated evidence
```

## Alternatives

- Add an import-linter exception: rejected because it weakens the hard floor.
- Keep a repository compatibility wrapper: rejected because repository would
  still import upward, or the wrapper would become dead facade debt.
- Move all referenced checks into repository: rejected because status/report
  orchestration belongs above repository truth readers.
