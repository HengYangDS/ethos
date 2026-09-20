---
subject: ethos:foundations-execution
role: research
state: active
relations:
  part_of: ../modern-engineering-foundations.md
  informs: ../../plans/terminal-governance-product-design.md
  constrained_by: ../../governance/product-design-contract.md
---

# Execution And Evidence Reuse

Status: active research; observations are qualified only for their named scope.

Purpose: compare native and container execution foundations on actual ETHOS inputs.

See also: [Research Overview](../modern-engineering-foundations.md),
[Product Design Contract](../../governance/product-design-contract.md), and
[Terminal Plan](../../plans/terminal-governance-product-design.md).

## Execution, Reuse And Failure Latency

Optimize the complete feedback interval: expose cheap failures first, avoid
recomputing still-applicable results, reuse raw evidence for new presentation,
freeze before full proof and observe effects before retry. ETHOS already has a
dependency-ready gate queue; a superficial scheduling wrapper is not the missing
capability. The opportunity is finer input closure, less preparation, isolated
resources and native result reuse.

[Pants][pants] is the leading dependency-aware test candidate for this measured
cut. Its [process owner][pants-process] distinguishes persistent reuse from
per-session deduplication. [Dagger][dagger] is a candidate for container/package
execution. [Bazel][bazel] and Nix remain alternatives where their execution or
supply model fits better, not rejected because ETHOS has one Python package.

Current removal targets are the corresponding scheduling/process code in
`src/ethos/adapters/gates/runner.py`, repeated preparation in
`tools/ci/python_test_gate.py` and environment assembly under
`src/ethos/adapters/repo/runtime/materialization/`. Preserve acceptance
obligations, exact proof binding, native effect tests and runtime activation.
A selected engine supplies execution evidence, never repository authorization.

## September 20 Replacement Analysis

At source `81848f2fe50ef5ebea8f8e1dee75854a7be45c45`, exact full proof took
804.632 seconds. Tests took 597.887 seconds from offset 22.696; installed
acceptance took 170.509 seconds from offset 622.743. Their durations total about
95.5 percent of elapsed proof time. Eight pytest workers do not provide
dependency-aware reuse across candidates, and wrapping these same coarse commands
does not establish a better critical path.

### Distinct Replacement Responsibilities

| Foundation | Replacement scope | Incumbent to retire | ETHOS retains |
| --- | --- | --- | --- |
| Pants | Input inference, per-target/compatible-batch tests, sandboxing, caching, result capture | Equivalent custom selection, scheduling, materialization and cache logic | Accepted obligations, candidate binding, fresh effect admission and evidence interpretation |
| Dagger | Container builds/tests, immutable inputs, services, reusable operations and traces | Repeated container assembly and local/provider recipes | Native macOS/Windows qualification, coordination, publication authorization and current observations |
| Nix/uv2nix | Interpreter, native libraries, build inputs, derivations and store reuse | Equivalent Unix environment/package construction | Portable delivery, host selection, live users, activation/rollback and repository authority |

Use one scheduler and one environment-assembly owner for each adopted scope.
A Nix-built OCI image consumed by Dagger is a producer/consumer relation, not
two editable selections. Stacking Pants inside Dagger is unjustified if both
own the same scheduling and supply. Nox may project an entry, never a second plan.

### Pants: Executed Comparison

The official Homebrew launcher 0.13.2 ran engine 2.33.1 in one owned disposable
root. Python 3.14.7, the original source/test bytes and native pytest TOML were
held fixed. Comparison used two pytest workers or two Pants process slots;
the public-proof target also used native Pants xdist concurrency two. Pantsd
was disabled. These are development-host comparisons, not Python 3.12 or
native Windows qualification.

Supply preparation was separate from execution: native
`uv export --locked --offline --all-groups --no-emit-project --no-header --format requirements-txt`
derived a hashed requirements projection without editing uv.lock. Seventy-one
hash-checked wheels were prepared; Pants then used an offline wheelhouse with
indexes disabled. Result-store clearing retained this supply.

| Workload | Baseline runs | Pants first | Pants unchanged runs | Cleared result store |
| --- | --- | ---: | --- | ---: |
| 48 original decision tests | 1.096 / 1.098 / 1.050 s | 5.586 s | 2.093 / 2.080 / 1.987 s | 19.559 s |
| Those tests plus five original Git-worktree cases | 1.804 / 1.780 / 1.744 s | 12.878 s | 1.960 / 1.951 / 2.000 s | Not separately measured |
| 23 original public proof/source-boundary tests | 8.540 / 8.462 / 8.786 s | 14.417 s | 2.015 / 2.143 / 2.039 s | 27.562 s |

The first two partitions show no wall-time advantage over direct pytest.
The public-proof partition shows useful unchanged-result reuse: median 8.540
versus 2.039 seconds. Cold preparation and execution remain slower. None of
these observations predicts the full 598-second test gate or 805-second proof.
Warm runs still execute three preparation processes; cache hits are not fresh
test execution.

#### Real Input And Platform Findings

- The initial launcher download failed DNS. Its documented bootstrap URL mapping
  consumed locally fetched, hash-identical official Python/PEX artifacts; checks
  were not disabled. Homebrew cask deprecation warnings were retained.
- The 2.33.1 uv resolver is experimental and reconstructs a project plus Pants
  metadata; it is not transparent consumption of an arbitrary existing uv.lock.
  Its `uv_requirements` parser did not consume modern dependency groups in this
  experiment. The native hashed export avoids a second editable resolution.
- With the exported requirements format, `resolves_generate_lockfiles=false`,
  `pytest.install_from_resolve="ethos"` and `requirements=[]` consume the
  declared tool closure. The attempted pytest subset instead selected a PEX
  JSON-lock path and failed; that failed setup is not a framework benchmark.
- Import inference omitted checkout/package data. Explicit JSON/TOML, templates
  and package resources were required. Resources are conservatively grouped;
  this is not a minimal per-target closure. The public target's native dependency
  query reported 249 addresses.
- Hidden-directory defaults omitted `.config` and `.ethos`; explicit native
  inclusion restored the unchanged pytest/configuration inputs.
- Default `BUILD` conflicts with ETHOS's `build/` on case-insensitive macOS.
  Native `build_patterns=["BUILD.pants"]` resolved the conflict in the
  experiment. No production tree or Python source needed a naming workaround.
- The public-proof baseline initially failed because the isolated checkout had
  no official OpenSpec supply. Both candidates then used the same declared,
  lock-validated Node supply. Its 5,007 file/link entries were fingerprinted,
  passed as an input identity and verified unchanged afterwards; the post-run
  inventory cost 0.199 seconds. This supply remained outside the Pants sandbox,
  so neither hermeticity nor a production-safe fingerprint protocol is proved.
- Diagnostic output from Pants includes pytest failures on stderr. Consumers
  must preserve both channels and native exit; stdout absence is not success.

These findings change the integration cut. A native engine cannot infer mutable
Git state, native executable bytes, external facts or undeclared runtime resources
from Python imports. Do not copy the entire repository into every target and
claim minimal invalidation. Do not add a parallel resolver or a growing set of
name exceptions. The selected production boundary must declare or materialize
actual inputs and keep live effects outside reusable execution.

#### Falsifying Cases And Native Capability Use

| Counterexample or capability | Executed result |
| --- | --- |
| Unrelated document added to the 48-test partition | Tests remain cached; PASS in 1.982 s. |
| Release observation changed to return the wrong result | Invalidation and failure in 2.561 s; restored source passes. |
| Proof-source observer falsely reports clean source/index | Invalidation and failure in 12.469 s; restored source passes in 1.980 s. |
| Invalid native pytest argument | Public partition fails with exit 4 in 2.866 s; restored policy passes. |
| Declared Node supply changed to an absent path | Invalidation and nonzero failure in 7.637 s; restored supply passes. |
| Owned result/blob store deleted while supply remains | Public partition reexecutes, PASS in 27.562 s, zero cache hits. |
| Native `--test-report` after successful execution | 23 JUnit cases materialized in 2.319 s using cached test output, not another test run. |

All source, test and policy perturbations were restored. The failure-channel
assertion in the probe initially inspected stdout only; correcting that observer
used retained stderr rather than rerunning the already-proved failure.

Native batching can reuse expensive fixtures, but any changed member invalidates
the entire compatible batch. One process per file and one whole-repository batch
are both unmeasured defaults, not final designs. Batch by actual compatible
resources; let a selected engine own concurrency rather than nest schedulers.
Native timeouts, interruption, descendant cleanup, raw coverage reuse, remote
execution and the production package-supply closure still require qualification.
Upstream issue 23657 reports a uv concurrency failure on 2.33.0, with a partly
unverified explanation; it is a counterexample to examine, not proof that
2.33.1 fails or a reason to reject Pants wholesale.

### Dagger: Executed Evidence, Not An End-to-End Speed Claim

The installed 0.21.9 CLI used Docker to prepare a privileged engine container and
anonymous volume. A 20-second initial deadline was insufficient; bounded startup
completed. A rejected command flag was replaced with the query interface selected
from native help, not guessed retry syntax.

A digest-pinned Python Linux container executed ETHOS's actual verdict module
with three assertions. First execution including image preparation took
50.559 seconds; repeat took 1.199 seconds with the same random marker and an
explicit cache hit. An injected failed assertion returned nonzero in 1.560
seconds. This proves bounded execution/reuse/failure, not source invalidation,
cleared-cache parity, full pytest compatibility, reproducible wheels, native
Windows behavior or a 40-times proof speedup.

The useful cut is an immutable source-to-package or Linux test subgraph,
excluding current Git admission and remote publication. Mutable cache volumes
are download accelerators, not authoritative environments; secret/external-state
changes must not be assumed to invalidate a result. After zero active sessions
were observed, the exact engine and volume were removed and other containers
preserved. The immutable engine image remains supply, not an active probe service.

### Nix: Build Closure, Not Merely Another Tool Installer

Nix addresses interpreter, native libraries, compilers, build tools and builder
environment beyond language lockfiles. uv2nix derives Python packages from uv.lock;
a flake lock can pin Nixpkgs/build infrastructure without becoming a second Python
resolver. Its documentation warns against reprovisioning that same environment
with uv and identifies build-system dependencies as additional inputs.

A derivation path or successful substitution does not prove bit-identical
rebuilds or correctness. Fixed-output fetching, sandbox/fallback, overlays and
binary-cache trust remain reviewable. Portable wheel/npm delivery must work
without a Nix installation; store references do not prove relocation or native
Windows support. The inspected manual lists Linux and macOS support.

No Nix installation or ETHOS build was executed. The qualification target is one
actual package closure derived from the existing lock, followed by an independent
rebuild and a no-Nix installed consumer. A dev shell that leaves equivalent
runtime assembly intact would not achieve this replacement.

## Common Acceptance Workload And Quality Coverage

The [overview workload](../modern-engineering-foundations.md#comparative-acceptance-workload)
owns the shared experiment contract. Additional execution-specific obligations:

| Dimension | Required distinguishing evidence |
| --- | --- |
| Coverage | Reused raw coverage belongs to the relevant exact inputs and preserves combined line/branch coverage; no stitching focused runs into a fictitious full run. |
| Isolation | Concurrent/interrupted tests cannot consume partial supply or share mutable Git state; qualify actual process descendants and cache corruption. |
| Input completeness | Native tools, non-Python data, rules, environment and relevant Git facts invalidate reuse; unrelated changes avoid unnecessary execution. |
| Scope | Every tracked carrier has applicable checks; generated outputs require source/digest/reconstruction rather than silent exemption. |
| Portability | Linux containers, native macOS and native Windows are separately qualified. |
| Maintainability | Count retired duplicate owners and actual adapter/operational cost, not only configuration or code-line totals. |

The read-only quality inventory found 2,930 tracked files and 548 Python files.
Ruff selected all 548 and carrier assignment had no unowned file; this proves
selection, not effective assurance. Ty still translates package "." to "src".
The current Prettier-only JavaScript path accepts a formatted undefined binding.
An execution-engine change does not fix these quality obligations.

## Disposition And Evidence Limits

Proceed with a dependency-complete Pants test-partition replacement under the
existing Change; do not activate it for all workloads merely because one warm
partition wins. Qualify selected batching, input materialization, coverage and
failure behavior, then remove corresponding custom execution code. Preserve
direct execution where no replacement benefit is established, under the existing
quality owner rather than a second acceptance mechanism.

Dagger remains the source-to-package/container replacement candidate; Nix/uv2nix
remains the native build-closure candidate. They are different responsibilities,
not a mandatory three-engine product stack. Their missing delivery observations
remain explicit and must not become indefinite excuses to retain custom assembly.

Evidence resides in the existing quality evidence home:
`tracked-quality-scope.json`, `foundation-source-review.json`,
`foundation-resolver-review.json`, `dagger-engine-preflight.json`,
`dagger-verdict-workload.json`, `dagger-workload-cleanup.json`,
`pants-comparison-casefold-safe.json`, `pants-native-resource-comparison.json`,
`pants-public-proof-supply-comparison.json`, `pants-public-proof-supply-input.json`,
`pants-native-report-reuse.json` and `pants-native-target-dependencies.json`.
Failed preparation records remain failures; none is exact repository proof.
The completed environment and three owned baseline pytest roots were removed
after process quiescence and exact ownership checks. Reproduction inputs and
native JUnit bytes remain in `pants-reproduction-inputs.tar.gz`; cleanup preview
and absence readback remain in `pants-workload-cleanup*.json`. Homebrew supply,
the project's Node environment and unrelated resources were preserved.

## Sources

Source inspection, local execution and delivery qualification have different
strength. Links identify inspected materials, not blanket endorsements.

- [Pants resolver source](https://github.com/pantsbuild/pants/blob/release_2.33.1/src/python/pants/backend/python/subsystems/setup.py)
- [Pants uv lock generation](https://github.com/pantsbuild/pants/blob/release_2.33.1/src/python/pants/backend/python/goals/lockfile.py)
- [Pants test batching, isolation and reports](https://www.pantsbuild.org/2.33/docs/python/goals/test)
- [Reported uv concurrency issue](https://github.com/pantsbuild/pants/issues/23657)
- [uv2nix build/environment boundaries](https://pyproject-nix.github.io/uv2nix/usage/getting-started.html)
- [Nix supported platforms](https://nix.dev/manual/nix/2.35/installation/supported-platforms.html)
- [Nix sandbox settings](https://nix.dev/manual/nix/2.35/command-ref/conf-file#conf-sandbox)

[pants]: https://github.com/pantsbuild/pants/blob/c94f9f4ccfd43342b8f9379a139a328555bc5a5b/src/python/pants/engine/process.py
[dagger]: https://github.com/dagger/dagger/blob/f2aefc20cf41b5ed7922df7244e0f10ddc6031f7/README.md
[bazel]: https://github.com/bazelbuild/bazel/blob/aac8677f8e69e30fb105026ff524e04965640499/README.md
[pants-process]: https://github.com/pantsbuild/pants/blob/c94f9f4ccfd43342b8f9379a139a328555bc5a5b/src/python/pants/engine/process.py
