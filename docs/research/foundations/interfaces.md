---
subject: ethos:foundations-interfaces
role: research
state: active
relations:
  part_of: ../modern-engineering-foundations.md
  informs: ../../plans/terminal-governance-product-design.md
  constrained_by: ../../governance/product-design-contract.md
---

# Interfaces, Extensions And Product Languages

Status: active research; dated observations retain their original evidence limits.

Purpose: Evaluate replaceable capability boundaries and implementation-language choices.

See also: [Research Overview](../modern-engineering-foundations.md),
[Product Design Contract](../../governance/product-design-contract.md), and
[Terminal Plan](../../plans/terminal-governance-product-design.md).

## Extension Contracts, Isolation And Interoperability

Use standard Python entry points for installed capability discovery; use
[pluggy's registration and hook validation][pluggy-mechanism] only where genuine
multi-provider hook composition would otherwise be reimplemented. Discovery,
selection, trust and arming are separate observations. In-process plugins share
the process's privileges; a plugin API is not a sandbox.

[MCP][mcp] and [A2A][a2a] are protocol candidates for tools/resources and agent
collaboration. Expose existing typed capabilities through thin adapters; remote
task identifiers and protocol state cannot replace official Change or Lease
state. An adapter must declare identity/version, permission scope, cancellation,
timeouts, retry behavior, result provenance and unsupported semantics. All agents
and models consume the same authority; none is hard-coded as the product owner.

[Wasmtime/WASI][wasmtime] is worth a bounded trial for genuinely untrusted,
portable capability code with restricted imports, filesystem and resource use.
Admission requires actual sandbox escape/resource tests and usable bindings, not
an assumption that WebAssembly alone provides the needed isolation. Native
capabilities and separate processes remain possible alternatives. No marketplace
or universal plugin runtime is needed before independent implementations pass
one shared conformance workload.

## Language And Product Shape

Python-only is not a product invariant. [Modern Python][python312] offers type
parameters, clearer type aliases and override checking; existing structured
concurrency and pattern matching can simplify implementations within the declared
support floor. New syntax must preserve generated schema and public behavior,
not merely reduce lines. Do not treat post-3.12 features as available on the
minimum supported interpreter.

[Rust][rust] is a candidate for a bounded packaging/process/filesystem or semantic
analysis component when its safety and deployment benefits beat boundary/build
costs. [Go][go] is a candidate for a standalone service/tool or direct CUE/CEL
integration when that removes more foreign-runtime machinery than it adds.
TypeScript may fit interactive interfaces and the tooling ecosystem without
moving authoritative meaning into a browser. [Rich][rich] and the existing CLI
framework can improve readable progress and diagnostics without creating another
command plane. No language migration is justified by shifting handwritten code
outside the Python budget; total maintenance surface remains visible.

## Installed Product Comparison

September 21, 2026, Asia/Shanghai: the existing accepted package at source
abc5ab1541834032cd27a79b18d89f9a49f49266 executes outside the checkout.
The installed-package probe resolved ETHOS and bundled OpenSpec from immutable
production supply, not the source tree. This establishes source-independent
execution, not host distribution or a complete Agent journey.

An actual PyInstaller onedir build from that package took 18.901 seconds.
Frozen and ordinary installed entries both adopted an isolated repository with
Python, uv and npm absent from PATH. Frozen hook installation blocked with
hook_runtime_python_abi_invalid; ordinary installed hook installation passed.
The hook boundary treats sys.executable as Python, while a frozen executable is
the application. This identifies a replaceable execution-boundary assumption,
not evidence that freezing cannot work.

The experiment used foreign site-packages with the Homebrew builder and emitted
a deprecation warning. Its dependency collection was deliberately broad; optional
module warnings, native platforms, signing, relocation and full client lifecycle
remain unqualified. Evidence: product-packaging-lifecycle-probe.json,
product-source-independence-observation.json and pyinstaller-product-build-bound.json
under the existing build/evidence/quality/commit-integrity execution output.

Homebrew installation is a user-required delivery channel. Native Python formula
support is an alternative to freezing, while uv tool environments separate a
Python tool from the project environment. Compare both with a portable
interpreter/wheel image on the same full lifecycle; none wins by naming alone.
The existing installed-product Change owns the selection and implementation,
not this research note. Do not confuse internal npm supply for OpenSpec with
user-facing ETHOS distribution.

Official references: [Homebrew Python formula support][brew-python],
[uv tool environments][uv-tools], and [PyInstaller runtime identity][frozen-runtime].
The current AIGW source and installed OpenSpec package illustrate different
delivery mechanics; neither is authority for ETHOS design or proof of a current
hosted release.

### Measured Runtime Cost And Retirement Boundary

September 30 inspection of accepted source `ebe828d31aacca56f82b9a1dabc77e829989c328`
found two repository-local generations totaling approximately 863 MiB. The current
generation is approximately 432 MiB: Node supply is 199 MiB, the CEL native extension
39 MiB and the ETHOS package 23 MiB; Python and remaining tools/dependencies account
for the rest. These are allocated-size observations, not download sizes or proof
that every byte is independently reclaimable.

The Node package includes 62 MiB of development headers and 17 MiB of npm/Corepack.
Their necessity for the shipped product workload is unproven. Bundling an
interpreter can provide useful environment independence; copying a complete SDK
and retaining every historical package does not follow from that requirement.
Do not trim an active immutable generation in place or select a new packager
solely because its executable looks smaller.

The existing [installed-product decision](../../../openspec/changes/installed-product/design.md)
owns a minimal qualified dependency closure, native Homebrew delivery, host-shared
immutable versions and repository-local selection. Its common workload must verify
CLI/MCP/SDK, hooks, official OpenSpec, offline behavior, upgrade, rollback and
retirement before replacing the current bundle. Keep package caches, recovery
inputs, generated reports and live runtimes distinct; their owners and retention
conditions differ. Current repository-private installation is not the terminal
product form.

The candidate now selects installed dependency bytes from uv's native PEP 751
`pylock.toml` export before hashing or copying. The export remains a transient
projection of `uv.lock`; packaging supplies marker evaluation, normalized names
and version comparison. Missing, mismatched and duplicate packages or invalid
markers refuse construction. The locked uv explicitly opts into its pylock
consumer, whose current implementation still marks this format experimental.
This does not change the stable-release policy or qualify other uv versions.

One native measurement reduced the observed dependency files from 10,620 to
8,401 and their logical bytes from 519,195,951 to 349,985,840. Observation took
1.88 seconds before selection and 0.67 seconds after; this single macOS sample
does not establish full-proof latency. A real target environment contained the
72 applicable production distributions, passed uv's exact locked check and
dependency compatibility check, and imported FastMCP and Node supply. Its owned
temporary root was removed. The 206 adjacent runtime/installation regressions
passed; additional native lock fault cases also pass. Complete wheel delivery,
native platforms and runtime activation remain open under the existing tasks.

## MCP Framework Selection Evidence

September 21, 2026, Asia/Shanghai: the standalone FastMCP 4.0.5 comparison used
its real in-process client with one typed probe tool, not an ETHOS mutation.
Eight cases compared flexible and strict modes. Undeclared root and actor
arguments were rejected without executing the body in both modes. A string
Boolean was coerced in flexible mode and rejected before execution in strict
mode. Valid calls retained structured output in both modes.

This refutes the inference that the official SDK MCPServer's extra-argument
behavior also describes standalone FastMCP. The installed-product Change selects
FastMCP strict mode instead of manual low-level callback assembly. The comparison
does not qualify subprocess transport, cancellation, effect recovery, package
delivery or platforms. Its 66-package isolated environment is an observed supply
closure, not proof that every package is necessary for ETHOS deployment.

Evidence remains in the existing build/evidence/quality/commit-integrity output:
fastmcp-contract-probe.log and the owned script under the recorded mcp-sdk-scratch
root. Official [FastMCP tool validation][fastmcp-tools] documents strict mode;
the measured behavior, not the documentation alone, supports this choice.

## MCP Adapter Implementation Observations

The owned Work Lane committed FastMCP supply as e9bf7d27d and the command
declaration/consumer correction as 2bfca40b8. The accepted checkout and installed
runtime remain unchanged. Candidate implementation is not installed acceptance.

The declaration defect was reproduced through exact prewrite and then covered
by eight positive/negative cases. Declaration alone no longer counts as a
consumer; a candidate declaration still cannot authorize its new consumer.
The related admission/projection suite passed 63 tests before commit.

A real stdio client now exercises discovery, strict unknown-field and Boolean
rejection, explicit-root isolation, authorized adoption, stale request rejection
and fresh-process reconnect. MCP plus CLI regressions passed 42 tests. Later
focused runs cover fixture consolidation and native cancellation; their counts
overlap and are not independent evidence totals.

FastMCP's native synchronous tool timeout was measured with a 20 ms deadline
and 100 ms body: it returned success after about 144 ms. The adapter therefore
adds a post-drain cancellation checkpoint under the same AnyIO deadline.
Queued requests expire without entering their bodies, active native work drains,
and a new observation remains usable. Four MCP cases passed after this repair.
This does not prove hard interruption of blocked filesystem calls or recovery
from every process-kill window.

Existing test fixtures were consolidated by semantic responsibility, preserving
distinct cases and assertions rather than excluding obligations. The latest
measurement is 46,661 product and 49,972 test ELOC; both limits are 50,000.
Native Ruff, dependencies, import boundaries, schemas and focused typing passed.
The direct module-layout provider passed; its host-proof wrapper rejected an
unfrozen source/index pair, so it was not reported as executed proof.

Raw outputs remain under the existing commit-integrity evidence root:
mcp-command-owner-tests.log, mcp-command-relation-red.log,
mcp-command-relation-green.log, mcp-stdio-integration.log,
mcp-deadline-red.log, mcp-deadline-green.log, mcp-final-focused.log and
mcp-native-static-gates.log. The existing installed-product tasks own remaining
work. Full proof, accepted integration, Homebrew and platform qualification
remain separate and unproved.

## Sources

Links identify inspected documents, not blanket endorsements. Source-level and
README observations above have different strength; repository popularity and
marketing claims were not used as evidence of comparative performance.

[pluggy-mechanism]: https://github.com/pytest-dev/pluggy/blob/6a7f8960eb4009b551f14030233cea7a64ccaf5d/src/pluggy/_manager.py
[mcp]: https://github.com/modelcontextprotocol/modelcontextprotocol/blob/aa8ce049f089f92618340190d4ece141f663310d/README.md
[a2a]: https://github.com/a2aproject/A2A/blob/6d6640c29b102f7a8d23784901351b5d2454fe71/README.md
[wasmtime]: https://github.com/bytecodealliance/wasmtime/blob/2be5e3a62b9569bf3f46db996297a306442885ea/README.md
[python312]: https://github.com/python/cpython/blob/7bfa97f4dca58ab45def2ca0a1e8088997a4fa0b/Doc/whatsnew/3.12.rst
[rust]: https://github.com/rust-lang/rust/blob/9c99d05505bccb67912d68e05fe7fc7c58afcb41/README.md
[go]: https://github.com/golang/go/blob/fdcd66bb544d230a7eb0c2512e9e7a6ab191388b/README.md
[rich]: https://github.com/Textualize/rich/blob/9d8f9a372cc5916fd4781fec207ced7ddac2f08f/README.md
[brew-python]: https://docs.brew.sh/Language-Specific-Formulae
[uv-tools]: https://docs.astral.sh/uv/concepts/tools/
[frozen-runtime]: https://pyinstaller.org/en/stable/runtime-information.html
[fastmcp-tools]: https://gofastmcp.com/servers/tools
