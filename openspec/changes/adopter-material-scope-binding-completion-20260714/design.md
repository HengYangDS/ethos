## Context

OpenSpec owns its official artifacts and CLI lifecycle. ETHOS owns the
repository-governance companion contract around those artifacts. An adopter
must not be able to bypass lifecycle by configuring only native proof gates,
nor borrow any arbitrary active Change for unrelated material work.

## Design

`[openspec].material_paths` is an explicit, non-empty profile declaration of
portable repository-relative glob patterns. An unarchived Change may add a
strict `scope.toml` companion with its covered paths. It is not official
OpenSpec metadata and does not alter the official workflow schema.

The lifecycle adapter receives the official list selection and creates one
scope-binding read model. `lane prewrite` supplies its requested paths; `plan
--changed` and `prove` supply the dirty scope. All three surfaces expose the
same stable uncovered diagnostic:
`openspec_material_path_uncovered:<path>`.

Only a material request consisting of precisely an official active Change's
otherwise absent `openspec/changes/<id>/scope.toml` receives a bootstrap
admission. The companion then has to validate and cover itself. Missing or
invalid companions on unrelated official Changes remain diagnostics; they do
not invalidate a path covered by another valid companion.

## Alternatives

- **Private DDWG validator/schema:** rejected because the cross-adopter
  admission rule belongs to ETHOS and would fork product semantics.
- **Treat every active Change as universal coverage:** rejected because it
  permits unrelated material changes to borrow a carrier.
- **Add lifecycle to code-correctness gates:** rejected because gate-floor
  configuration cannot own Change lifecycle truth.

## Proof Strategy

Focused contract, admission, CLI plan/prove, and scaffold tests cover missing,
covered, uncovered, invalid, official-selection, and exact-bootstrap cases.
Strict official OpenSpec validation and lifecycle run separately from the
ETHOS-owned companion validation. An executed proof binds the committed head;
archive, candidate landing, accepted closeout, and publication remain distinct
transitions.

The product change adds typed contracts, a read model, and focused regressions.
Its source-budget debt record preserves the repository baseline and names the
subsequent scope-binding compression wave; it is not a permanent exception.
