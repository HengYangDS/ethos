## Context

Task 3 validates exact provider signatures and maps memory or recursion failures
to stable gaps, but the descriptor reader currently allocates from unbounded
`st_size`, and the native API may run startup conformance and construct parser
state for arbitrary bytes. Catching exhaustion after allocation is not a
resource contract. The repository therefore cannot start immutable historical
replay or activate v2 until the existing canonical prerequisite is implemented.

A read-only inventory on the accepted Task 3 head classified 2,880 carriers and
three reviewed exclusions. The largest current carrier was 201,661 bytes under
`utf8-footprint`; Python was 34,267 bytes; TOML was 22,397 bytes; JSON was
12,255 bytes; shell was 11,472 bytes; YAML was 7,973 bytes; and control files
were below 1 KiB. These observations verify compatibility but do not calculate
or authorize the ceilings.

## Decisions

1. **The resource boundary is part of MetricContract v3.** Every metric atom
   gains required `execution_mode` and `max_carrier_bytes` fields. The registry
   wire id becomes `ethos-source-budget-metrics-v3`, while existing `*-v2`
   profile and contract IDs remain because they identify the Budget Contract v2
   metric domains. Old unbounded registry payloads fail closed; no compatibility
   forwarder or default is allowed.

2. **Bounded in-process execution is the admitted first implementation.** The
   only admitted mode is `bounded_in_process_v1`. The fixed ceilings are:

   | Provider class | Maximum carrier bytes |
   | --- | ---: |
   | `utf8-footprint` | 262,144 |
   | `python-tokenize` | 65,536 |
   | all other current providers, including `utf8-control` | 32,768 |

   These are provider execution contracts, not budget allowances. They cannot
   vary by path, carrier, role, profile, or metric and cannot be inferred from
   the current largest file.

3. **Provider identity binds execution.** The repository-owned provider
   descriptor includes execution mode and ceiling; its descriptor schema and
   grammar digest advance atomically. Registry validation rejects different
   resource contracts for the same parser id/version. Resolved-provider
   admission also requires one complete parser, grammar, normalization, mode,
   and ceiling signature before any bytes are read.

4. **The reader rejects before allocation.** `measure_carrier` resolves the
   metric contracts first. After opening the final object and confirming it is
   regular, `fstat.st_size > limit` fails before the first `os.read`. A permitted
   object is read with a total probe bounded by `limit + 1`; post-read `fstat`
   and the existing path-entry/fingerprint checks detect growth or replacement.
   An oversize reader failure reports only
   `source_budget_measurement_carrier_bytes_exceeded:<relative>`; direct native
   admission reports `source_budget_native_carrier_bytes_exceeded`. Neither gap
   contains exception text, absolute paths, observed sizes, ceilings, bytes, or
   partial measurements.

5. **Native admission independently rechecks the boundary.** Direct
   `measure_native` validates the exact contracts and rejects `len(content) >
   max_carrier_bytes` before dependency/startup conformance, decoding, AST, or
   provider parsing. This prevents callers from bypassing the descriptor reader.

6. **Snapshot semantics remain all-or-nothing.** One oversize carrier produces
   no carrier success and no `MeasurementSnapshot`. Existing sorted complete-gap
   accumulation remains; values, coordinates, and digests are never emitted for
   a partial inventory.

7. **Isolation is a fail-closed alternative, not a fallback.** If independent
   security review finds the byte ceiling insufficient, C1 does not close.
   `isolated_worker_v1` must then be a one-shot bytes-in/typed-result-out worker
   with a versioned protocol, explicit CPU, memory, wall, descriptor/process,
   and output limits, parent-side content/digest revalidation, stable failure
   mapping, and no automatic in-process fallback.

## Rejected Alternatives

- A single repository-wide ceiling: it ignores provider-specific allocation and
  object-graph risk.
- Path or carrier exceptions: they turn execution safety into an allowlist and
  make immutable replay non-portable.
- Deriving limits from current maxima: it rewards growth and silently raises the
  boundary when the repository expands.
- Catching `MemoryError` only: it reacts after the unsafe allocation.
- A timeout-only subprocess: it does not bound memory, descendants, file
  descriptors, protocol bytes, or output.

## Risks And Mitigations

- **File grows after the first stat.** Read no more than `limit + 1`, then check
  the observed post-read size and existing stable fingerprint.
- **Forged or mixed resource fields.** Canonical model replay, registry
  provider-consistency validation, provider descriptor matching, and native
  revalidation all fail closed.
- **Ceiling changes measurement identity.** Metric-registry, resolved-contract,
  native, carrier, and snapshot digests all bind the new fields; vector values
  remain unchanged for identical admitted content.
- **C1 accidentally activates v2.** v1 remains authoritative and v2 remains
  inactive; replay, policy, gates, and cutover are explicitly outside scope.

## Acceptance

- All metric atoms use wire/contract version 3 and a reviewed resource contract.
- No current or immutable-baseline measured carrier exceeds its provider limit.
- An oversize worktree object is rejected before the first read and direct native
  bytes are rejected before startup conformance or parsing.
- Limit-plus-one growth is detected without retaining more than `limit + 1`
  bytes.
- Any oversize carrier invalidates the complete snapshot.
- Existing YAML graph-safety failure is unchanged.
- v1 policy, debt, terminal targets, per-file ELOC, and authority are unchanged.
