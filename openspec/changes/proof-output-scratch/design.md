# Design

## Context

See the [proposal](proposal.md). The places a proof writes to, read from the code at the base:

- **Scratch under the temporary root.** Six calls under `src/ethos/adapters/gates` make a
  directory there (`grep -n "TemporaryDirectory(\|mkdtemp("` over that package). The behavior
  probe's root holds the synced environment, bytecode, pytest's base directory and cache, coverage
  data and Hypothesis data, carries the owner mark and is removed in a `finally`. A process that
  is killed removes nothing. On the preparing host 19 directories with a product prefix lay under
  the temporary root (`ls -d` by prefix), 3 of them made by a gate adapter and none a behavior
  probe's; which of them a live process still used was not read.
- **The Git-common store.** Check documents with each gate's whole output, and the archive of
  each attempt that declares native outputs, are files of `artifacts`, which the retention verb
  retires after `retention.grace_seconds`. A bounded result's full text goes to `payloads`.
- **The lane, at a launcher's request.** The behavior probe copies its reports to
  `ETHOS_NATIVE_OUTPUT_DIR` when the proof's launch names it; hosted jobs do.
- **The lane, by a declared command.** The command runs in the lane with its launch environment
  (the sibling study of the gate environment measured it). A gate declares a command, its native
  outputs and no environment. Two placeholders exist: `{python}`, bound for every command, and
  `{native_output}`, replaced at launch for a gate that declares native outputs.
- **ETHOS's own registry.** Its declared commands run sessions of `tools/ci` that write reports
  under `build/evidence`, packages under `build/artifacts`, work trees under `build/runtime/work`
  and caches under `build/runtime/tool-cache`. Hosted jobs run the same sessions directly and
  upload from those paths.
- **Retirement.** A landed lane that holds a nontracked path outside a content review refuses
  with `retirement_content_review_required`. The held row `residue-class` lets the retirement
  derive that review when every such path lies in a declared, checked root. The artifact topology
  makes the evidence homes promotable, so they can never be such a root.

## Goals / Non-Goals

Goals:

- One owned scratch root for a proof attempt, so one mark names its owner and one removal ends it.
- A way for a declared command to write outside the lane that changes nothing for a command that
  does not use it.
- A report that shows each repository what its proofs leave in a lane.

Non-Goals:

- A rule that refuses evidence in a lane. It would be new law, and it needs this report in an
  earlier release.
- The environment of a declared command, including the two variables of the plan's item 10. Owner
  of the question: the owner, through `gate-child-environment`, read at the cut of 0.2.0-beta.14.
- The move of ETHOS's own sessions and registry. Owner: a following row (working name
  `proof-output-registry`), in the release after the one that reads the placeholder.
- The release of a scratch root whose owner is gone. Owner: the row that `host-reservation-guests`
  names in its decision 11, read at the cut of 0.2.0-beta.14.
- `residue-class` and its second slice. This design states what they can then rely on.
- Windows-specific behavior of the listing and the walk, which no run here covered.

## Decisions

1. **A proof attempt owns one scratch root.**
   - **Rests on:** decision 9 of `host-reservation-guests`, which marks one of the six
     directories and hands the other five to this row; the 19 directories counted in the
     context, none of which names its owner.
   - **Considered:** (a) pointing the temporary root of the proof at one directory, which that
     design rejected: it changes the temporary path of every tool a gate starts, and a process
     keeps the root it first resolved; (b) a mark in each of the six, which leaves six things to
     release after a kill; (c) a variable that names the root to every child, which changes what
     a declared command receives.
   - **Chosen because:** the run's runner owns the root. It is made when a command or a probe
     first asks for it, so a run that asks for none makes none, and it ends with the runner, so
     the proof, the host observation and the readiness run need no scope of their own. Each of
     the six makers takes it as an explicit parent, so no tool's temporary root moves. One mark
     names the owner and one removal ends the run. The runner hands the root to a probe that
     declares a parameter for it, as it hands `candidate` today
     (`adapters/gates/verification.py`); gates run on worker threads of the run, so no
     process-wide state and no environment variable carries it.
   - **Applies to:** the commands of a run (tasks 1.1 and 2.1) and the probes that run in its
     process (tasks 1.2 and 1.3, which need the parameter above in six call chains and a
     regression for each maker). A probe that a session starts in a child process makes its own
     directory as today, until that session is given the root by decision 2. A maker that runs
     outside a run of gates keeps the temporary root.
2. **A declared command names the attempt's scratch with `{scratch}`.**
   - **Rests on:** the two placeholders that exist; the absence of any environment field on a
     gate; the count in the proposal: for 21 of 25 declared commands the declaration does not
     show where the command writes, so nothing the product could set would move all of them.
   - **Considered:** (a) passing two variables to every command, the plan's first form, which is
     decision 5; (b) one new variable for every child, which is small and still a change of what
     every gate receives; (c) an `env` table on a gate, which is the design that
     `gate-child-environment` owns.
   - **Chosen because:** a command opts in by its own declaration. The placeholder is replaced at
     launch with a directory inside the attempt's root that every command of the attempt shares,
     so one command's package can be another's input. The gate's identity keeps the placeholder,
     so a reused result does not depend on a random path.
   - **Applies to:** declared commands in a proof and in readiness. No command counted in the
     proposal, and none of ETHOS's own, holds the word today (0 of 25 and 0 of 16), so no
     existing command changes. A runtime older than this reader passes the word through as it
     is, so a registry may use it only when every runtime that proves the repository reads it:
     the reader ships one release before any registry writes it.
3. **Evidence that outlives the attempt stays a declared native output.**
   - **Rests on:** the accepted requirement `Declared native outputs bind one gate attempt`; the
     attempt's archive in the store's `artifacts` (`adapters/gates/native/attempt.py`), which the
     retention verb retires and whose bytes `store-retention` reports against the row
     `retention.status_bytes`.
   - **Considered:** a directory of the store for each attempt's files, which is a new kind for
     the retention verb to classify; declaring the evidence homes of a lane as residue, which the
     topology cannot allow for a promotable home.
   - **Chosen because:** the owner store, its retention and its budget exist. This is the plan's
     "owner stores within D's byte budgets" without a new store.
   - **Applies to:** reports in the declared formats, each within the bound of the capture. Any
     other file a command writes into `{scratch}` ends with the attempt; its text survives where
     the command prints it, in the check document. A launcher that wants files names a root with
     `ETHOS_NATIVE_OUTPUT_DIR`, as hosted jobs do today.
4. **A proof reports what its attempt left in the lane.**
   - **Rests on:** DR-0029: a rule reports for a release before it can block; the count that 21
     of 25 declarations do not show their outputs, so only an observation can; the study of
     `residue-class`, in which a lane's retirement fails on what a proof left.
   - **Considered:** (a) a listing around every gate, which attributes each path exactly and
     costs two listings a gate; a focused proof of one gate attributes exactly without it; (b)
     walking every ignored root, which reads an environment's thousands of nodes for a fact that
     a residue row states better; (c) a required gap, which is a refusal for trees that pass
     today.
   - **Chosen because:** before the first gate and after the last, the proof takes Git's listing
     of nontracked paths collapsed to directories, the files of the topology's evidence and
     artifact homes by name, size and modification time, and the names directly under the work
     home. The difference is the report: for each home the files and bytes that appeared or
     changed, and each new nontracked root. It costs two listings and two walks of small trees,
     and it changes nothing that a gate receives.
   - **Applies to:** the proof that executes its gates, full or focused. Not covered: the host
     observation and the readiness run, which report no footprint; a write inside an environment
     or a tool cache, which the residue rows cover; a write outside the lane. A lane that cannot
     be listed reports that and decides as before.
5. **The two variables of the plan's item 10 are not passed to every declared command.**
   - **Rests on:** the sibling studies, each measured in one checkout. An offline sync without
     a cached wheel fails in 0.03 seconds; a sync from a filled cache takes 1.5 to 2.3 seconds,
     and the environment holds 336,542,031 bytes; the exact check of the package manager passes
     on a checkout's own environment while it is fresh, so a residue row can name it. Read from
     the code: the `ty` probe binds the lane's environment by path.
   - **Considered:** passing both, which gives each gate that starts with `uv` (7 of the 25
     counted) a second environment and a new way to fail offline, a refusal for a tree that
     passed; passing only `PYTHONPYCACHEPREFIX`, which moves bytecode alone and is still a change
     of what every gate receives.
   - **Chosen because:** a lane keeps its environment whether a gate uses it or not, so moving
     the gate's copy does not empty the lane; the residue row does. What a declared command
     receives is one decision with one owner. Accepted: bytecode beside sources, and an
     environment that a gate creates, stay in a lane until its repository opts in.
   - **Applies to:** every release through 0.2.0. It agrees with the owner's decision of
     2026-11-17 that a declared command's child is built from a list, by a state for each
     repository. This amends the plan's item 10, which the plan's decision 5 allows.
6. **After a full proof a lane holds only what the residue rows can name.**
   - **Rests on:** the table of writers in the context, read and not run; the roots that the
     study of `residue-class` proposes as rows: the environment, the Node packages and declared
     tool caches.
   - **Considered:** stating nothing and leaving the question to `residue-class`, which would
     then design against an unknown.
   - **Chosen because:** once a registry's commands write to `{scratch}` and declare their
     reports, a proof adds to the lane only the caches of the tools it runs there and bytecode
     beside the sources that a command imports. Those are rows of the plan's residue class. The
     evidence, artifact and proof-made work directories are gone, so the derivation of the
     second slice of `residue-class` finds only rows after a proof.
   - **Applies to:** the proof's own footprint. It does not cover what a lane's work leaves: a
     work directory that an agent authored, Hypothesis data of a focused run, bytecode whose
     source is gone or a handoff package. Those are unique content, and the lane keeps the
     content review for them. The report of decision 4 is a difference across one attempt and
     does not list what a lane held before it.

## Risks / Trade-offs

- Nothing leaves a lane until a repository edits its commands. The report is the only pressure,
  and a repository can ignore it.
- A placeholder that an older runtime does not read becomes a directory named `{scratch}` in the
  lane, or a failed command. The one-release rule of decision 2 is the guard, and it costs a
  release before ETHOS's own lanes change.
- A command that reads another command's output from the shared directory needs that command to
  have run in the same attempt. ETHOS's registry has such a chain (its build, its install smoke
  and its supply chain gates depend on each other in that order), so the row that moves the
  registry and the row that reuses gate results have to agree on it.
- A person who looks for a report file after a failed proof finds it only if the gate declared
  it or the launch named a root. Today the file lies in the lane.
- The listing of decision 4 does not see a write inside a root that Git ignores whole, so a
  report of nothing is not a proof of nothing.
- A proof killed before its end leaves one marked root instead of several unmarked ones. Nothing
  removes it until the release of a dead owner's scratch lands.
- The root ends when its runner is released. A reference that outlives the run, such as a held
  traceback in a long-lived server, delays the removal to the end of the process at the latest.
- The sizes are estimates, and the root's is the least certain: it travels as a parameter
  through six call chains. One of the six makers lives in a module of 492 effective lines, the
  runner has 457 and the proof operation 449, against the limit of 500 (the product's own
  measure of each file at the base), so the root has to arrive there in very few lines or a
  module is split first. The row enters a batch only with a size measured on its patch.
