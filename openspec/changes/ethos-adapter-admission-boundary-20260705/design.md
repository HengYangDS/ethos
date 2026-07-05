## Context

The official OpenSpec boundary is `ethos-repository`: repository governance,
binding taxonomy, and coupling-audit semantics. The ETHOS repo-local product
boundary remains source, tests, schemas, current docs, claims, and evidence;
OpenSpec is the carrier for this non-trivial governance semantic change.

## Design

The coupling registry remains the single machine-readable place where binding
classification is inspected. This change does not add another registry. It adds
one field to adapter/profile entries: `admission`, containing:

- `authority_ref`: where the admission rule is grounded.
- `truth_boundary`: fixed to `profile_or_adapter`.
- `decision_state`: fixed to `admitted` for registry participation.

`ethos quality coupling-audit --json` now fails when an adapter/profile binding
is missing admission, claims repository truth, or stays in a draft decision
state. The JSON schema accepts the same object and rejects other shapes.

## Alternatives

A vendor-name denylist was rejected because it would encode surface names as a
shadow authority and would require endless updates. A new adapter decision file
was also rejected because it would duplicate the existing binding registry. The
minimal durable shape is to attach admission metadata to the registry entry that
already owns binding classification.

## Proof Strategy

- Unit tests cover the nominal registry and failure modes.
- `ethos quality coupling-audit --json` validates the implementation against
  `coupling-audit.schema.json`.
- `ethos openspec --lifecycle --json` validates the active carrier and claim
  binding.
- `ethos prove --execute --expect-head <HEAD> --json` binds the full proof to
  the commit that promotes the change.
