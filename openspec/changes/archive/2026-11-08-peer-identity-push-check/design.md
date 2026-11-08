# Design (draft 4, scratch)

## Context

The archived `rc-plan` (Appendix F, from `peer-identity-records-draft5.md`, its 05:4x decision and
its 06:0x amendment) settles the push-time check, the backstop, the mode and the keyless verifier.
`peer-identity-redaction` ships the grammar, the feed, `record_roots` and `effective_record_roots`
that this Change reads. Draft 2 adopted `f2-review-1.md`, draft 3 `f2-review-2.md` and draft 4
`f2-review-3.md`, none with a blocker. Labels only: H1 host, P1 and P2 ports, F1 namespace path, I1
project ID.

## Goals / Non-Goals

Goals:

- No new fed literal reaches a peer through a governed push, and a raw push meets a backstop.
- A marker edit in a record root is admitted only when it reproduces what it replaces, with no key.

Non-Goals:

- History rewriting (`history-rebuild-map`), key creation, Keychain access and record immutability.
- A scan of history: only what a push adds beyond the peer's advertisement is read.

## Decisions

1. **Range (F.4).** `push_admission_report` checks, for each ref update, the commits
   `<pushed> --not <every tip the peer advertises>`, passed to `rev-list --stdin`; tips absent
   locally are skipped and annotated tags exclude their peeled commits. `push_admission_report`
   takes `advertisement`, `network` or `tracking`. Under `network` (the hook and `execution.py`) the
   advertisement is one `ls-remote` through `run_network_git` within `seconds("git")` and no prompt,
   read once per remote per process as the invocation fact `("peer-advertisement", remote)`, which
   stores an unreadable outcome too so it is not retried; the `invocation_facts` docstring names
   this one exception to "failures are never reused". A publication therefore reads it once
   in-process and once in its hook. Its time falls inside the measured admission of the push budget.
   Under `tracking` (`request_gaps.py`, the publication request path) the range excludes the
   remote-tracking refs and no network is read. A deletion adds nothing. A pushed annotated tag adds
   its message. An unreadable advertisement is `unknown`, and under `required` refuses with
   `peer_identity_range_unknown:<remote>`.
2. **Mode.** `peer_identity.mode` (`disabled` by default, `required`) is read first, through
   `load_committed_repository_profile`, at the commit whose policy push admission already trusts: a
   new ref's creation baseline, the accepted head on accepted delivery, or the target ref's tip that
   the hook receives as `remote_head`, falling back to the creation baseline when that object is
   absent locally; never the working tree. A profile that is missing or invalid there reads as
   `disabled` with the advisory `peer_identity_mode_unread`, never as a crash or as `required`. The
   advertisement runs only under `required`, so a `disabled` adopter pays no network call. Under
   `required`, a protected peer whose remote cannot be read locally refuses with
   `peer_identity_feed_unreadable:<remote>`.
3. **Refusals.** Added lines and commit and tag messages refuse every bounded occurrence of a fed
   host, a fed full path (a one-segment namespace never alone), `:<port>` after any host, and a
   closed context with a fed value, former values included, of every protected peer, whichever peer
   the push targets. The gap is `peer_identity_literal:<form>:<n>:<m>:<line>`, where `<form>` is one
   of `url`, `scp`, `authority`, `host`, `path`, `id`, `port` or `manual`, and `n`, `m` and `line`
   are positions: no gap carries a value, and `<remote>` in the other gaps is a local remote name.
   The gaps join the report's `required_gaps` and its reason chain. Merges use `--cc`.
4. **Backstop.** `hook commit-range --check peer-identity` is a mode of the existing command: with
   the four flags its CI projection already passes, it calls `_introduced_commit_revisions` with the
   baseline that `--remote-head` names, and has its own exit. It applies no signature or commit
   policy, reads the mode at both the range baseline it resolved, whichever source supplied it, and
   the proposed head, enforces when either is `required`, and exits 1 only on a fed literal then. A
   zero `--remote-head` (a new branch) falls back to `refs/remotes/<remote>/<accepted branch>` as
   `_baseline` does for `proposal/*`; with neither it is the advisory
   `peer_identity_backstop_baseline_missing` (exit 0). Its feed comes from `CI_SERVER_HOST`,
   `CI_SERVER_PORT`, `CI_PROJECT_PATH` and `CI_PROJECT_ID` through the grammar's `Feed`, and it is
   inert without them, so only the GitLab projection carries it: one step after the policy step of
   the same job, edited in `.config/ci/pipeline.cue`. It runs on pushes to `dev`, `main` and
   `proposal/*` and on merge requests, whose base is `CI_MERGE_REQUEST_DIFF_BASE_SHA`.
   `_range_coordinates` and `test_a_main_push_still_admits_its_pushed_range` select the policy step
   by the absence of `--check`, and each adopter's job goes through its own CI declaration owner in
   its activation lane.
5. **Keyless verifier (F.6).** `_validate_commit_revisions` reads each revision's first-parent diff
   (`--cc` for a merge) and judges a changed line under an effective record root that introduces a
   marker: it pairs, one to one, with the removed line it reproduces through one public alignment
   function in `peer_identity`, which owns the closed contexts and boundaries. Split at its markers
   and at closed-context digit runs, a marker line's literal pieces appear in order in the removed
   line, each gap one admitted span and each differing digit run a number in its range. Roots per
   revision are `effective_record_roots(load_committed_repository_profile(root, rev))` at the
   commit, the incumbent baseline and the proposed head. A revision whose profile is missing or
   invalid contributes no roots of its own and is judged by the union of the roots of the incumbent
   baseline and the proposed head that read; when neither reads, it refuses with
   `record_roots_unread`, so a range never relies on roots it can change itself. It runs under every
   mode, since markers appear only after a redaction, and `--check peer-identity` does not run it. A
   marker line in an added file, or a rename read as a deletion and an addition, has no removed line
   and refuses; replay is judged the same way, since no rebuilt history is in scope. Refusals:
   `record_marker_unpaired`, `record_marker_malformed`, `record_marker_unkeyed` (a marker equal to
   the plain SHA-256 or empty-key HMAC of its pre-image).
6. **Advisories and repair.** A protected peer under `disabled`
   (`peer_identity_protected_peer_disabled`) and `peer_identity_mode_unread` are `status`
   advisories in `summary.peer_identity_advisories`, apart from the coordination count, and never
   required gaps. The readiness count, the fed literals outside the record roots,
   is the redaction preview's `outside_roots`: it reads the whole tracked tree, which took 10 s on
   ETHOS under load on 2026-11-08, too slow for every `status`. wib's `[artifacts]` table retires by
   the obligation `record-binding`, folding `durable_evidence_roots` to
   `record_roots = ["evidence/"]` and removing `state_tracked_truth`. `record_roots` and
   `peer_identity` ship in one release, so each adopter moves both keys in one profile-format lane,
   whose predecessor reports `repository_profile_invalid`.

## Risks / Trade-offs

A raw `git push --no-verify` or a hookless clone bypasses the push check, which is why the backstop
exists where the mode is `required`; a raw new-branch push stays outside the backstop; a deleted and
re-added file bypasses the added-line rule; readiness and `status` do not see a literal that the
advertisement excludes, and the publication request path may pass what the hook later refuses;
another spelling of H1, a port in free prose, headers, path names, binary and UTF-16 files are not
read; the backstop lacks the SSH port and every former value, and a new branch with no tracking
baseline stays outside it; a remote name is the owner's choice and is printed as given.
