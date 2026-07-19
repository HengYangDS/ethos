## 1. Carrier Contract RED

- [ ] 1.1 Add failing tests for frozen/extra-forbid models, duplicate IDs and
  matchers, invalid paths, exact-one classification, explicit exclusions,
  unsupported extensions, and deterministic digest identity.
- [ ] 1.2 Run the carrier contract and adapter tests and verify they fail because
  the new contract modules do not exist.

## 2. Metric Contract RED

- [ ] 2.1 Add failing tests for required metric identity, profiles, dangling
  references, duplicate coordinates, invalid grammar digests, BPE/model-token
  rejection, non-compensation, and deterministic digest identity.
- [ ] 2.2 Run the metric tests and verify they fail because the new contract
  module does not exist.

## 3. Minimal Contract Implementation

- [ ] 3.1 Implement frozen strict contract models, symmetric fail-closed load
  envelopes, canonical digest helpers, pure exact-one classification, inventory
  classification, and metric-profile resolution.
- [ ] 3.2 Keep the implementation content-free: do not import parsers, read
  carrier bytes, calculate measurements, or modify v1 gate/report routing.

## 4. Declarative Manifests And Schemas

- [ ] 4.1 Add independent carrier and metric policy manifests; do not reuse the
  v1 format-selection taxonomy as v2 truth.
- [ ] 4.2 Add the two compact JSON Schemas and prove they match generated model
  projections exactly.

## 5. Repository Classification Verification

- [ ] 5.1 Classify the current Git-present maintained inventory exactly once or
  through an explicit reviewed exclusion, with deterministic results under
  reversed input order.
- [ ] 5.2 Run focused contract, adapter, schema, config, and lint checks to GREEN.

## 6. Governance Closeout

- [ ] 6.1 Update the bounded claim and Chronicle with reviewed results and
  explicit T2/T3 boundaries.
- [ ] 6.2 Run strict OpenSpec, claims, plan, parity, and final HEAD-bound proof;
  complete tasks and prepare official archive inputs.
- [ ] 6.3 Archive through the official OpenSpec command, bind the claim to the
  dated archive, regenerate parity, and execute archive-HEAD proof.

## Post-Archive Transition Boundary

Official archive does not itself perform candidate land, accepted-root closeout,
local publication readiness, remote publication, hosted CI, or Work Lane
retirement. Each requires its own current command evidence. Only this owned Lane
may be retired after accepted ancestry proves absorption; foreign Lanes remain
outside this Change's authority.
