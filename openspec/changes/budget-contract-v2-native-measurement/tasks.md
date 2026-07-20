## 1. Measurement Contract RED

- [x] 1.1 Add failing tests for frozen extra-forbid models, non-negative metric values, stable ordering, coordinate completeness, exact typed/XOR/context-bound non-subclassable load envelopes, and forged native/carrier/snapshot/vector digests.
- [x] 1.2 Run the kernel tests and retain the expected missing-contract failure before adding the production owner.

## 2. Minimal Measurement Contracts

- [x] 2.1 Implement MetricValue, NativeMeasurement, CarrierMeasurement, MeasurementCoordinate, MeasurementSnapshot, canonical digest helpers, and the three fail-closed load envelopes with authoritative context replay for carrier and snapshot success.
- [x] 2.2 Run focused kernel tests to GREEN with statement and branch coverage for the new contract owner.

## 3. Native Provider RED

- [x] 3.1 Encode adversarial cases in one cases.toml test carrier and add failing tests for UTF-8/BOM/CRLF, Python packing/identifiers/literals, structured formatting/duplicates/non-finite/graph safety, Jinja dynamic units/dynamic bytes/static-comment separation and non-finite numeric rejection, Shell-v4 function/case/Zsh/heredoc/no-progress behavior, contextual nested substitution closers and recursion-exhaustion classification, YAML tag-canonical key identity, resource exhaustion, C4 grammar, and exact provider-signature mismatch.
- [x] 3.2 Add failing tests for canonical CPython 3.14 admission, wrong-runtime rejection, dependency-major mismatch, provider conformance fingerprint drift, reproducible grammar descriptors, and removal of the false POSIX-only shell identity.
- [x] 3.3 Run the native tests and retain expected missing-provider failures.

## 4. Native Provider Implementation

- [x] 4.1 Implement canonical-runtime admission, cached provider conformance self-test, strict UTF-8/newline normalization, exact provider dispatch, Python/footprint/Jinja parsing with strict finite canonical JSON, and Shell v4 in declaration-only `measurement/native/shell/__init__.py` plus bounded `core.py` and `grammar.py`; include contextual nested closers, stable memory/recursion-exhaustion gaps, and descriptor cleanup on every exit.
- [x] 4.2 Implement TOML/JSON/YAML/INI/C4 parsing, duplicate/non-finite/tag/graph rejection, YAML tag-plus-canonical key identity with typed entry storage, canonical scalar framing, and semantic-node counting in measurement/native/_structured.py.
- [x] 4.3 Update metric provider versions, reviewed conformance constants, and reproducible grammar digests atomically; bind PyYAML to major 6; reconcile the minimal-adoption base by restoring the product-owned, parse-only Jinja carrier/type/schema without restoring its renderer; repair the stale canonical full-scaffold, overlay, profile, and provider-CI obligations through an explicit repository-governance delta; declare the lazy Jinja parser through one exact package-scoped deptry policy/runner rule; refresh lock/schema metadata; and run fresh native/contract/config/dependency tests to GREEN.
- [x] 4.4 Close every public measurement `MemoryError` boundary without leaking exception text or partial output, close an opened descriptor if registration itself exhausts memory, and make missing or non-directory adoption roots return the stable repository gap before write.

## 5. Descriptor And Snapshot RED

- [x] 5.1 Add failing tests for ancestor/final symlinks, FIFO non-blocking admission, non-regular objects, read/stat errors, ancestor/final entry replacement, same-size rewrites, pre/post fingerprint drift, and stable gap redaction.
- [x] 5.2 Add failing tests for reversed inventory order, classified-only measurement, reviewed-exclusion skipping with complete inventory binding, direct excluded-carrier rejection, one-file failure rejecting the whole snapshot, domain movement, same-domain multi-carrier summation, native/forged-output duplicate coordinates, and raw-versus-normalized digest separation.
- [x] 5.3 Run adapter tests and retain expected missing-orchestration failures.

## 6. Descriptor And Snapshot Implementation

- [x] 6.1 Implement component-by-component descriptor traversal, no-follow final reads, regular-file checks, pre/post state comparison, profile resolution, and fail-closed carrier measurement.
- [x] 6.2 Implement classified-only canonical snapshot ordering, reviewed-exclusion skipping with complete manifest/inventory identity, scope/metric/unit aggregation, complete-gap accumulation, vector digest, and snapshot digest without persistent OS metadata.
- [x] 6.3 Measure the complete current inventory in forward and reversed order and bind adapter/Chronicle report-only reviewed counts, provider coverage, the deterministic current YAML-anchor gap, and digests without persisting counts in MeasurementSnapshot or canonical digests or claiming cross-file Git atomicity.

## 7. Quality And Governance Closeout

- [x] 7.1 Run focused 100 percent statement/branch coverage, v1 source-budget regressions, Python lint/format/ratchet, config/schema/dependency/module-layout checks, and strict OpenSpec/claims/lifecycle validation.
- [x] 7.2 Expand the active claim promotion targets after TDD creates every production/test/corpus owner, complete independent code/spec/security review, refresh generic parity when required, and bind final results and digests into claim and Chronicle.
- [ ] 7.3 Commit the final pre-transition carrier and run exact-HEAD proof; then complete official archive inputs without claiming archive, candidate land, accepted closeout, publication, or Lane retirement prematurely.

## Post-Archive Transition Boundary

Official archive does not itself perform archive-HEAD parity/proof, candidate
land, accepted-root closeout, local publication readiness, remote publication,
hosted CI, or Work Lane retirement. Each requires separate current evidence.
Only this owned Lane may be retired after accepted ancestry proves absorption;
foreign Lanes remain outside this Change's authority.
