# Budget Contract v2 Carrier Resource Boundary

## Why

Task 3 made native source measurement deterministic and fail closed, but a
classified carrier can still cause an unbounded allocation or parser object
graph before `MemoryError` is translated into a stable gap. The canonical
contracts specification already requires a versioned carrier-byte ceiling or an
admitted isolated-execution boundary before v2 activation. The implementation
plan incorrectly proceeds directly to Git replay without closing that
prerequisite.

## What Changes

- Advance the metric-registry wire contract to v3 and require every metric atom
  to declare `execution_mode = "bounded_in_process_v1"` and a strict positive
  `max_carrier_bytes`.
- Bind fixed provider ceilings: 262,144 bytes for `utf8-footprint`, 65,536
  bytes for `python-tokenize`, and 32,768 bytes for every structured, template,
  shell, diagram, INI, and control provider.
- Require one resource contract for every complete provider signature; a
  provider cannot vary its mode or ceiling by path, carrier, role, profile, or
  metric.
- Resolve and validate the provider resource contract before opening carrier
  bytes. Reject a pre-open size above the ceiling before the first `os.read`,
  cap the read probe at `limit + 1`, and recheck post-read size/fingerprint.
- Recheck the same exact ceiling in the native API before startup conformance,
  UTF-8 decoding, AST construction, or provider parsing.
- Make any oversize carrier invalidate its carrier and complete snapshot; no
  partial vector or best-effort zero is admitted.
- Correct the canonical design and implementation plan so immutable Git replay
  consumes Task 3 measurement capability plus this resource boundary rather
  than assuming a successful worktree snapshot.

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

This Change updates only the v2 metric-contract wire owner, provider descriptor,
descriptor-bound reader, native admission boundary, generated schema, focused
tests, and canonical plans. It does not change carrier classification, v1
source-budget policy, debt, allowance, terminal targets, per-file ELOC, current
v1 authority, or the known YAML graph-safety gap.

## Out Of Scope

- Immutable Git blob replay, baseline shadow output, YAML-provider remediation,
  vector policy, Debt v2, changed-scope admission, dual control, calibration,
  cutover, or global v1 LOC retirement.
- Per-path overrides, automatically derived ceilings, threshold increases based
  on current repository maxima, exclusions, partial snapshots, or parser
  fallback.
- A subprocess timeout presented as isolation. If independent security review
  rejects bounded in-process execution, this Change stays open and must instead
  implement a versioned one-shot `isolated_worker_v1` with CPU, memory, wall,
  descriptor/process, protocol, and output limits and no in-process fallback.
- Remote publication, hosted CI claims, or mutation of foreign Work Lanes.
