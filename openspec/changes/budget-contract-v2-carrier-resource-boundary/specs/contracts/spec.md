## ADDED Requirements

### Requirement: Versioned Static Hybrid Execution Contract

ETHOS SHALL admit Budget Contract v2 native measurement only when every resolved
provider has an exact MetricContract v4 execution identity selected by the
repository-owned provider descriptor rather than by a path or caller.

#### Scenario: Metric atoms bind one provider execution contract

- **WHEN** a metric registry is loaded or one carrier profile is resolved
- **THEN** every atom SHALL declare contract version 4, an admitted execution
  mode, a strict positive carrier-byte ceiling, an execution-contract id, and a
  canonical execution-contract digest
- **AND** the complete tuple SHALL be exactly `(execution_mode,
  max_carrier_bytes, execution_contract_id, execution_contract_digest)` and the
  public helper SHALL return it in that order
- **AND** every atom for one parser id SHALL use that same complete tuple across
  roles, profiles, metrics, and parser versions
- **AND** `bounded_in_process_v1` SHALL map only to parser ids
  `utf8-footprint`, `utf8-control`, and `diagram-contract` and execution id
  `ethos-source-budget-execution:bounded-in-process-v1`
- **AND** `isolated_worker_v1` SHALL map only to parser ids `python-tokenize`,
  `json-stdlib`, `tomllib`, `pyyaml-safe`, `configparser`, `jinja2`, and
  `shell-lexical` and execution id
  `ethos-source-budget-execution:isolated-worker-v1`
- **AND** ceilings SHALL be exactly 262,144 bytes for `utf8-footprint`, 65,536
  for `python-tokenize`, and 32,768 for every other parser id
- **AND** an execution digest SHALL be SHA-256 over canonical compact sorted-key
  UTF-8 JSON whose schema is `ethos-source-budget-execution-descriptor-v1` and
  whose fields bind mode, id, and ceiling; isolated descriptors SHALL additionally
  bind the exact worker-protocol id/digest and resource-profile id/digest
- **AND** a bounded descriptor SHALL have exactly the four top-level properties
  `schema`, `execution_contract_id`, `execution_mode`, and `max_carrier_bytes`
- **AND** an isolated descriptor SHALL have exactly those four properties plus
  `worker_protocol` and `resource_profile`; each added property SHALL be an
  object with exactly `id` and `digest`, and no descriptor/property MAY contain
  an extra member, `null`, omitted default, or defaulted value
- **AND** execution descriptors SHALL exclude parser/version, grammar,
  normalization, metric coordinates, role, profile, carrier, and path; provider
  descriptor v2 SHALL bind those identities separately
- **AND** those fields SHALL enter provider, registry, resolved, native,
  carrier, and snapshot identities without changing vector values/digest
- **AND** v3, missing, forged, mixed, defaulted, overridden, or unknown execution
  declarations SHALL fail closed.

### Requirement: Common Parent Carrier Admission

ETHOS SHALL bound every regular carrier in the parent before either in-process
parsing or isolated-worker spawn; execution mode SHALL select only the parsing
location.

#### Scenario: Either execution mode uses the same bounded parent read

- **WHEN** a classified regular carrier selects either admitted execution mode
- **THEN** ETHOS SHALL resolve the exact provider/execution descriptor before
  opening content
- **AND** initial size above the ceiling SHALL fail before the first `os.read`
- **AND** the parent SHALL retain one content object of at most `limit + 1`
  bytes, check post-read oversize before ordinary drift, and preserve no-follow,
  fingerprint, path-entry, close, and resource-failure checks
- **AND** direct bytes SHALL be rechecked before bounded parse or worker spawn
- **AND** an oversize or changed carrier SHALL expose no partial measurement or
  complete snapshot.

### Requirement: Bounded Linear Provider Admission

ETHOS SHALL run only the independently accepted linear providers in process and
SHALL bound their content before allocation beyond the admitted carrier buffer.

#### Scenario: A bounded carrier is read once under its descriptor ceiling

- **WHEN** a carrier admitted by the common parent boundary selects
  `bounded_in_process_v1`
- **THEN** only the three exact bounded parser ids SHALL execute in process
- **AND** direct bytes and the complete execution tuple SHALL be rechecked before
  bounded provider execution
- **AND** an oversize or changed carrier SHALL expose no partial measurement or
  complete snapshot.

### Requirement: Isolated Complex Provider Execution

ETHOS SHALL execute every complex parser in a one-carrier/one-process
`isolated_worker_v1` boundary with no in-process fallback.

#### Scenario: One carrier is processed by one bounded worker

- **WHEN** a resolved provider selects `isolated_worker_v1`
- **THEN** the parent SHALL use the common bounded carrier admission, hash those
  bytes, verify provider/execution identity, and send no repository path or
  source descriptor to the child
- **AND** the child SHALL establish its resource limits before importing the
  isolated engine and SHALL revalidate the same bytes, contracts, provider, and
  execution identity before parsing
- **AND** CPU, wall, memory intent, descriptors, processes, file output, request,
  response, protocol, and result sizes SHALL be fixed and versioned
- **AND** any spawn, capability, timeout, resource, output, protocol, crash, or
  signal failure SHALL return a stable redacted gap and SHALL NOT retry through
  an in-process engine.

#### Scenario: Worker gaps use one finite public vocabulary

- **WHEN** the parent maps a worker/supervisor failure
- **THEN** it SHALL return exactly one of `source_budget_worker_unavailable`,
  `source_budget_worker_isolation_unsupported`, `source_budget_worker_timeout`,
  `source_budget_worker_resource_exhausted`,
  `source_budget_worker_output_exceeded`,
  `source_budget_worker_protocol_invalid`, or `source_budget_worker_failed`
- **AND** a child result gap SHALL be limited to the unsuffixed exact set
  `source_budget_native_contract_invalid`,
  `source_budget_native_execution_contract_invalid`,
  `source_budget_native_provider_signature_mismatch`,
  `source_budget_native_runtime_unsupported`,
  `source_budget_native_text_invalid_utf8`,
  `source_budget_native_text_embedded_bom`,
  `source_budget_native_resource_exhausted`, and
  `source_budget_native_carrier_bytes_exceeded`; dependency mismatch SHALL allow
  only suffix `jinja2` or `pyyaml`, and conformance/parse/unavailable SHALL allow
  only suffix `ini`, `jinja`, `json`, `python`, `shell`, `toml`, or `yaml`
- **AND** only the parent carrier layer MAY append one validated
  repository-relative path as the final public component.

#### Scenario: The worker protocol and result are fully revalidated

- **WHEN** a worker request or response crosses the process boundary
- **THEN** ETHOS SHALL enforce one versioned length-framed canonical message,
  reject duplicate/non-canonical/truncated/overlong/trailing data, and bind the
  request, content, resolved contracts, provider identity, and execution
  identity digests
- **AND** a result SHALL contain exactly one typed success or one admitted child
  gap
- **AND** the parent SHALL reconstruct and validate the complete native
  measurement from trusted request contracts before exposing success
- **AND** worker output SHALL never expose PID, signal, path, observed size,
  threshold, bytes, or exception text.

### Requirement: Platform-Truthful Resource Supervision

ETHOS SHALL distinguish resource-fault isolation from a general arbitrary-code
sandbox and SHALL fail closed when a required platform capability is absent.

#### Scenario: Linux and Darwin enforce the same resource intent honestly

- **WHEN** isolated execution starts on a supported POSIX platform
- **THEN** the resource profile SHALL fix CPU soft/hard to 5/6 seconds, parent
  wall to 8 seconds, RSS to 134,217,728 bytes sampled every 10 ms, NOFILE to 32,
  NPROC to 1, CORE to 0, and regular-file FSIZE to 0
- **AND** protocol limits SHALL fix header to 32,768 bytes, total stdin to
  327,680 bytes, and total result to 65,536 bytes
- **AND** Linux SHALL use a 536,870,912-byte address-space limit and `/proc`
  telemetry
- **AND** on Darwin the parent SHALL obtain the first successful pre-request
  `libproc` `pti_virtual_size` sample as an immutable baseline, SHALL write no
  request bytes before it exists, and SHALL trip on any 10 ms sample above
  baseline plus 536,870,912 bytes without claiming a kernel-hard absolute AS/RSS
  bound
- **AND** missing telemetry, limit, session, or kill/reap capability SHALL report
  `source_budget_worker_isolation_unsupported` rather than silently weakening
  execution.

### Requirement: C1 Preserves Later-Stage Authority Boundaries

ETHOS SHALL keep source-budget authority and later migration stages unchanged
while the carrier execution boundary is implemented and reviewed.

#### Scenario: Hybrid isolation is accepted without activating Budget Contract v2

- **WHEN** C1 passes its contract, adversarial, platform, inventory, and proof
  gates
- **THEN** v1 source-budget and per-file ELOC SHALL remain unchanged and
  authoritative
- **AND** v2 SHALL remain inactive
- **AND** the carrier manifest SHALL remain
  `ethos-source-budget-carriers-v2`/version 2, all 16 existing profile ids SHALL
  retain their `*-v2` names, and all 28 existing contract ids SHALL retain their
  `*-v2:*` names while only the metric registry wire advances to v4
- **AND** immutable Git replay, provider-gap repair, vector policy, Debt v2,
  changed-scope admission, dual control, cutover, global v1 LOC retirement, and
  remote publication SHALL require their later governed Changes.
