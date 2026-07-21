## Context

MetricContract v3 bound fixed carrier-byte ceilings and correctly exposed the
missing pre-read/native boundary. It did not bound parser amplification. On
July 21, 2026, independent review demonstrated that the INI implementation
copies every `[DEFAULT]` key into every section before canonical framing. A
9,590-byte carrier with 700 defaults and 700 sections reached 77.4 MiB Python
peak, emitted a 20,489,335-byte canonical stream, and took 2.87 seconds. The
reader/native bounded GREEN is therefore rejected and remains uncommitted
experiment history. The v3 metric-contract and diagnostic-test commits already
on this Lane remain visible migration input and must be superseded atomically;
they are not accepted C1 completion.

The same review accepted UTF-8 footprint/control and C4 as linear under their
fixed byte ceilings. It required isolation for INI and recommended isolation for
all complex parser/object-graph providers. The planning workload contains 2,889
all-worker starts versus 873 static-hybrid starts, a 69.8 percent reduction.
Cold-start latency is platform evidence to remeasure at acceptance, not a fixed
design constant or a reason to weaken the reviewed boundary.

## Decisions

1. **MetricContract v4 supersedes bounded-only v3.** The registry wire becomes
   `ethos-source-budget-metrics-v4`; every atom has `contract_version = 4` and
   required `execution_mode`, `max_carrier_bytes`, `execution_contract_id`, and
   `execution_contract_digest`. Existing Budget Contract v2 profile and
   contract ids keep their `*-v2` names. Complete v3 payloads fail closed.

2. **Routing is parser-static, never caller-selected.** The only admitted map
   and mode-to-family identity are:

   | Execution | Execution contract id | Exact parser ids |
   | --- | --- | --- |
   | `bounded_in_process_v1` | `ethos-source-budget-execution:bounded-in-process-v1` | `utf8-footprint`, `utf8-control`, `diagram-contract` |
   | `isolated_worker_v1` | `ethos-source-budget-execution:isolated-worker-v1` | `python-tokenize`, `json-stdlib`, `tomllib`, `pyyaml-safe`, `configparser`, `jinja2`, `shell-lexical` |

   One parser id has one execution tuple `(execution_mode,
   max_carrier_bytes, execution_contract_id, execution_contract_digest)` across
   every role, profile, metric, and parser version. Path, carrier, role, profile,
   metric, caller, and runtime overrides are forbidden.

3. **Carrier ceilings do not change.** `utf8-footprint` remains 262,144 bytes,
   Python remains 65,536 bytes, and every other provider remains 32,768 bytes.
   These are execution inputs, not budget allowances, and cannot rise from
   repository observations.

4. **Execution identity has one pure-kernel owner.**
   `packages/ethos-core/src/ethos_core/contracts/source_budget/measurement/execution.py`
   owns the typed descriptor, the two id constants, mode-to-id validation,
   canonical compact sorted-key UTF-8 JSON, and SHA-256. The descriptor schema is
   `ethos-source-budget-execution-descriptor-v1`. Every descriptor binds
   `execution_contract_id`, `execution_mode`, and `max_carrier_bytes`; an
   isolated descriptor additionally binds exact
   `ethos-source-budget-worker-protocol-v1` and
   `ethos-source-budget-worker-resource-profile-v1` id/digest references. The
   bounded object has exactly those four top-level properties. The isolated
   object adds exactly `worker_protocol` and `resource_profile`, each an object
   containing exactly `id` and `digest`. All descriptor models reject additional
   properties, `null`, omission-backed defaults, and defaulted values. The
   id names one execution family while the digest names a parameterized instance,
   so current policy has exactly four execution digests: bounded 32 KiB, bounded
   256 KiB, isolated 32 KiB, and isolated 64 KiB. Parser/version, grammar,
   normalization, metric coordinates, role, profile, carrier, and path are
   excluded from this digest and bound separately by provider descriptor v2.
   Metric atoms store the id/digest; provider, registry, resolved, native,
   carrier, and snapshot identities consume them. Vector values/digest remain
   independent when admitted metric values do not change. The public helper
   returns `(mode, ceiling, id, digest)` in that exact order.

5. **Parent carrier admission is common to both modes.** The parent resolves the
   complete provider/execution descriptor before opening bytes, rejects initial
   oversize before the first `os.read`, performs one read of at most
   `min(before_size + 1, limit + 1)`, checks post-read size before ordinary
   drift, and retains one content object no larger than `limit + 1`. Direct
   bytes and the execution tuple are rechecked before either in-process parse or
   worker spawn. Mode selects only the parsing location. The bounded parsing path
   remains deliberately narrow: only the three reviewed linear parser ids run in
   process.

6. **Complex providers use one-shot isolation.** One carrier produces one child
   process, one request, one typed response, and EOF/exit. There is no pool,
   batch, broker, persistent state, or in-process retry. The worker receives no
   repository path, root, environment authority, or file descriptor for source
   content; only parent-admitted bytes and typed identities.

7. **The worker protocol is strict and bounded.** Its pure-kernel descriptor is
   implemented before policy v4 is minted, while request/result/frame behavior
   remains a separate RED/GREEN step. Protocol v1 uses distinct
   request/result magic, big-endian 32-bit lengths, canonical JSON headers, and
   raw request content. Header bytes are capped at 32 KiB, total stdin at
   320 KiB, and total response/result at 64 KiB. Duplicate keys, non-canonical
   JSON, wrong version/magic, truncation, overclaimed lengths, extra responses,
   and trailing bytes fail closed. Request and result bind content, resolved
   contracts, provider identity, execution identity, and request digests.

8. **Parent and child both verify authority.** Before spawn, the parent checks
   exact contracts, provider descriptor, execution descriptor, content SHA, and
   ceiling. After resource setup and before parsing, the child repeats those
   checks. The parent never trusts child objects: it reconstructs and validates
   `NativeMeasurement`, all echoed digests, coordinates, and measurement digest
   using the trusted request contracts.

9. **The supervisor enforces a fixed, digest-bound resource profile.** The
   initial profile is
   CPU soft/hard 5/6 seconds, parent wall deadline 8 seconds, 128 MiB RSS with
   10 ms observation, Linux address-space cap 512 MiB, NOFILE 32, NPROC 1,
   CORE 0, regular-file FSIZE 0, request/header/output limits above, no stderr,
   private mode-0700 HOME/TMP/cwd, `sys.executable -I -B -X utf8`, closed file
   descriptors, and a new session. Violation causes process-group TERM, a
   100 ms grace, KILL, pipe close, and bounded wait/reap.

10. **Platform claims remain truthful.** Linux uses kernel CPU/address-space/
    descriptor/process limits plus `/proc` telemetry. Darwin has no independent
    kernel-hard absolute AS/RSS limit (`RLIMIT_AS` aliases `RLIMIT_RSS`), so it
    uses kernel CPU/FD/process/core/file limits plus `libproc` RSS observation.
    Before the parent writes any request bytes, the first successful pre-request
    `PROC_PIDTASKINFO.pti_virtual_size` sample becomes an immutable baseline;
    every 10 ms sample above baseline plus 536,870,912 bytes trips the resource
    boundary. Missing baseline/telemetry reports
    `source_budget_worker_isolation_unsupported`. This watchdog is not described
    as seccomp/container or a kernel-hard absolute memory sandbox.

11. **No fallback and stable gaps have exact meanings.** A provider declared
    isolated never retries through the bounded engine. Parent-only outcomes are
    exactly `source_budget_worker_unavailable`,
    `source_budget_worker_isolation_unsupported`,
    `source_budget_worker_timeout`,
    `source_budget_worker_resource_exhausted`,
    `source_budget_worker_output_exceeded`,
    `source_budget_worker_protocol_invalid`, and
    `source_budget_worker_failed`. Child results admit only the finite native
    vocabulary specified by the delta contract: eight unsuffixed codes, two
    dependency suffixes, and seven isolated-provider suffixes. Unknown or
    malformed gaps are protocol-invalid. Only the parent carrier layer appends a
    validated repository-relative path. The bounded providers are a different
    descriptor-declared capability, not a fallback.

12. **Snapshot semantics remain all-or-nothing.** Any oversize, worker,
    protocol, parser, or resource gap removes the carrier result and complete
    snapshot. Public gaps contain no PID, signal, absolute path, observed size,
    threshold, bytes, or exception text; measurement adds only the governed
    repository-relative path.

## Rejected Alternatives

- Bounded-only execution: rejected by demonstrated INI multiplication.
- Isolating every provider: safe but wastes 69.8 percent of planned worker starts on
  providers independently accepted as linear.
- Lowering only the INI ceiling or banning defaults: changes the fixed contract
  or measurement semantics instead of bounding execution.
- Persistent pools, request batches, and fork brokers: mix carrier state and
  cumulative resource accounting and violate one-carrier/one-process v1.
- `communicate()` with a timeout: buffers unbounded output and is not isolation.
- Container/cgroup/Rust-helper expansion: stronger sandboxing but a new
  portability and supply-chain program; reserve it for a successor if the
  stdlib/POSIX design fails independent review.

## Risks And Mitigations

- **Worker cold-start cost.** Static hybrid routing removes linear providers
  from the worker path. Performance remains evidence, not a reason to weaken
  limits or add persistence.
- **Darwin sampling overshoot.** Small carrier ceilings, hard CPU/process/file
  limits, an absolute 128 MiB RSS watchdog, the 512 MiB pre-request-baseline VMS
  growth tripwire, 10 ms telemetry, process isolation, group kill, and
  adversarial tests bound the failure intent. The claim explicitly excludes a
  kernel-hard absolute RSS/AS guarantee.
- **Forged execution identity.** Parent and child recompute repository-owned
  descriptors and reject any atom/header/result mismatch.
- **Child output or descendant escape.** NPROC, independent session, bounded
  nonblocking pipe reads, process-group TERM/KILL, and unconditional reap are
  required and tested.
- **Half-migrated wire.** v3 fails closed; policy, schemas, provider descriptors,
  grammar digests, tests, and downstream digest goldens advance atomically.

## Acceptance

- Static hybrid MetricContract v4 and provider descriptor v2 are exact and
  immutable.
- Worker protocol/frame and parent replay pass strict contract tests.
- No parent import or runtime path can execute a provider declared isolated in
  process.
- CPU, memory, wall, output, protocol, FD/process, kill/reap, and capability
  failures map to stable redacted gaps with no fallback or partial result.
- Exact-limit content succeeds; limit-plus-one fails before parsing.
- An exact-ceiling INI amplification carrier is contained and terminates without
  harming the parent or producing a partial measurement.
- Current and immutable-baseline inventories show no new oversize gap and retain
  the known YAML graph-safety gap.
- v1 policy/debt/terminal targets and per-file ELOC remain unchanged and
  authoritative; v2 remains inactive.
- Before implementation/proof is claimed, Claim promotion targets include the
  execution owner, worker contract package, protocol schema, protocol/frame
  tests, supervisor test, and architecture boundary test.
