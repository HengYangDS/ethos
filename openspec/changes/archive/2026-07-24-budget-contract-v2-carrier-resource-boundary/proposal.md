# Budget Contract v2 Carrier Resource Boundary

## Why

Task 3 made native measurement deterministic and fail closed, but the first C1
implementation admitted every provider in process behind only a carrier-byte
ceiling. Independent security review rejected that design on July 21, 2026.
The INI provider expands defaults across every section: a 9,590-byte adversarial
carrier produced a 77.4 MiB Python peak, a 20,489,335-byte canonical stream,
and 2.87 seconds of work. A fixed 32 KiB input ceiling therefore does not bound
its parser object graph or CPU cost.

The rejected reader/native bounded GREEN was never committed or promoted. The
MetricContract v3 contract and diagnostic test commits remain in this Work Lane
as explicit migration input; they are not the accepted C1 design and SHALL be
atomically superseded by v4. C1 must remain open and isolate every complex
parser while retaining the simpler bounded path only for providers independently
accepted as linear.

## What Changes

- Advance the metric-registry wire and every atom to v4. Every atom declares a
  required execution mode, fixed carrier-byte ceiling, execution-contract id,
  and execution-contract digest.
- Statically bind parser ids `python-tokenize`, `json-stdlib`, `tomllib`,
  `pyyaml-safe`, `configparser`, `jinja2`, and `shell-lexical` to
  one-carrier/one-process `isolated_worker_v1` execution with contract id
  `ethos-source-budget-execution:isolated-worker-v1`.
- Retain `bounded_in_process_v1` only for parser ids `utf8-footprint`,
  `utf8-control`, and `diagram-contract`, with contract id
  `ethos-source-budget-execution:bounded-in-process-v1`.
- Apply the same descriptor-first, one-`limit + 1` parent read and post-read
  drift checks to both modes; the mode selects only the parsing location.
- Add a repository-owned provider descriptor v2 and execution descriptors. The
  mode cannot vary by path, carrier, role, profile, or metric, and an isolated
  failure never retries in process.
- Add a versioned, bounded bytes-in/typed-result-out worker protocol, parent and
  child signature/ceiling revalidation, resource supervision, process-group
  termination, output limits, and strict parent replay of returned results.
- Keep the original carrier ceilings unchanged: 262,144 bytes for
  `utf8-footprint`, 65,536 for `python-tokenize`, and 32,768 for every other
  parser id.
- Preserve v1 authority, v2 inactivity, all 16 existing `*-v2` profile ids, all
  28 existing `*-v2:*` contract ids, carrier-manifest wire
  `ethos-source-budget-carriers-v2`/version 2, and per-file ELOC.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contracts`: subject=budget-contract-v2-carrier-resource-boundary;
  reuse=extend; change=modify;
  facet:lifecycle=authoring,validation,migration;
  facet:surface=contract,adapter,policy,evidence;
  facet:authority=source,test,config,openspec,claim,evidence.

## Impact

This Change updates the v2 metric wire, execution/provider identity, safe
worktree reader, native routing, worker protocol and supervisor, generated
schemas, focused tests, evidence, and the canonical design/implementation
plans. It adds no source-budget allowance, debt, exclusion, or path override.

Measured current-worktree counts may increase while C1 files are authored.
Acceptance must re-establish a complete classified inventory, three reviewed
exclusions, no new oversize gap, and the existing deterministic YAML graph gap.

## Out Of Scope

- Immutable Git replay, baseline shadow output, provider-gap remediation,
  vector policy, Debt v2, changed-scope admission, dual control, cutover,
  global v1 LOC retirement, or remote publication.
- A persistent worker, request batch, fork broker, subprocess timeout presented
  as isolation, automatic in-process fallback, dynamic resource expansion,
  path/profile/carrier exceptions, or raised carrier ceilings.
- A claim that this worker is a seccomp, container, network, or arbitrary-code
  security sandbox. It is a deterministic parser resource-fault boundary.
