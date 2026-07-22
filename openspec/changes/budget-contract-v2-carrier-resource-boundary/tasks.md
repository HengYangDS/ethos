## 0. Rejected Precursor And Governance Pivot

- [x] 0.1 Admit the C1 carrier, write MetricContract v3/resource RED, implement
  the bounded byte-reader experiment, and independently review it.
- [x] 0.2 Reject bounded-only execution after the INI multiplication evidence;
  preserve the uncommitted reader/native GREEN as external history, retain the
  committed v3 contract/tests as explicit migration input, and restore the Lane
  to `1aa6f28a` before authoring the pivot.
- [x] 0.3 Author OpenSpec, canonical plans, Claim, Chronicle, and Change scope
  for MetricContract v4 static hybrid execution dated 2026-07-21.
- [x] 0.4 Resolve independent-review findings, rerun the complete governance
  gate set, and commit the reviewed pivot before writing v4 RED.

## 1. MetricContract v4 RED And GREEN

- [x] 1.1 Add exactly eight diagnostic RED nodes without first replacing the
  shared valid fixture: bounded-v4 positive, isolated-v4 positive, complete-v3
  fail-closed, helper four-tuple, parser-global mode/id/digest drift,
  execution-identity propagation with unchanged measurement vector, generated
  schema requirements, and repository static-policy mapping.
- [x] 1.2 Implement v4 models and make
  `metric_provider_resource_contract(...)` return exactly
  `(execution_mode, max_carrier_bytes, execution_contract_id,
  execution_contract_digest)`, preserving the old first-two-field order. Keep
  carrier-manifest v2, 16 profile ids, and 28 `*-v2:*` contract ids unchanged.
- [x] 1.3 Add the pure-kernel execution descriptor owner at
  `measurement/execution.py` plus descriptor-only worker protocol/resource
  owners, then provider descriptor v2. Atomically update 28 policy atoms and
  every grammar/digest golden from owner-computed real digests. The four current
  parameterized execution digests are bounded-32KiB, bounded-256KiB,
  isolated-32KiB, and isolated-64KiB.

## 2. Worker Protocol Contract RED And GREEN

- [x] 2.1 Add pure kernel RED for typed request/result models, success-gap XOR,
  the exact finite child-gap allowlist and seven parent-only worker gaps, five
  bound digests, parent replay, generated schema, and no path/environment fields.
- [x] 2.2 Add binary-frame RED for magic/version, big-endian lengths, canonical
  JSON, duplicate keys, all truncation boundaries, overlimits, wrong-direction
  frames, extra responses, and trailing bytes.
- [x] 2.3 Implement protocol models, canonical digest constructors,
  revalidation, strict frame codecs, and generated worker schema without adding
  subprocess behavior to the kernel package.

## 3. Static Router And Import Boundary RED And GREEN

- [ ] 3.1 Add RED proving UTF-8/control/C4 use only the bounded engine and every
  complex provider uses only the worker supervisor.
- [ ] 3.2 Add import-graph and forged-signature RED proving the parent cannot
  import or call an isolated engine and no worker failure falls back in process.
- [ ] 3.3 Split provider identity, bounded engine, isolated engine, and router
  modules within module-layout/code-size limits; preserve exact metric values.

## 4. Worker Bootstrap And Supervisor RED And GREEN

- [ ] 4.1 Add RED for private environment/cwd, `-I -B -X utf8`, resource setup
  before engine import, no source path/FD transfer, and child-side signature and
  ceiling revalidation.
- [ ] 4.2 Add RED for bounded nonblocking stdin/stdout, stderr suppression,
  timeout, output flood, malformed response, crash/signal, ignored TERM, KILL
  escalation, descendant-held pipes, FD closure, and zombie-free reap.
- [ ] 4.3 Add Linux and Darwin capability/backend RED for CPU, RSS/address-space
  intent, NOFILE, NPROC, CORE, FSIZE, wall, telemetry, and unsupported mode.
  Darwin RED SHALL acquire the first successful pre-request `pti_virtual_size`
  sample as baseline and trip above baseline plus 512 MiB; no request bytes may
  be written before the baseline exists.
- [ ] 4.4 Implement one-shot bootstrap, POSIX supervisor, platform telemetry,
  group termination, stable redacted parent gaps, and strict parent result
  replay. Do not use `communicate()` or an in-process fallback.

## 5. Reader, Native, And Snapshot GREEN

- [ ] 5.1 For both execution modes, resolve exact provider/execution identity
  before content open, reject initial oversize before `os.read`, use one
  `limit + 1` bounded parent read, and keep existing
  no-follow/fingerprint/cleanup semantics. Mode selects only parse location.
- [ ] 5.2 Recheck direct bytes before bounded execution or worker spawn; ensure
  limit-minus-one/exact-limit success and limit-plus-one rejection.
- [ ] 5.3 Preserve within-limit object drift, stable path-bound gaps, and complete
  snapshot absence after any carrier/worker failure.

## 6. Adversarial, Performance, And Inventory Evidence

- [ ] 6.1 Prove exact-ceiling INI defaults-by-sections amplification is contained;
  add deep/wide Python, JSON, TOML, YAML, Jinja, shell, C4, and UTF-8 cases.
- [ ] 6.2 Prove timeout, CPU/RSS/FD/process exhaustion, output flood, protocol
  corruption, crash, process-tree cleanup, and Darwin/Linux capability paths.
- [ ] 6.3 Measure hybrid cold-start/runtime without changing limits or adding a
  persistent worker; record any unacceptable cost as an explicit blocker.
- [ ] 6.4 Verify complete current and immutable-baseline inventories, no new
  oversize gap, three reviewed exclusions, and the unchanged YAML graph gap.

## 7. Quality And Governance Closeout

- [ ] 7.1 Reach focused 100 percent statement/branch coverage and run native/v1
  regressions, Ruff, types, config/schema/shell, dependency/import,
  module-layout, code-size, no-compat, and source-budget gates.
- [ ] 7.2 Complete independent security, contract, simplicity, and platform
  review. If hybrid isolation is rejected, keep C1 open; do not raise a ceiling.
- [ ] 7.3 Bind final evidence/promotion targets, refresh parity, run exact-HEAD
  default/full proof, archive, archive-HEAD proof, candidate land, accepted-root
  closeout, local publish readiness, and owned-Lane retirement as separate
  transitions. Before an implementation/proof claim, promotion targets SHALL add
  `measurement/execution.py`, the kernel `measurement/worker` package, the
  worker-protocol schema, protocol/frame tests, supervisor test, and architecture
  boundary test. Do not push remotely.
