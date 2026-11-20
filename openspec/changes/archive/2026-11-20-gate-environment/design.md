# Design

## Context

See the [proposal](proposal.md). The figures below were measured on 2026-11-17 in a scratch clone
at the base of this Change, each by the command or the file that its decision names. Counts of
governed repositories come from the tracked `.ethos/*.toml` files of the 30 checkouts on the
preparing host, read as shapes only.

ETHOS starts two kinds of gate child. A declared command runs through `LocalGateRunner._run` in
`src/ethos/adapters/gates/runner.py`: its first word is resolved with `shutil.which` on the launch
path, and `gate_attempt` starts it with no environment of its own, so `run_command` copies the
process environment. A provider's child runs under `locked_environment` of the Mise adapter: the
locked tools and the host's command baseline form its path, and the `MISE_` and `__MISE_`
families are removed.

One spike set 20 dummy variables, a few for each class, and printed the names that each kind of
child received, never a value. The command child received all 156 names of its parent. The
provider child lost 11, Mise's two families with `VIRTUAL_ENV` and `PYTHONPATH`, and kept 16 of
the 20 markers: an SSH agent socket, forge tokens, cloud credentials, registry and agent
credentials, Node options and the Git configuration overlay. The preparing shell held 139 names.

The design contract states where this ends: "Repository-declared commands execute inside the
repository's selected locked toolchain, not ambient `PATH`. Failure evidence preserves the
resolved binary, argv, cwd, redacted effective path" (`docs/governance/product-design-contract.md`,
lines 403 to 405). Neither sentence holds for a declared command. The accepted requirement
`Locked execution keeps native mise policy` describes `locked_environment`, which a declared
command never receives.

Of the 30 checkouts, 17 declare 59 command gates; by distinct profile, 8 profiles declare 32
command gates and 13 provider gates in the profile, and 7 name a registry that this design did
not read. Of the 32 commands, 26 start with a bare tool name that the launch path resolves, 4
start with `mise exec --locked`, and 2 run a path of the repository. No gate declares a field
that names a variable. This repository declares 16 commands, all through its bound interpreter.

## Goals / Non-Goals

Goals:

- An executed proof says what its declared commands inherited, in names, classes and counts.
- A reader can tell from one result whether its verdict could have followed its launch.
- Each of the seven measured cases has a decision that answers it, or a named owner.
- The owner's two decisions, the child's environment and the cache root, rest on measured costs.

Non-Goals:

- Changing what any gate child receives. Decision 6 carries that to `gate-child-environment`.
- A refusal of any tree or invocation that passes today.
- The cache root, which `package-cache-root` carries (Decision 8).
- Masking persisted output, which `gate-output-redaction` carries (Decision 9).
- The keys that local Git admits from the overlay, which `git-overlay-keys` carries
  (Decision 10).
- The children of providers, hooks, publication and Git, whose environments have their own
  owners.

## Decisions

1. **This Change reports, and builds no child's environment.**
   - **Rests on:** the committee's rule R14, under which a rule that is new to governed
     repositories reports before it blocks; the spike of Decision 6, which shows the two ways a
     built environment blocks a passing gate; and the checkouts, where no gate names a variable
     and the files show for none of the 26 bare commands whether its tool is locked.
   - **Considered:** stating the boundary in prose alone, which costs no line and leaves every
     case where it is; building the child now, estimated at 170 product and 260 test
     line-equivalents, which blocks a gate with an unnamed variable on the day it lands; and
     refusing an executable outside the locked toolchain (Decision 7).
   - **Chosen because:** the report is the first declared state of the rule that Decision 6
     enforces, and it lets each repository see what its gates inherit before anything is taken
     away. It measures 124 product and 150 test line-equivalents by the source budget's own
     counter. Accepted: after this Change a gate child still receives every class of
     credential, and only the result changes.
   - **Applies to:** executed `prove` results: a governed proof, a host observation and a
     readiness run. It covers no child of a provider, a hook, a publication or Git.
2. **`summary.environment` holds names, classes and counts, never a value.**
   - **Rests on:** appendix A.7 of the archived `rc-plan` design, which names
     `summary.environment` as the place where a result says what it dropped; the result schema,
     where `summary` is an open object; and the spike of the two kinds of child.
   - **Considered:** listing every name outside the list, which was 132 names on the preparing
     shell, most of them an agent harness's own; naming each credential variable, where a name
     can identify a service; and one diagnostic on each check, which changes the
     `diagnostic_count` of every passing command from zero.
   - **Chosen because:** seven members answer the measured cases and stay small: `mode`, which
     is `inherited` in this Change; `names`; `outside_allow_list`; `credential_classes`, drawn
     from `ssh-agent`, `forge-token`, `cloud-credential` and `credential`; `locked_toolchain`,
     which is `declared`, `undeclared` or `unread:<code>`; `outside_lock`, the Mise adapter's
     own codes for the declared tools that the launch path resolves outside their locked
     install; and `git_overlay_keys`, the section and variable of each key (Decision 10).
     Accepted: a class is read from a name's shape, so a secret under a plain name is counted
     and not classed.
   - **Applies to:** every `prove` result that executed gates. A result that executed none
     carries no such member. A declared tool whose install is missing is named as the Mise
     adapter names it today.
3. **The check of a declared command names its executable and its supplier.**
   - **Rests on:** the contract's "resolved binary"; and a spike that ran one command through
     the gate runner under three launch paths: it started interpreters 3.14, 3.14 and 3.9,
     passed each time, and none of the 12 fields of its result named the binary.
     `NativeExecution.executable` holds the path and reaches a result only for a gate with
     native outputs.
   - **Considered:** naming every executable that the child starts, which needs process tracing
     and has no portable owner; and naming only the first word, with `outside_lock` saying what
     the child's own lookups would find for each locked tool.
   - **Chosen because:** the first word is what ETHOS itself resolves, and the pair answers the
     third case: on the preparing shell the launch path resolved 11 locked tools outside the
     lock, and none from an empty launch. The supplier is `declared` for a path that the
     declaration names, `locked` for a locked install, `host-baseline` for the host's own
     command directories, `launch-path` for any other directory, and `unresolved`.
   - **Applies to:** each declared command's check in `data.checks`: its summary in a governed
     proof, and the whole check in a host observation or a readiness run. A provider gate's
     check names neither: both members are empty. A command that timed out or was not found
     names both too.
4. **One list of kept names has its owner in the product, and it is short.**
   - **Rests on:** the releasing host's rule, which keeps a home directory, a system path and a
     temporary directory; the 21 names that
     `tools/ci/delivery/acceptance/host_environment.py` keeps for the release journey; and the
     spike, where 132 of 139 names lay outside a list of 22.
   - **Considered:** the spike's 22 names, which include the locale, the terminal and the shell;
     each one is a way for a verdict to follow its launch, since a locale changes sorting and
     encodings. And reading the tools' list, which the product may not import.
   - **Chosen because:** the list is `HOME`, `TMPDIR`, `USER`, `LOGNAME` and `PATH`, with the
     system names that Windows needs: `APPDATA`, `COMSPEC`, `LOCALAPPDATA`, `PATHEXT`,
     `SYSTEMDRIVE`, `SYSTEMROOT`, `TEMP`, `TMP`, `USERNAME`, `USERPROFILE` and `WINDIR`. Names
     compare without case, as `run_command` compares the names it removes.
   - **Applies to:** the count `outside_allow_list` in this Change, and what a child keeps once
     Decision 6 is built, where the product replaces `PATH`. The tools' list converges on this
     one in `gate-child-environment`.
5. **A report that cannot be read says so, and no report changes a verdict.**
   - **Rests on:** `locked_environment`, which raises for a lock that is missing, incomplete or
     not trusted; the spike, where reading the lock once took 0.08 seconds; and
     `report_verdict`, which reads a diagnostic's severity and gaps and nothing of a summary.
   - **Considered:** failing the proof when the lock cannot be read, which is a new refusal; and
     leaving the member out, after which a reader cannot tell an unread lock from a clean one.
   - **Chosen because:** `locked_toolchain` then holds `unread:<code>` with the adapter's own
     code, or the class of an error that carries none, `outside_lock` is empty, and the gates
     run as they do today.
   - **Applies to:** the result alone. The Attestation and its schema do not change, so a
     verdict's record does not yet say what it inherited; `gate-child-environment` decides that
     with the built environment.
6. **A declared command's child is built from the list in `gate-child-environment`, by a state
   that each repository declares.**
   - **Rests on:** the contract's sentence on the locked toolchain; and a spike that started a
     child with the list, the locked environment and one named variable: 20 of 144 names reached
     it and no marker, the named variable arrived, building it took 0.21 seconds, and a tool
     that the lock does not hold was absent from its path. The gate model forbids unknown
     fields, so a runtime that does not read a new field refuses a profile that uses it.
   - **Considered:** building it for every repository at once, which cures the third case and
     causes the sixth on the same day, against R14; never building it, which keeps MCP proof a
     preview and needs the contract's sentence amended; and an opt-in on each gate alone, which
     leaves no state of the repository to report.
   - **Chosen because:** it changes what a governed repository's gate receives, so it was the
     owner's to decide. The owner decided on 2026-11-17: the child is built from a list by a
     state that each repository declares, the default state reports and changes no child, and
     the default flips at 0.3.0. The draft designs the rest: a gate names the variables that it
     needs, by name only; the path is the locked tools and the host baseline; and a tool outside
     the lock ends as today's `missing_command`.
   - **Applies to:** nothing in this Change. The draft carries the first, third, sixth and
     seventh cases to their cure, with the launch that host scripts keep today.
7. **No executable is refused for lying outside the locked toolchain.**
   - **Rests on:** the report spike, where an ordinary shell on the preparing host resolved 11
     locked tools outside the lock; and the 26 commands that start with a bare tool name.
   - **Considered:** the refusal, estimated at 40 product and 80 test line-equivalents, which
     is the least code and would refuse those commands from any shell that is not empty.
   - **Chosen because:** it is the symptom of Decision 6 without its cure. Under a built path a
     tool outside the lock is not found, which is an existing result.
   - **Applies to:** this Change and the draft. `outside_lock` and the supplier report the same
     fact without a refusal.
8. **The package cache gets a root of the repository in `package-cache-root`.**
   - **Rests on:** the host's cache, read with `du` and its buckets' directory names: 39
     unpacked wheels of this product hold 12.3 of 16.9 GiB, each a distinct build installed from
     a path or URL. Runtime materialization sets `UV_NO_CACHE`; the one wheel reference that a
     child receives without it is the observer requirement of a native attempt. Measured with
     uv 0.13.8 on private caches, in three runs: a lane cache seeded with the lock's 121 wheel
     directories took 1.8 to 3.7 seconds and 686 MiB of apparent size, and an offline sync from
     it 1.5 to 2.3 seconds; uv refused a store that it cannot write, and one whose buckets it
     cannot write, in three link modes; a dry run of the offline sync passed on an empty cache,
     so only the real sync can be a readiness check; and installing the project without the
     cache took 1.6 to 2.2 seconds and left the cache unchanged.
   - **Considered:** a root for each lane, which the lane's end bounds and which costs the seed
     for every lane, in real bytes where files cannot be cloned; one store that is only read,
     which uv does not support; and leaving the host's cache, after which the second case
     returns with the next cleaner.
   - **Chosen because:** the owner decided the shape on 2026-11-17: one package cache root for
     each repository, under the Git common directory; the product's own wheel installed without
     the cache; and the sync run in readiness. It needs no seed. The draft designs the rest: the
     root lies beside the native tool cache, and an explicit `UV_CACHE_DIR` still wins, as the
     hosted jobs set it. It is estimated at 90 product and 150 test line-equivalents. Accepted:
     a proof fails until its repository's root is filled once by an online locked sync.
   - **Applies to:** the second case and the growth, built in 0.2.0-beta.14. Nothing of this
     Change depends on it. The draft's first task measures which command writes the product's
     wheels.
9. **One owner masks persisted output after children stop receiving credentials.**
   - **Rests on:** a search of the product for redaction, which finds peer identity and the
     secret scan's own flag in 16 files and no owner of a gate's output; the proof operation
     and the proof artifact, which carry both streams whole; and the accepted requirement
     `Native command failures keep their complete outcome`.
   - **Considered:** masking now, by the values of variables whose names look like
     credentials, which rewrites evidence while every credential still reaches every child.
   - **Chosen because:** a child that never received a value cannot print it. After Decision 6
     only the variables that a gate names can leak, and one owner masks exactly those values
     where the proof writes its record. It is estimated at 60 product and 120 test
     line-equivalents, and it modifies that requirement.
   - **Applies to:** `gate-output-redaction`. Until it lands, a result and its record can hold
     what a gate printed.
10. **The Git configuration overlay is named now, withheld from gate children with Decision 6,
    and declared for local Git in a Change of its own.**
    - **Rests on:** the obligation that `environment-entry` handed to this row; the spike, where
      the overlay's count reached both kinds of child; and `src/ethos/adapters/repo/git.py`,
      which gives local Git every key but a wildcard `safe.directory` and holds 490 of its 500
      effective lines.
    - **Considered:** admitting only declared keys here, which changes every Git call of the
      product and of its suite and needs that module split first.
    - **Chosen because:** `git_overlay_keys` names each key by its section and its variable,
      so a result says what the launch carried. A key's subsection can hold a URL with a
      credential, so it is left out, and text that is no key is named `unreadable`; a key's
      value is never read. A built child receives no Git variable, which meets "other children
      get no overlay" of appendix A.7. The keys and values that local Git admits are a design
      for every Git call, estimated at 40 product and 80 test line-equivalents.
    - **Applies to:** `git-overlay-keys`, which carries the declared keys, the dropped keys in a
      result, and no overlay for signing.
11. **Tracked closure, a gate's base, invariance and the holder stay with their owners.**
    - **Rests on:** the fourth case, which a hosted run from a fresh checkout showed and a local
      proof could not; the fifth, which DR-0029 records; and the draft's candidates, of which
      three name no variable and no cache.
    - **Considered:** proving from a materialized copy of the tracked tree, which closes a
      gate's inputs and is not sized here; and a count of ignored entries in the result, which
      every lane would report as nonzero.
    - **Chosen because:** each has an owner that already holds its subject. The hosted plane is
      the one that is closed over tracked files, and `hosted-observation` gives a landing its
      reader of that plane. `record-roots-one-owner` owns what a gate reads of a record root.
      Invariance tests of ETHOS's own measuring gates wait for the rule row, as the draft said.
      A verdict that is free of its holder needs Decisions 6 and 8 built first, and its claim
      belongs to the successor record of DR-0029.
    - **Applies to:** the fourth and fifth cases, which this Change does not cover.
12. **The design contract states the launch as it is, in one sentence, and the gate runner's page
    states the rest.**
    - **Rests on:** the committee's resolution of 2026-11-17, which the owner approved: the row is
      done only when the contract states the boundary. The contract page holds 500 non-blank lines,
      which is the document ceiling, so its paragraph keeps its six lines.
    - **Considered:** keeping the contract's sentence as the target that Decision 6 builds, which
      this design first chose and the resolution overrode, since 0.2.0 ships no list-built child;
      five sentences in the contract, which pass the ceiling by seven lines; and removing other text
      of the contract to make room, which is a larger edit of that page than this row needs.
    - **Chosen because:** a contract that states a target as a fact is false in every release that
      does not build it. One sentence states the fact. The page that tells a reader how a command
      runs states what a result reports and that `inherited` is the only mode.
    - **Applies to:** the first sentence of the contract's paragraph on repository-declared
      commands, and `docs/architecture/gate-runner.md`. The contract's next sentence, on what
      failure evidence preserves, is not changed here. The state in which a child is built from the
      list, and what a detached run's children receive, are carried by `gate-child-environment`.

## Risks / Trade-offs

- The report can be read as protection. It is none: after this Change a declared command still
  receives an SSH agent socket and every token of its launch.
- A class is a guess from a name. A token under a plain name is not classed, and a harmless
  variable whose name ends in `TOKEN` is.
- A proof asks the lock at most twice, once for the suppliers of its commands and once for its
  summary; one such read took 0.05 seconds in five reads at the base. A lock that cannot be read
  is reported and costs the proof nothing else.
- `names` counts the process that ran the proof, so it includes the Change and the actor that
  the invocation itself sets. Those reach the child too.
- An executable's path names a directory of the host. A result already holds such paths, and
  the Attestation does not gain this one.
- A reader that compares a whole summary or a whole check of a host observation meets new
  members. The hosted verification reads its members by name.
- The list is short. A gate that needs a locale will name it once Decision 6 is built, and until
  then the count alone says how far a launch is from the list.
- Four drafts follow one row. Each names its owner and the release that reads it again, and the
  two that the owner decided build nothing in this Change.
