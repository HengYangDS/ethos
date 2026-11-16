# Design

## Context

See the [proposal](proposal.md). A CI peer is a declared publication peer with the `ci_cd`
capability (`src/ethos/repository/release/publication.py`). At the base the product reads a forge
in one place: `src/ethos/adapters/mutation/publication/retirement.py` lists a branch's reviews
through `gh` or `glab`, after `forge.py` resolved the peer's web repository from local connection
metadata. `git grep -nE '"(gh|glab)"' ba9a1046d -- src/ethos` finds four argv rows, all in that
module. The product holds no HTTP client: `git grep -n "urllib.request" ba9a1046d -- src/ethos`
finds two modules, and both use only its path conversion.

The repository's own `tools/ci/hosted_observation.py` reads each forge's latest run for a Nox
session. It is not bound to a commit and is not shipped, so an adopter has no reader at all.

The archived `rc-plan` design gives the form `publish --observe-hosted --expect-head <head>`, the
operation name `publish.hosted.observe`, one hosted-plane Attestation per CI peer, and the named
breaking change that a release ref needs a passing hosted observation on each CI peer. DR-0029,
accepted after that plan, lets a release add a refusal to a tree that passed its predecessor only
when an earlier release reported the rule and this one ships its repair, and it freezes new rules
from the tag of 0.2.0-beta.11 to 0.2.0.

## Goals / Non-Goals

Goals:

- One reader of the hosted runs of one exact commit on each CI peer, with the conclusion of each
  run and of each job that kept a run from passing, that tells a job the pipeline lets fail from
  a failed run.
- A command that gates on the observation; a landing preview and a release ref's probe that
  state it.
- A named gap for each peer state other than a pass, with its repair.
- A caller without forge credentials is answered `unknown`, never `pass`.

Non-Goals:

- Any refusal. A landing, a closeout and a publication admit what they admitted before.
- A stored observation: decision 5 departs from the plan here and says which Change adds it.
- A token, a credential store or an HTTP client. The provider's CLI holds the session.
- The retirement of `tools/ci/hosted_observation.py` and of its Nox session, the fixture forge
  peer with a stub executable, and the tools lines of the plan: they belong to the golden-path
  journey's row.
- Selecting peers with `--peer`, and a run that its owner dispatched to fail on purpose.

## Decisions

1. **The reader lives beside the forge resolver, and shares its bounded listing.**
   - **Rests on:** the product has one forge adapter today and no network client for a forge: the
     `git grep` of the Context, and `git grep -n "_provider_rows(" ba9a1046d -- src/ethos`, which
     finds one caller of the bounded provider listing.
   - **Considered:** a client for the two REST interfaces, which needs a token reader that the
     Change must not add; the repository's CI tool, which is not shipped and reads no exact
     commit; a new adapter package, a second home for forge calls.
   - **Chosen because:** `hosted_runs.py` sits beside `forge.py`, and the listing moves from
     `retirement.py` into `forge.py` as `provider_rows`, with one added parameter that names the
     member of an answered object. One resolver and one runner serve reviews and runs. The cost is
     that a reading depends on the JSON that two CLIs print.
   - **Applies to:** the providers `github` and `gitlab`, the two keys of one table, which the
     owner decided on 2026-11-15 to keep in one reader. A peer of any other provider is `unknown`
     with the reason `provider_unsupported`.
2. **One listing answers for a head whose runs passed; a run that failed or still runs costs one
   more read, of the jobs that did not pass.**
   - **Rests on:** the help of the installed CLIs, read on 2026-11-15 with `gh run list --help`,
     `gh run view --help`, `glab ci list --help` and `glab ci get --help` (gh 2.104.0, glab
     1.130.0): the first lists runs by `--commit`, the second prints `jobs` as JSON, the third
     lists pipelines by `--sha`, the fourth prints one pipeline as JSON. No forge was called. The
     sizes come from `hosted_observation` over recorded answers for two CI peers, serialized as a
     result is (`json.dumps` at an indent of two): 704 bytes and two provider calls for a head
     whose runs passed; 906 bytes and three calls when one peer's run of 20 jobs failed with one
     failed job; 3,908 bytes when all 20 failed.
   - **Considered:** reading every run's jobs, which the first form of this patch did: a synthetic
     entry measured 6,962 bytes at 20 jobs a run, and a clean head cost two calls for each peer.
     `src/ethos/result.py` bounds a result at 16,384 bytes and then keeps only the scalar fields
     of an entry over 1,024 bytes inline. Also the REST paths through each CLI's `api` command:
     for one provider that command takes its host from the working directory or a flag and the
     product would encode the project path, where `--repo <web URL>` carries both, as the reviews
     listing already relies on.
   - **Chosen because:** a reader needs the jobs of a run only when the run did not pass. The
     clean entry stays under the inline bound, which a regression holds, and a failed head still
     names its failed jobs. Every call runs within `timeout.tool_seconds` with prompts disabled
     and standard input closed. The cost: a job that failed inside a run that passed is not
     listed.
   - **Applies to:** one listing of at most 100 runs. A full page, a row that names another commit
     or carries no identity, and a word outside the reader's table make the peer `unknown`
     (`provider_answer_unusable`); the reader never guesses. The JSON that the four commands print
     is confirmed by task 5.2.
3. **The run's conclusion decides the run; a failed job is told apart as allowed only by the
   provider's own mark.**
   - **Rests on:** the lesson of 2026-11-14, when one job concluded as failed on both forges while
     the pipeline concluded as passed; and the release lane's script, which reads the mark
     `allow_failure` on one provider's job rows and keeps a list of job names for the other.
   - **Considered:** a declared list of the jobs that may fail, a second owner of what the
     pipeline file already says; and judging a run by its jobs, the error of 2026-11-14.
   - **Chosen because:** the pipeline file is the one owner of which job may fail, and the forge
     states its effect in the run's conclusion: a run that passed although a job failed is
     `passed`, and its jobs are not read. In a run that did not pass, a marked job is listed as
     `allowed_failure`; where the provider has no mark, it is listed as `failed`, and the run's
     state is still right.
   - **Applies to:** a peer's state, which is `failed` before `running` before `passed` over its
     runs. A cancelled run counts as failed. A peer whose runs were all skipped holds no run that
     ran and is `no_run`.
4. **A forge that gives no usable answer is `unknown`, by name.**
   - **Rests on:** the accepted requirement `Local And Hosted Planes Stay Separate`, and the
     reviews listing, which answers `unknown` when the provider refuses.
   - **Considered:** leaving the peer out, which reads as a pass; and `block`, which says the head
     failed.
   - **Chosen because:** a missing CLI, a session without credentials, a timeout and an
     unparsable answer are one fact for the caller: nothing is known. The peer carries the reason
     (`provider_query_failed`, `provider_answer_unusable`, `provider_unsupported` or the forge
     resolver's own gap), the next action a person can take, and no stderr. That action is the
     query that failed, the listing or the read of one run's jobs, so that a person reads the
     provider's own refusal; the resolver's local key; or a step by hand where no query of the
     reader answers: an answer that the reader does not use is not asked for again, and a peer
     whose provider has no reader drops `ci_cd` with its `ci_surface`, which a declaration
     holds together, or is read on its forge.
   - **Applies to:** the gap `hosted_run_unknown:<peer>`. With only such gaps the command's
     verdict is `unknown` and its exit 1. The gap's registered repair names the sign-in, after
     which observing again can answer, or points to the peer's own next action, since one code
     has four causes and a step by hand ends there.
5. **The observation is read each time. This departs from the plan, which records one
   hosted-plane Attestation per CI peer.**
   - **Rests on:** the plan's sentence in its A.5; and the consumers of this Change, which are
     the command's own result, the landing preview and the release ref's probe. None of them
     reads a past observation, and a run's state changes on the forge with no local event.
   - **Considered:** the plan's Attestation per CI peer in this Change. It needs a predicate, its
     issue and query, and a rule for how old a stored fact may be, with no reader yet to say
     which rule is right. Also a cache in Git-common state, a second store beside the Attestation
     set.
   - **Chosen because:** a stored `running` would still read `running` after the run failed, and
     a record without a reader is unproved. The departure costs two things. Nothing records who
     observed a head and when. A forge that cannot be reached at the release reads as `unknown`,
     where a record made while it was reachable would have answered.
   - **Applies to:** `publish --observe-hosted`, the landing preview and the release ref's probe.
     The stored record is added by the Change that arms the release ref's refusal, which is the
     first reader of a past observation.
6. **The command is a `publish` operation that exits by its verdict.**
   - **Rests on:** the plan names the form and the operation; the catalog test enumerates every
     selector assignment, and with the new selector it counts 108 operations and 18 unmatched
     `publish` assignments (107 and 9 at the base).
   - **Considered:** a leaf command under a new group; an exit of 0 on every verdict; a `--peer`
     selection.
   - **Chosen because:** the release lane's script gates a landing by its exit, and this command
     replaces it. A peer that failed or holds no run is `block`; only undecided peers are
     `unknown`. The gaps come in the order that decides the verdict, so the first gap names the
     peer that decided, and the next action is that gap's registered repair, or the command
     itself while a run may still conclude.
   - **Applies to:** the worktree's head, which `--expect-head` guards. A repository with no CI
     peer passes in the state `no_ci_peer`: it has no hosted plane, so no peer can fail, and a
     block would stop every landing chain of a repository without CI. The pass is stated
     where it is read: the operation's description says it, and the summary counts the CI
     peers that were observed, which is zero there. An invalid peer declaration blocks with
     its own gaps and the topology's own next action, or a general one where the topology
     names none. The observation carries that step itself, so the landing preview and the
     release probe show it too, and a repair that the registry holds for such a gap does not
     replace it. A peer state that no gap names fails the observation; it is never left out
     of the gaps, which would read as a pass.
7. **The landing preview carries the observation as data.**
   - **Rests on:** `require_closed_verdict` refuses a pass that carries a required gap, and
     `close_verdict` turns a warning into a block, so neither can hold an observation.
   - **Considered:** reading only when the preview passes, which hides the hosted state while
     another gap is open; and a summary line, which no reader of the preview has today.
   - **Chosen because:** `data.hosted_observation` on every candidate preview states each CI
     peer's state and the gaps under `observation_gaps`, a name the result's own gaps do not use.
   - **Applies to:** `land.preview`, whose declared effects gain `remote-read`. An apply, a
     closeout, a release and a re-tag read nothing. A preview of a head whose runs passed costs
     one call for each CI peer.
8. **The probe of a release ref reports the observation now; the refusal arms no earlier than
   the release after this one.**
   - **Rests on:** DR-0029: a rule reports for one release before it refuses, and the release
     that arms it ships its repair. The plan names the refusal as breaking item 8. Three cases
     are not measured by any command of this Change: a run dispatched to fail on purpose, a CI
     peer whose pipeline does not run for the accepted branch, and an SSH remote without the
     local `forgeRepository` key.
   - **Considered:** arming it in this release, which DR-0029 refuses and which would stop every
     release publication from a host without a signed-in CLI; and reporting nothing until the
     arming Change, which would arm a rule that no release had shown.
   - **Chosen because:** `ethos publish --ref <ref> --probe-remote` states the observation of its
     proof head under `data.hosted_observation` when a target is the release branch or a release
     tag, and changes neither its verdict nor its gaps. The gaps it shows are the ones that will
     refuse, with their four registered repairs; a peer whose pipeline never runs for the
     accepted branch drops `ci_cd` or gains that pipeline.
   - **Applies to:** a probe that its own request admits. A probe of any other ref, a retirement
     and a receipt's apply read no forge. The owner names the release that arms the refusal (task
     5.5); that Change carries the Breaking entry and the stored record of decision 5.

## Risks / Trade-offs

- A landing preview and a release ref's probe now call two CLIs. A host without them, or without
  a session, gets `unknown` for each peer after one failed call; a slow forge costs up to
  `timeout.tool_seconds` a call.
- A head with many failed jobs still grows its entry: 3,908 bytes for 20 failed jobs. Past the
  result bound such an entry keeps its state inline and moves each peer's detail to the result's
  detail file.
- The reader was tested against recorded answers, not a forge. A CLI that changes a key makes a
  peer `unknown`; it cannot make one pass.
- Two runs of one commit count alike. A failed run of a proposal ref keeps the peer `failed` after
  the accepted branch passed at the same commit, until that run is rerun.
- An SSH remote needs `remote.<name>.forgeRepository` before any forge read, as the reviews
  listing already does.
- `tools/ci/hosted_observation.py` and its requirement in `proof-hosts` stay beside the product
  reader until the journey's row retires them.
