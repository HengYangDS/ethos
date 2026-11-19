---
subject: ethos:gate-runner
role: explanation
state: canonical
relations:
  canonical_for: proof execution
---

# Gate Runner

Status: canonical execution contract; current verification results are separate
HEAD-bound observations, not this document's state.

Purpose: explain selection, execution safety and the limits of local evidence.

The gate declarations own check identity, dependency closure, execution
identity and proof-set membership: the [packaged registry](../../system/gates.toml)
for the obligations every repository shares, and the gates a repository's
profile declares or names for its own. Native configuration owns
each tool's rules and supply. The policy compiler binds those materials; the
shared runner executes the resulting graph. Local CI uses that same full
closure rather than maintaining a second scheduler or list.

## Readiness And Execution

Run from the intended worktree with its locked environment provisioned and the
invocation actor projected into the process:

```sh
ethos prove --json
ethos prove --execute --gate repository-audit --expect-head "$(git rev-parse HEAD)" --json
ethos prove --execute --full --expect-head "$(git rev-parse HEAD)" --json
```

The first command observes readiness, not execution: planned checks remain
unknown with no exit code. Full proof requires `--execute`. Executed proof
requires the complete selected result set, successful execution and current
source/policy bindings; process success alone cannot establish acceptance.

The default proof set selects offline source checks. Full proof and local CI
also select declared carrier, security and package checks. Some require network
access for provisioning or external freshness. Missing supply or an unavailable
required observation does not pass. Hosted CI is a separate post-publication
observation, not an in-flight pipeline waiting on itself. Read the declaration
for current membership instead of copying gate lists here.

## Lane Footprint

An executed proof observes its lane before its first gate and after its last, and reports the
difference as `data.footprint`: for the evidence and artifact homes of the
[artifact topology](generated-artifact-topology.md) the files and bytes that appeared or changed,
the new names directly under the work home, and each new nontracked root of Git's listing. The
report is empty when nothing appeared. A path of those homes that cannot be read is counted as
`unread`, so a reading that is not whole never says that nothing appeared. It decides nothing: no
verdict, exit or required gap reads it, and a lane that cannot be observed reports why and raises
nothing. A bounded result keeps the counts and moves the paths to its detail. A write inside a root
that Git lists whole, such as an environment or a tool cache, is not seen, so an empty report does
not say that the lane is unchanged.

## Forge Projections

Each Forge's CI is a projection of the same gates. The gate declaration and its owner commands compile through `.config/ci/pipeline.cue` into the generated `.github/workflows/ci.yml` and `.gitlab-ci.yml`. Neither generated file is an editable source, and `ethos lane project` writes both from the model (repository-paradigm "CI for several Forges is one model" and "Repository orchestration is native").

A hosted run on a Forge is a separate observation of that Forge's plane (proof-hosts "Hosted provider observations remain evidence-class scoped"). Local proof, hosted status, ref reachability and release publication are distinct evidence states, and none stands in for another (quality "Local And Hosted Planes Stay Separate").

## Dependency Safety

The runner executes the admitted DAG through one bounded ready-node executor.
A completed prerequisite releases its dependents without waiting for unrelated
readers. Ready file-writing gates drain active readers and run alone. Results
retain canonical plan order rather than completion order. Invalid graphs fail
before execution. A dependent gate executes only after every
prerequisite has passed with exit code zero; otherwise it receives an unexecuted
blocked result naming the unmet dependency. Independent diagnostics can
continue. Dry-run projection does not execute effects or invent failed checks.
The declared inexpensive source checks precede heavy tests. Package delivery no
longer waits for coverage (`ecf55c727`); a coverage failure still fails the proof.
These prerequisites belong to the gate declaration, not a second phase registry.

Provider gates call their declared Python owner. Adapter gates invoke their
declared command. Results retain identity, verdict, exit code, diagnostics,
stdout and stderr; they do not infer success from missing evidence.

## The Environment Of A Declared Command

ETHOS does not confine a declared command. Its child receives the environment of the process that
launched the proof, credentials included, and its first word is the first match on the launch
path unless the declaration names a path. A provider's children get the locked tools and the
host's own command directories as their path, and still the other variables of the launch. So the
verdict of a declared command can follow its launch. A result that executed gates says by how
much, in names, classes and counts and never in a value:

- `summary.environment.mode` is `inherited`. `names` counts the variables of the process that
  ran the proof, the Change and the actor that the invocation itself sets among them, and
  `outside_allow_list` those beside the product's list of kept names: `HOME`, `LOGNAME`, `PATH`,
  `TMPDIR`, `USER` and the system names that Windows needs.
- `credential_classes` holds `ssh-agent`, `forge-token`, `cloud-credential` or `credential` when
  the name of a variable has that shape. A secret under a plain name is counted and not classed.
- `locked_toolchain` is `declared`, `undeclared`, or `unread:` with the Mise adapter's code, or
  with the class of an error that carries none. `outside_lock` holds that adapter's own codes for
  the locked tools that the launch path resolves outside their locked install. A lock that cannot
  be read changes no verdict.
- `git_overlay_keys` holds the section and the variable of each key that the launch sets through
  the indexed Git configuration variables. A key's subsection can hold a URL, so it is left out.
- Each check of a declared command names its `executable` and its `supplier`: `declared` for a
  path that the declaration names, `locked` for a locked install, `host-baseline` for the host's
  own command directories, `launch-path` for any other directory, and `unresolved`. A provider's
  check names neither. A Mise shim on the launch path reads `launch-path` and is named in
  `outside_lock`: the shim chooses the tool only when it runs.

A launch that holds only the kept names, with a path of the locked tools, reports zero names outside
the list and an empty `outside_lock`. The proof Attestation carries none of these members.
`inherited` is the only mode: a repository cannot yet declare that its commands start in an
environment built from that list.

## Input Keys And The Result Record

An executed run whose source still equals its commit after the gates gives each gate that
executed an input key: a digest of the gate as the policy binds it, the committed paths its
statement selects and the run's named inputs. The product's table
[`gate-inputs.toml`](../../src/ethos/contracts/gate-inputs.toml) states by provider ID what a
product provider reads. A command gate and a provider outside the table are keyed by every
committed path, and a provider that reads outside the committed tree is marked open. The named
inputs are the running product, the interpreter, the platform, Git's version, Git's attribute
classification of the committed paths and the names of the entries Git ignores; they are read
after the gates. Where the running product was built from the proved tree itself, the committed
files its wheel is built from are paths of every statement instead. No value of an environment
variable enters a key.

No gate is skipped. Every gate runs, and its decided verdict, pass or block, is compared with
the earlier decided results of the same key. The run is then written as one content-addressed
file under `gate-results/` in the Git-common store, with its head, its tree, its named inputs
and a digest of the names of the launch environment. The command's result names the record and
counts the comparisons by state; the rows stay in the record, so a result does not grow with
the gates. A differing earlier result is a note of the command's result, `gate_input_mismatch`,
outside every check: the verdict, the required
gaps, the proof artifact and the Attestation are those of a run without any record. A gate that
an unmet prerequisite held did not execute and has no row. A store that cannot be read or
written, or statements that cannot be read, leave every gate and the proof as they are, and the
result names the record as unavailable.

The record also names each committed file that a stated provider opened outside its statement,
seen in the provider's own process and not in a child, and the count of effective lines in the
Git directory's local attributes file.

## Command Scratch

A declared command names the scratch directory of its run of gates with `{scratch}` in an argument,
as it names the interpreter with `{python}` and the root of its declared native outputs with
`{native_output}`. The first command of a run that names it makes one directory under the temporary
root, marked with the run's owner once the run holds a host ticket. The scratch lies under the
launch's temporary root (`TMPDIR`, `TEMP` or `TMP`), so it is outside the lane only where that root
is, and nothing checks that. Every later command of that run receives the same directory, so one
command's output can be another's input, and the directory ends with the run. The gate's identity
keeps the placeholder. A command that does not name it is launched as it is declared, and nothing is
made. A runtime that does not read the placeholder passes the word through as it is, so a registry
names it only once every runtime that proves the repository reads it.

## Local Fallback Evidence

When no peer is reachable, `ethos publish` falls back to the proof Attestation
it already admits for the head: the proof runs the owner's declared gates.
`local_ci_fallback` reports that admission as `admitted`, `missing`,
`unavailable` or `not_required`, with text, and a missing proof names the full
proof command. The fallback never claims hosted CI success, remote publication
or installed-runtime acceptance. Those claims each need their own current
evidence.

See also: [Command Plane](../reference/command-plane.md) and
[Quality Gate Governance](../../.agents/skills/ethos-quality-gate-governance/SKILL.md).
