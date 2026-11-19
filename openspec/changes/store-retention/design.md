# Design

## Context

See the [proposal](proposal.md). Two stores are in scope, and each has a previewed verb today.

- **The Git-common store.** `ethos hook retire-records` (`src/ethos/application/retention.py`)
  previews and applies the retirement of its owned kinds: proof-check documents, merge preimages,
  gate attempt archives and terminal lane retirement units (`adapters/store/retention/kinds.py`).
  It runs only as the runtime that the repository selects and refuses while a proof holds the
  slot. Its preview sums the bytes of candidates and of files that no writer produced; nothing
  sums the store. `retention.status_bytes` is declared (1 GiB) and has no reader: the plan's
  Appendix D.3 gave it to `ethos status`, which was to report candidate bytes and suggest the
  preview above it, and that sentence was not built.
- **The host store.** Each installation records the repositories that select or hold it under
  `consumers/` (`adapters/repo/runtime/host_store.py`). The cleanup that ends `hook install`
  retires an installation that no record needs and no process uses
  (`materialization/host_retention.py`, `retire_unused_installations`). A consumer whose path is
  gone answers `absent`: its record and its installations stay, and the report names it.
  `ethos hook retire-supply` plans only installations that hold no consumer records, under the
  store's `install.lock`, with a scan of repository roots and a plan digest.
- **The readers of consumer records.** Four (`grep -rn installation_consumers src/ethos`): the
  cleanup, `retire-supply` (which skips an installation that has records), the writer check of
  `retire-records` (an installation that names this repository, or whose records cannot be read,
  is a writer root) and the read of release predecessors (each recorded repository is a subject,
  and one it cannot read is counted as unread).
- **The reading of absence.** `_consumer_state` asks `Path.exists`, outside the function's `try`.
  For a path below a directory of mode 0 the standard library's call raises `PermissionError` on
  Python 3.12.16 and 3.13.18 and answers False on 3.14.10, and `os.lstat` raises on all three
  (one probe, run on each interpreter). On 3.14 the product then answers `absent` (run). Read
  and not run: before 3.14 the exception leaves the reader and the whole cleanup defers. That
  reader's answer belongs to another Change (see the Non-Goals).
- **The observation.** The accepted quality requirement on owned temporary resources already has
  the scenario `Long-running resource acceptance is independently observed`: real workloads over
  24- and 48-hour windows, with growth, orphan age, high-water use and cleanup latency inside
  declared limits, which one manual sweep does not satisfy.
- **Authorization.** The apply of both verbs is declared `authorization="authorize"` and
  `destructive=True` (`contracts/operations/hook.py`). The row that gives the catalog its
  delegation rule has not landed.

## Goals / Non-Goals

Goals:

- An explicit, previewed and authorized release of a consumer that the host reports as absent.
- A report of each store's bytes against a declared budget, which can be read three times over 48
  hours.
- No change for an invocation or a tree that exists today.

Non-Goals:

- A budget that refuses. A later rule of that kind needs its own decision record.
- `ethos status` naming a budget row that is over, which is what remains of D.3's sentence.
  Owner: this row's next slice, read at the cut of 0.2.0-beta.14.
- Publication requests, superseded lane units and the verb's own plans and receipts as retirable
  kinds. The archived apply design left them to `record-retirement-kinds`, which no Change holds.
  They are this row's remainder, read at the cut of 0.2.0-beta.14, and the row stays open until
  they land.
- Scratch under the temporary root, and what a proof writes into a lane: `proof-output-scratch`.
- Authorization by delegation: the row that lands the catalog's rule.
- The reader `_consumer_state`. The Change `unsearchable-path-absence` owns it, under the
  owner's reading of 2026-11-17: absent on every supported interpreter, which keeps the record
  and the installations and only names the consumer.

## Decisions

1. **The release joins `ethos hook retire-supply`, behind the switch `--release-absent`.**
   - **Rests on:** where the records live and who locks them. The records are files of the host
     store, read under its `install.lock`; `retire-supply` holds that lock, scans roots and
     applies a previewed plan today. `retire-records` belongs to one repository's store, runs
     only as that repository's selected runtime and refuses under a held proof slot. No
     measurement decides this; the shape of the two verbs does.
   - **Considered:** (a) a mode of `retire-records`, as the plan's Appendix D.5 wrote it: a
     second lock and a scan in a verb bound to one repository, estimated at 60 more product
     lines, and the release could run only as one repository's selected runtime although the
     records belong to no repository; (b) a new command: one more entry in every table that
     restates the catalog; (c) a grace period after which an absent consumer counts as
     released, which the archived `absent-consumer-liveness` design rejected: no duration tells
     an unmounted volume from a deleted repository.
   - **Chosen because:** each store keeps one previewed verb, and a switch leaves every
     invocation of today byte-equal: without it no consumer record is planned. Accepted: the
     plan's words "joins the verb" are amended, which its decision 5 allows.
   - **Applies to:** the host store on every platform. Not the Git-common store.
2. **The release reads absence itself: only the host's answer that no entry exists.**
   - **Rests on:** the probe of the context, and two defects found in this area on 2026-11-17,
     both from a path predicate that answers differently before and from Python 3.14.
   - **Considered:** reusing the `absent` of `_consumer_state`, which binds a destructive step to
     a word that also covers a place the host cannot look at; catching the exception of
     `Path.exists`, which changes nothing from 3.14, where no exception arrives.
   - **Chosen because:** `os.lstat` raising `FileNotFoundError` or `NotADirectoryError` is the
     same statement on the three supported interpreters. Any other failure is unknown, and an
     unknown consumer is never planned, so no authorization can release it.
   - **Applies to:** the plan and the recheck before each unlink. No existing reader changes, so
     the cleanup's report and the release's plan may differ for a place that cannot be searched:
     the report may say `absent` where the plan holds nothing.
3. **The release unlinks consumer records and removes no installation.**
   - **Rests on:** `retire_unused_installations`, which retires an installation whose records
     need it no longer and into which no process or binding refers, at the end of every
     `hook install`. Read, not run, for the four readers of the context: an installation whose
     `consumers/` directory is empty reads as needed by no consumer in the cleanup, stays
     outside the plan of `retire-supply` without the switch, is no writer root, and gives the
     read of predecessors one subject fewer to count as unread.
   - **Considered:** removing the installation in the same apply, which makes a second owner
     that deletes installations and repeats the check for a running process.
   - **Chosen because:** one owner deletes installations. Accepted: the bytes go at the next
     cleanup, so the result names that cleanup as its next step and the bytes it would free.
   - **Applies to:** recorded installations. One without records stays with `retire-supply`
     without the switch.
4. **A scanned repository that names the installation is recorded before any record goes.**
   - **Rests on:** the moved repository of the known defect; the apply of `retire-supply`, which
     already records each scanned repository whose selectors name an installation.
   - **Considered:** releasing without a scan. A moved repository then loses the installation it
     selects at the next cleanup and has to pin again.
   - **Chosen because:** a move is the one case the host can prove: the new path's selectors name
     the installation that the old path recorded. A scanned repository whose selection cannot be
     read, or is in progress, keeps every record out of the plan, as it keeps every installation
     without records today.
   - **Applies to:** repositories at or directly under a scanned root. An unmounted volume cannot
     be scanned; its release is the person's statement. A consumer that returns after its
     installation was retired meets the accepted scenario on an external selected runtime that
     has disappeared, which this Change leaves as it is.
5. **A plan digest binds every record, and the existing gaps answer every refusal.**
   - **Rests on:** the contract of `retire-supply`: a preview that writes nothing, a digest over
     the plan, and `--expect-plan`, `--apply`, `--authorize`.
   - **Considered:** a persisted plan as `retire-records` writes, which needs a plan directory in
     a store that has none; new gap codes, each a row in the gap registry.
   - **Chosen because:** the digest covers the installation, the record and the consumer path of
     every row, so a record that appeared, went or changed refuses with `host_store_plan_changed`.
     A missing plan answers `host_store_plan_required` and a missing token
     `authorization_required`. Without an authorization nothing is unlinked. With one, the
     release still never unlinks the record of a path that exists or whose absence is unknown,
     never removes an installation, and writes nothing in a repository: it takes a scanned
     repository's selection lock without waiting, as the scan does today.
   - **Applies to:** the switch's two modes. The refusals can meet only an invocation that uses
     the new switch.
6. **The store report joins the preview of `retire-records`.**
   - **Rests on:** the preview is the one command that already reads the whole store. Measured
     by the budget tool on a spike that was never run: 34.1 product line-equivalents for the
     walk and the row.
   - **Considered:** `ethos status`, where D.3 put it: candidate bytes need every artifact read
     and classified, in the read that every agent starts with; a new read-only command;
     allocated blocks as the unit, which differ by file system.
   - **Chosen because:** the report costs one walk beside a scan that already reads every kept
     file. It gives, for each top-level name of the store, the regular files, the sum of their
     sizes without following a link and the directories it could not read, and the time of the
     read in UTC.
   - **Applies to:** the Git-common store of the repository whose selected runtime runs the
     preview. Trees of other owners (`runtime`, `packages`, `hooks`, `tool-cache`) are reported
     and not judged.
7. **Budgets are parameters of the `retention` group, in bytes.**
   - **Rests on:** the accepted requirement `Tunable values are declared parameters`; the
     declared row `status_bytes`; five installations of 687,372 to 695,212 KiB each on the
     preparing host (`du -d 2 -k`, which counts allocated blocks and not file sizes).
   - **Considered:** the host declaration as the owner of the host row, which is the right owner
     of a value that every repository of a user shares and costs a field of that declaration;
     product constants, which no repository can change; one row for each kind.
   - **Chosen because:** two rows answer the plan's three stores. `status_bytes` bounds the bytes
     in the directories that the verb owns, of a repository's store; its comment in the paradigm
     says so. A new row `host_bytes` (4 GiB, bound 1 TiB: about six runtime copies at the
     measured size) bounds the host store's installations, and the preview of `retire-supply`
     reports it, read through the parameters that the console binds to the invocation's
     repository: reading it from the accepted branch, as the other verb reads its floors, would
     refuse a repository without that branch, and a row that only reports needs no such guard.
     The stores that a proof writes to are the owned kinds, which the first row covers, and
     scratch, which `proof-output-scratch` owns.
   - **Applies to:** the report of the invoking repository. A binding's own value changes what
     that repository prints for the shared host store and nothing else.
8. **At a budget nothing refuses.**
   - **Rests on:** DR-0029: a rule that can block has a declared state, and no release adds a
     refusal to a tree that passed its predecessor.
   - **Considered:** a required gap for a row that is over; a proof that stops over budget; an
     apply that starts by itself, against the plan's rule that no other command runs the verb.
   - **Chosen because:** a row is `within` or `over` in a summary, or `unread` with a count
     where a place could not be read, so that an incomplete read never says `within`. Verdict,
     exit, gaps and next step stay what they are: the preview already names the apply when
     it has candidates. A row that is over with no candidate says so, and the repair is
     time or a higher value.
   - **Applies to:** every release through 0.2.0. A blocking state would be a new rule with its
     own record.
9. **The 48-hour observation is three previews' results, read by a second session.**
   - **Rests on:** the accepted scenario named in the context; the release-candidate gate's item
     on retention; DR-0029's rule that a session other than the authors' reads a result.
   - **Considered:** a sample record in the store with a reader that sums a window, estimated at
     50 product and 70 test lines, which adds an own-record kind that nothing retires yet;
     sampling inside `ethos status`, which writes during a read.
   - **Chosen because:** it costs no product line beyond decision 6. Each result carries the
     build that produced it and the time of the read. The record holds: a first and a last
     result at least 48 hours apart and one near the middle; one build in all three; at least
     one full proof and one lane retirement between the first and the last; every row `within`,
     or `over` and then `within` after an apply whose receipt holds no deferral. The reader
     derives growth, high-water use and cleanup latency from the three.
   - **Applies to:** the releasing checkout's store and its host's store, on the frozen beta.
     Not the stores of governed repositories, and not hosted runners.
10. **Authorization stays the catalog's.**
    - **Rests on:** the plan's decision 5, item 1; the operation declaration, whose `modes`
      helper gives an apply the tokens that its authorization kind names.
    - **Considered:** a delegation check inside the release, which would build the rule in one
      verb before its owner row designs it.
    - **Chosen because:** the switch is a request field of the existing destructive operation,
      so the rule that binds `hook.retire-supply.apply` binds the release, today and after the
      delegation row lands.
    - **Applies to:** both verbs. Nothing here waits on the delegation row.

## Risks / Trade-offs

- A person can release a consumer on an unmounted volume. The preview names each path and what it
  holds, and a consumer that returns pins again; that is the cost of any release at all.
- The report walks trees of other owners, such as runtime generations with many files. It runs
  only in the manual preview.
- Sizes are sums of file sizes. A file system that shares blocks holds fewer bytes than the
  report says, and `du` will not agree with it.
- Nothing retires the verb's own plans and receipts yet, and each preview writes a plan whose
  cutoffs hold its time (read, not run). The report shows them, which keeps the gap visible.
- The path predicates of this area answer differently before Python 3.14. The release avoids them
  by construction, and its tests still have to run on the two older interpreters.
- The catalog gains one flag, so every table that restates the catalog changes with it.
- The sizes are a spike's and an estimate. The row enters a batch only with a size measured on
  its patch.
