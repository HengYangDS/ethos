# Design

## Context

`commit_range_admission_report` validates an introduced range with the commit grammar, signatures
through the configured trust anchor and the record-marker verifier; it chooses the commit policy per
revision, the candidate's from the head and the incumbent's from the baseline commit, and for an
existing update it judges `HEAD --not <remote head>`, as hosted CI does. Ref and merge admission
call it inside the hook process, which loads the installed runtime. A proof gate provider receives
the checkout's `current_head`; every proof runs providers with `candidate` false
(`LocalGateRunner(candidate=not exact)`). Hosted CI runs the same full set in a checkout whose only
remote is `origin` (`tools/ci/hosted_verification.py`).

## Goals / Non-Goals

Goals: the full proof of the ETHOS repository fails on a commit that the next publication's hosted
validation would refuse.

Non-Goals: adopters, whose validations already run one runtime; the hosted jobs, which keep
validating the real pushed ranges; network reads; the commits that `ethos land` creates after the
proof (merge, closeout and archive commits); GitLab's `hook commit-range --check peer-identity`
step.

## Decisions

1. **A provider gate of ETHOS's own registry.** `commit-ranges` is read-only, offline, trust-bearing
   contract evidence that depends on `repository-audit` and has a 300 s bound. It declares
   `profile = "product"` with its own `tool_adapter`, so the proof binds its provider to the
   candidate's `src/ethos/` and not to the installed wheel. The provider calls
   `commit_range_admission_report` directly; no command mode is added.
2. **Baselines are the observed peer tips.** For each declared peer whose remote the checkout
   configures and each of the accepted and release branches, the tracking tip
   `refs/remotes/<remote>/<branch>` is the remote head of an existing update. A stale tip only
   widens the range, onto commits already published, which the note's `git fetch` corrects.
3. **One judged range per tip.** Peers and branches that share a tip share one range, judged once
   and recorded with every holder, since the policy is chosen per revision.
4. **No evidence is no pass.** An invalid publication declaration refuses with its own gaps. A
   configured peer without a tracking tip for a branch is the note
   `commit_ranges_peer_unobserved:<remote>:<branch>`; when no configured peer has a tip, the gate
   refuses with `commit_ranges_unobserved`. A checkout that configures no declared peer remote
   passes with `applicable` false and the note `commit_ranges_no_peer_remote`. Notes are `note`
   diagnostics, which the gate runner does not promote to gaps. An absent trust anchor refuses with
   the native `commit_trust_anchor_missing`.

## Risks / Trade-offs

- A hosted proof judges nothing; the hosted job's `hook commit-range` step remains the hosted check
  of the actual push.
- The landing proof's stored report must show `applicable: true`; a peer-less pass is an ordinary
  pass attestation, so the acceptance reads the stored report.
- The 300 s bound rests on one timing observation of the current ranges.
