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
The installed executable is Node 24.19.0. PyPI's current non-yanked stable
`nodejs-wheel-binaries` release is also 24.19.0, with macOS, Linux and Windows
architecture wheels. Upgrading that wrapper alone cannot deliver Node 26.
Replacing its underlying official Node supply requires the existing product
packaging owner and native qualification; host Node 26 does not update embedded
bytes.
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

The earlier candidate selected installed dependency bytes from uv's native PEP 751
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

The candidate constructor also installed the exact accepted predecessor wheel
into an isolated target in 8.10 seconds. Outside the checkout, its CLI version,
help and dependency compatibility checks passed; all 73 installed distributions
were compatible. This qualifies that constructor transition with a predecessor
wheel, not the delivery of the candidate wheel or an activated successor.

### Packaging Reassessment: Artifact Installation Is Not Environment Copying

September 30, 2026: candidate `15d2fbbcef97f5eef0f3b35956e4606291ba8c26`
retains a standard wheel, a platform runtime archive and a separate npm launcher.
These carriers have different acceptance obligations; none proves the others.

| Observation | Consequence |
| --- | --- |
| Exact npm launcher bytes, outside the checkout with Node but no Python or uv, exit 127 even for `--version`. The package contains no ETHOS implementation payload. | This is a development launcher, not source-independent product installation. Its source/PATH fallbacks and placeholder publication metadata must not be presented as delivered distribution. |
| Native uv installs the same 72 production dependencies into an empty venv offline in 2.72 seconds using available cache artifacts, without projecting installed files first. Dependency checking passes. An empty owned cache fails explicitly. | Native artifact installation is viable. A prepared artifact closure is a prerequisite for cold offline builds; ambient cache availability is not a release guarantee. This timing is not total build or installed-lifecycle latency. |
| An isolated dependency wheel is installed, its module bytes are changed without changing package identity, and the current projection copies those changed bytes. Subsequent uv `--require-hashes --strict` synchronization passes and retains the changes. | Hashing copied installed files preserves observed bytes, not their correspondence to locked artifacts. A no-op package synchronization does not revalidate every installed file. Neither the sample module nor an external effect is executed; this does not prove a full-proof or publication bypass. |
| The Cask uses `command_wrapper` to invoke ETHOS's existing console script. That script locates Python relative to `$0`, so directly linking it would select the link directory instead. | The wrapper currently has a relocation purpose, not a new semantic authority. Reconsider the launcher boundary before removing it; official `binary` linking alone is not a safe replacement. |
| The installation owner copies runtime and wheel from the package carrier into a shared generation. Package-manager removal and safe generation retirement are still separate open tasks. | Shared version pinning can be justified by live consumers, but another full copy and lifecycle require demonstrated necessity, bounded retention and native upgrade/uninstall acceptance. |

The raw experiments are retained under the existing
`build/evidence/quality/validation-results/` owner:

- `packaging-npm-source-independent-probe.json`
- `packaging-native-install-comparison.json`: failed isolation attempt; disabling
  native configuration also changed the effective prerelease policy.
- `packaging-native-install-comparison-explicit-policy.json`: replay with the
  accepted prerelease policy explicit, production inputs unchanged.
- `packaging-installed-byte-integrity-counterexample.json`

Every disposable target was removed. No accepted runtime, adopter, shared cache
entry or guest service was edited. These are local experiments, not a new release.

Prefer native locked-artifact installation into a fresh build target, followed
by platform relocation/signing, sealing and installed acceptance. Cache supplies
reusable computation, not authorization or independent artifact authenticity.
Keep the wheel as the Python/SDK carrier and assess a relocatable directory bundle
for ordinary CLI delivery; one-file extraction is not a product requirement.
Remove the npm product claim unless it gains a qualified installable payload.
Keep native Homebrew installation separate from the packager choice. A prior
formula changing dylib bytes invalidates a pre-relocation manifest; it does not
prove formula/bottle delivery inherently unsuitable. Do not claim a selected
optimal builder before the common lifecycle passes.

The candidate implementation now removes lock-based installed-file selection.
uv performs production artifact synchronization with hashes, strict dependency
checking, wheel-only installation and explicit reinstallation. Only this operation
uses the native reusable cache; ambient uv policy is excluded and the cache path
remains an explicit supply location. The interpreter copy excludes site-packages;
already sealed runtime migration retains its separately validated byte projection.
Fresh targets and same-version altered targets use artifacts, not installed names.

The local regression family passed 251 tests before the additional interpreter
copy correction; the final affected family passed 75 tests, with Ruff and Ty
clean. These overlapping results are not independent evidence totals.
The first complete image revealed a carried pip outside the production lock.
After excluding interpreter site-packages, construction took 6.24 seconds and
installed exactly 72 production dependencies plus ETHOS, with no unexpected
distribution. CLI version/help and dependency checking passed. This is a warm
single-host predecessor-wheel experiment, not a cold-host release or a full
installed-product journey. Retained receipts:

- `native-artifact-product-image.json`: initial image with the unexpected pip.
- `native-artifact-product-image-clean-interpreter.json`: exact clean closure.
- `native-artifact-public-boundary.json`: public product gate remains BLOCK on
  dynamic semantic observations and the unfinished native Nox evidence input.

This finding maps to existing installed-product tasks 3.2--3.5 and
proof-throughput task 5.11. Cold runner supply, exact-source proof, accepted
activation, complete native quality evidence and public installation remain open;
no packaged candidate is promoted by these experiments alone.

Official sources were read on September 30 through direct public HTTPS after
the configured Exa reader returned HTTP 429: [Homebrew formula guidance][brew-python],
[Cask command wrappers][brew-cask], [uv tool installation][uv-tools],
[uv cache safety][uv-cache] and [PyInstaller bundle modes][frozen-modes].
PyInstaller's documented one-file startup extraction and platform-specific output
are tradeoffs, not evidence that another packager has passed ETHOS acceptance.

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
[brew-cask]: https://docs.brew.sh/Cask-Cookbook#stanza-command_wrapper
[uv-cache]: https://docs.astral.sh/uv/concepts/cache/
[frozen-modes]: https://pyinstaller.org/en/stable/operating-mode.html
[fastmcp-tools]: https://gofastmcp.com/servers/tools
