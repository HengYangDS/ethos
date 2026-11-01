# Design

## Context

See [proposal.md](proposal.md). Four facts shape the design.

- **One override rule exists.** `size_resolution` (`src/ethos/repository/paradigm/size.py`) resolves
  the size group: a key the contract does not declare, a malformed value, a restated default, or a
  looser value beyond the bound or without a reason is a gap and leaves the default in force; a
  stricter value applies; a looser value within the bound applies and is reported as a deviation
  with its reason.
- **Deadlines already nest.** `command_scope(timeout_seconds=...)` sets an invocation deadline
  (`_COMMAND_DEADLINE` in `src/ethos/adapters/process.py`), and every `run_command` under it runs
  within the smaller of its own timeout and the remaining deadline. The gate runner opens such a
  scope only when a gate declares `timeout_seconds`; an undeclared gate runs unbounded.
- **The command has two composition roots.** `ethos.cli.main` opens the invocation's command scope
  and knows its `--root`; the Git hook protocol is the other entry. Adapters below them do not know
  which repository they serve.
- **The 74 literals fall into six classes** (`d747b77c6`; `windows-native-security` deletes one):

| Class                        | Sites                                                                                                                                                                                    | Values      | Meaning                                          |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------ |
| A command inside a gate      | 21 (`adapters/gates/*`)                                                                                                                                                                  | 30 to 300   | a second budget inside the gate's                |
| A native tool outside a gate | 10 (`projections/cue.py`, `openspec/*`, `starter/generation.py`, `mutation/proof_admission.py`, `mutation/publication/retirement.py`, `commit/creation.py:325`, `hook/admission.py:302`) | 30 to 120   | how long one tool run may take                   |
| A Git command                | 23 (`repo/hook/admission.py`, `starter/*`, `commit/*`, `trust_anchor/verification.py`, `content`, `mutation/carrier_edit.py`)                                                            | 10, 30, 120 | how long Git may hang before ETHOS stops waiting |
| A version or identity probe  | 9 (`toolchain/mise.py`, `native_supply.py`, `runtime/selection.py`, `runtime/retirement.py`, `cue.py:46`, `commit/creation.py:282`, `evidence/external.py`)                              | 5 to 15     | how long a tool may take to say who it is        |
| A lock wait                  | 4 (`runtime/materialization/*`, `ref_intent.py`)                                                                                                                                         | 1, 10       | how long to wait for another holder              |
| A protocol constant          | 6 (`FileLock(..., timeout=0)`, `slot.acquire(timeout=0)`, `worktree_effects.py`)                                                                                                         | 0, 5        | try once, or a fixed abort grace                 |

`tools/` holds 29 further literals, mostly in the delivery acceptance; they run outside a governed
repository's proof and keep their values until their own owners migrate them.

## Goals / Non-Goals

**Goals:**

- Every tunable value has one declaration with its default, unit and bound, and a governed
  repository may set its own value by one rule.
- Every gate runs under a deadline, and a proof says which values it ran under.
- No numeric timeout literal or timeout constant remains in `src/`, and the check keeps it so.

**Non-Goals:**

- Names and carrier paths (branch roles, binding files). They are fixed for every repository and
  belong to `owned-literals`, which reuses the declaration but not the override rule.
- Measured timeouts. The architecture design's `probe-rows` derives probe timeouts from a measured
  95th percentile; this Change gives that work the parameter it will set.
- Host-wide settings. A value applies to one repository through its binding; a slow host is served
  by the repository it runs, not by an environment variable.

## Decisions

- **The paradigm declares parameter rows; the size ceilings are one group.** `[[parameter]]` rows in
  `paradigm.toml` carry `group`, `key`, `default`, `unit`, `bound` and the `retired` keys they
  replaced, as `[[language]]` and `[[tool]]` rows do. The `[size]` table becomes two rows of group
  `size`, so `.ethos/rules.toml [paradigm.size]` keeps its keys. A lower value is stricter for every
  parameter, so the row needs no direction until a parameter needs the other one. Rejected: a second
  file for parameters, which would split one contract; one model field per parameter, which would
  make each new parameter a code change.
- **One resolution rule.** `size_resolution` becomes `parameter_resolution(rules, paradigm)` and
  resolves every declared group with the current rule and gap kinds, `<group>-declaration` and
  `binding-restatement`. Deviations name the group and key. `repository_ceilings` stays as the size
  group's projection.
- **One accessor per invocation.** `parameter(group, key)` reads a context variable that each
  composition root sets from the target repository's resolution
  (`with repository_parameters(root):`, in `ethos.cli.main` and the hook protocol), and falls back
  to the declared defaults where no repository is bound. Adapters do not take the repository root to
  read a value.
- **Gates own their budget.** Every gate runs under a deadline: its declared `timeout_seconds`, or
  the repository's `timeout.gate_seconds` (default 600, bound 7,200). A command inside a gate
  declares no timeout of its own and runs within that deadline, so the class-A literals and
  `python_quality.py`'s 600-second default go; a caller that runs gate code outside a gate, such as
  `lane format` or the archive projection, opens the deadline that gate would have. A declared
  `timeout_seconds` above the bound is a profile gap. ETHOS declares `local-install-smoke`'s, the
  one undeclared gate measured above half the default (617 to 712 seconds). Rejected: keeping
  per-tool budgets inside the gate, which made the release-tests limit unreachable for Ordo.
- **Five host parameters.** `timeout.tool_seconds` (60) bounds a native tool outside a gate,
  `timeout.git_seconds` (30) and `timeout.git_history_seconds` (120) bound Git, and
  `timeout.probe_seconds` (15) bounds a version or identity probe, each with a bound of ten times
  its default; `timeout.lock_seconds` (10, bound 100) bounds a lock wait. A Git observation that
  used 10 seconds takes the Git value: the class bounds a hang, it is not a speed budget.
- **Protocol constants are native arguments or named.** A non-blocking acquisition becomes
  `blocking=False`, which filelock 4.2 accepts in the constructor and in `acquire`. The update-ref
  abort grace keeps a named constant beside the protocol that fixes it. A repository cannot change
  them because they carry no repository-dependent quantity.
- **Evidence.** Each `gate_completed` event carries `timeout_seconds` and its source (`gate`,
  `repository` or `default`), and the proof summary lists every deviation of the invocation's
  resolution with its reason, as the paradigm report lists size deviations today.
- **The check.** An architecture test parses `src/` and `tools/` and counts keyword arguments and
  parameter defaults named `timeout` or `timeout_seconds` whose value is a numeric literal, and
  module constants named `*TIMEOUT*` assigned one. `src/` is 0 when this Change lands; the recorded
  `tools/` count only falls. Positional timeouts are outside the count.

## Risks / Trade-offs

- [A gate without a declared timeout that runs longer than 600 seconds now fails] → ETHOS declares
  each gate measured above half the default: `unit-architecture` (about 1,270 seconds, already
  declared) and `local-install-smoke`; every other gate took at most 42 seconds in proofs p3 and p4
  of `windows-native-security`. Before the release, the fleet preview reads each governed
  repository's latest proof durations, and a gate above half the default receives a declared
  `timeout_seconds` in that repository's binding before it upgrades.
- [A gate whose inner tool hung now waits up to the gate's 600 seconds instead of its tool's 30] →
  The gate fails as `gate_timeout` with its elapsed time; a repository that wants a faster failure
  declares a lower `timeout_seconds` for that gate or a lower `timeout.gate_seconds`.
- [The product and test budgets have little headroom] → Each site replaces a literal with an
  accessor call or removes it, the generalized resolution replaces `size_resolution`, and the
  declaration grows in TOML, not Python. The size tests become the resolution's tests for both
  groups, and duplicated test helpers are consolidated before new cases are added.
- [A repository sets a large value to hide a slow tool] → Looser values need a reason, stay within
  the bound and appear in every proof summary.

## Migration Plan

One lane. Without a repository value every parameter keeps today's behaviour, except that class-A
commands share their gate's deadline, undeclared gates are bounded at 600 seconds, and Git
observations wait 30 instead of 10 seconds.
