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
88186616714567768561e5447993e4ab5c999c04 executes outside the checkout.
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
remain unqualified. Evidence was recorded on 2026-09-21 as
product-packaging-lifecycle-probe.json, product-source-independence-observation.json
and pyinstaller-product-build-bound.json under build/evidence/quality/commit-integrity;
it is no longer retained.

Homebrew installation is a user-required delivery channel. Native Python formula
support is an alternative to freezing, while uv tool environments separate a
Python tool from the project environment. Compare both with a portable
interpreter/wheel image on the same full lifecycle; none wins by naming alone.
The selection and implementation belonged to task 3.4 of the installed-product
Change, not this research note; DR-0016 withdrew that task, and the Change was
archived on 2026-10-24. Do not confuse internal npm supply for OpenSpec with
user-facing ETHOS distribution.

Official references: [Homebrew Python formula support][brew-python],
[uv tool environments][uv-tools], and [PyInstaller runtime identity][frozen-runtime].
The current AIGW source and installed OpenSpec package illustrate different
delivery mechanics; neither is authority for ETHOS design or proof of a current
hosted release.

## MCP Framework Selection Evidence

September 21, 2026, Asia/Shanghai: the standalone FastMCP 4.0.5 comparison used
its real in-process client with one typed probe tool, not an ETHOS mutation.
Eight cases compared flexible and strict modes. Undeclared root and actor
arguments were rejected without executing the body in both modes. A string
Boolean was coerced in flexible mode and rejected before execution in strict
mode. Valid calls retained structured output in both modes.

This refutes the inference that the official SDK MCPServer's extra-argument
behavior also describes standalone FastMCP. The installed-product Change, archived
on 2026-10-24, selected FastMCP strict mode instead of manual low-level callback
assembly. The comparison does not qualify subprocess transport, cancellation,
effect recovery, package delivery or platforms. Its 66-package isolated environment
is an observed supply closure, not proof that every package is necessary for ETHOS
deployment.

Evidence was recorded on 2026-09-21 in build/evidence/quality/commit-integrity:
fastmcp-contract-probe.log and the owned script under the recorded `mcp-sdk-scratch`
root. Neither is retained now. Official [FastMCP tool validation][fastmcp-tools]
documents strict mode; the measured behavior, not the documentation alone, supports
this choice.

## MCP Adapter Implementation Observations

The owned Work Lane committed FastMCP supply as d5e4f247e and the command
declaration/consumer correction as 7de9b980f. Both are now on `dev`; the accepted
checkout and installed runtime were unchanged on 2026-09-21. Candidate
implementation is not installed acceptance.

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
distinct cases and assertions rather than excluding obligations. On 2026-09-21
the measurement was 46,661 product and 49,972 test ELOC against 50,000 limits;
the ceilings are now 70,000 and 90,000.
Native Ruff, dependencies, import boundaries, schemas and focused typing passed.
The direct module-layout provider passed; its host-proof wrapper rejected an
unfrozen source/index pair, so it was not reported as executed proof.

Raw outputs were recorded on 2026-09-21 under the commit-integrity evidence root
and are no longer retained: mcp-command-owner-tests.log, mcp-command-relation-red.log,
mcp-command-relation-green.log, mcp-stdio-integration.log,
mcp-deadline-red.log, mcp-deadline-green.log, mcp-final-focused.log and
mcp-native-static-gates.log. Tasks 2.3, 2.4, 3.5 and 3.6 of the archived
installed-product Change, withdrawn by DR-0016, name the remaining MCP, Homebrew
and platform work. On 2026-09-21, full proof, accepted integration, Homebrew and
platform qualification remained separate and unproved.

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
