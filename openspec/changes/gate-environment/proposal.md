# Proposal

## Why

The archived `rc-plan` design orders this row in its Family 4 (lines 101 to 104):
"`gate-environment` (working name; R8(c); unsized) follows A7 and precedes A10 and MCP `prove`:
proof gates run in an allow-listed environment without SSH agent or forge tokens, or the PDC
states the non-sandbox boundary, and one owner redacts persisted failure output." A7 is
`environment-entry`, which the base of this Change holds. The committee's resolution of
2026-11-14 places the row in 0.2.0-beta.13.

A verdict must depend on its subject alone. Seven times a proof's verdict, or what it examined,
moved with something outside the subject. Each case was measured on the releasing host or relayed
by the session that met it:

- **The shell that launched it.** The children of the providers dropped `MISE_` variables and
  kept Mise's activation state, so a result depended on the launching shell.
  `mise-activation-isolation` fixed it for those children in 0.2.0-beta.11. A gate that a
  repository declares as a command still receives the launching environment unchanged; the
  third case measures it.
- **The host's package cache.** A full proof of 2026-11-15 failed two gates on one cause: the
  behavior gate's offline locked sync found no wheel for one interpreter in the host's uv cache,
  which a cleaner had emptied the day before. It held a wheel for 103 of 121 locked packages. A
  governed repository's proof lost 17 admitted minutes after a wait of 60 to the same cause.
- **The launcher's path.** Two controlled runs of one command gate on one commit of a governed
  repository both passed. Launched from a shell with another package manager first on the path,
  the gate's environments bound that manager's interpreters; launched through the locked
  toolchain, they bound the locked ones. The verdict was the same and the subject was not.
  On 2026-11-16 one full proof of a disposable copy of a governed repository, under the
  packaged candidate of 0.2.0-beta.11, failed one test of a declared command gate: the test
  found the package manager that the interpreter bundles, where the repository declares
  another. The harness had removed Mise's activation variables from its shell while the
  shell's path stayed activated, and Mise then runs the bundled copy (jdx/mise#15771). A
  declared command gate receives the launching environment unchanged, by the same code in
  0.2.0-beta.10 and 0.2.0-beta.11; the Mise adapter builds the children of the providers
  alone. A second pair of full proofs from the same launch failed the same test under both
  releases with the same six gaps. The proof passed from an empty environment, and the gate's
  command passed from the unchanged shell. So no release regressed, and the verdict followed
  the launch.
- **Ignored files.** A governed product tagged a release with three failed hosted runs. A tracked
  test pinned a digest of a value that includes ignored build output, so the full proof passed
  only in the lane that held the build.
- **The holder.** DR-0029 records that a verdict is not yet free of its holder: the prover of a
  unit is its landing owner.
- **A variable that a gate needs.** One governed repository's gate needs the path of a browser,
  which its hosted job declares as an environment variable. Under an empty environment that gate
  blocks. So the empty environment that cures the third case causes this one.
- **A rule kept outside the product.** The releasing host launches every proof from an empty
  environment with a home directory, a system path and a temporary directory. Scripts outside
  the product keep that rule.

The package cache is also an output that nothing bounds. Lanes, tests and proofs on the
releasing host build into the one uv cache that every repository of that host shares, while
the hosted jobs use a cache root of their own. Measured by the session that keeps the host's
supply: on 2026-11-14 that cache held 287 GB, of which 284 GB were entries that nothing
referenced, most of them copies of one test fixture and local builds of this product. Trimmed
to 12 GB, it held 18 GB two days later. Read again on 2026-11-17 for this design, with the
bucket's own directory names and `du`: 39 unpacked wheels of this product hold 12.3 GiB of the
16.9 GiB in the archive bucket, about 324 MiB each, every one a distinct build installed from a
path or URL; 167 editable builds of this product hold 183 MiB; 8,522 editable installs of one
test fixture hold 133 MiB. The wheels stay referenced, so no pruning removes them. Which command
wrote them is not measured. uv's own pruning cannot run there while long-lived holders keep the
cache open. The owner asked for the root fix on 2026-11-16, as that session relayed.

The design study behind this Change measured both kinds of gate child. A declared command's
child receives every variable of its launch, credentials included, and the first tool on the
launch path. A provider's child receives the locked tools and still every credential. The
design contract already says that declared commands run in the locked toolchain and that failure
evidence keeps the resolved binary; neither holds for a declared command today. A rule that
changes what a governed repository's gate receives reports before it blocks, by the committee's
rule R14. The owner decided on 2026-11-17 that a declared command's child is built from a list by
a state that each repository declares, that the default state reports and changes no child until
0.3.0, and that 0.2.0-beta.13 lands the report. This Change is the report.

## What Changes

- An executed `ethos prove` result states, in `summary.environment`, what its declared commands
  inherited from the launch: the mode, the count of variables, the count outside the product's
  one list of kept names, the classes of credential among them, whether the locked toolchain
  could be read, the locked tools that the launch path resolves outside their locked install,
  and the section and variable of each key of the Git configuration overlay. It holds names,
  classes and counts, never a value. A host observation and a readiness run state the same.
- The check of each declared command names the executable that the proof started and its
  supplier: the declaration, the locked toolchain, the host's own command directories or
  another directory of the launch path. A provider gate's check names neither.
- The architecture page of the gate runner states the boundary: ETHOS does not confine a
  declared command, and the result says what it inherited.
- Nothing that a gate child receives changes. No refusal is added and no exit code changes.

Carried by draft Changes that this Change creates, each with the release that reads it again:

- `gate-child-environment` (the cut of 0.2.0-beta.14): a declared command's child is built from
  the list, the locked toolchain's path and the variables that its gate names, by a state that
  each repository declares; gate children receive no Git configuration overlay; the product
  builds the launch that host scripts keep today. The owner decided this form on 2026-11-17.
- `package-cache-root` (the build in 0.2.0-beta.14): one package cache root for each repository
  under the Git common directory, the product's own wheel installed without the cache, and the
  offline sync in the readiness tier. The owner decided this shape on 2026-11-17, and nothing of
  this Change depends on it.
- `gate-output-redaction` (the cut after `gate-child-environment` lands): one owner masks
  persisted output.
- `git-overlay-keys` (the cut of 0.2.0-beta.14): the obligation carried from
  `environment-entry`, the keys and values that local Git admits.

Not this row, each with its owner: whether a gate's inputs are closed over tracked files
(the hosted plane shows it today, and `hosted-observation` gives a landing its reader of that
plane); a gate's base as an input that the proof binds (`record-roots-one-owner`); invariance
tests of ETHOS's own measuring gates (the rule row); and a verdict that is free of its holder
(the successor record of DR-0029).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: ADDED `A proof result states the environment its declared commands inherit` and
  `A declared command's check names its executable and supplier`.

## Impact

- `src/ethos/adapters/gates/child_environment.py` (new), `src/ethos/adapters/toolchain/mise.py`,
  `src/ethos/adapters/gates/runner.py`, `src/ethos/application/proof/operation.py`,
  `src/ethos/application/proof/host.py` and `src/ethos/application/proof/report.py`.
- `tests/unit/adapters/gates/test_child_environment.py` (new), and cases or assertions in
  `tests/unit/adapters/toolchain/test_mise_supply.py`, `tests/unit/cli/test_host_gate_proof.py`,
  `tests/unit/cli/test_proof_command.py` and `tests/unit/gates/test_parallel_proof.py`.
- `docs/architecture/gate-runner.md`, `CHANGELOG.md` and four draft proposals.
- The result of every executed proof gains members. Its verdict, its gaps, its exit code and its
  Attestation do not change.

Owner: the release lead. The environment of a declared command's child is the owner's decision
of 2026-11-17, and `gate-child-environment` builds it. The shape of the cache root is the owner's
decision of the same day, and `package-cache-root` builds it in 0.2.0-beta.14.
