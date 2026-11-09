# Design

## Context

`commit_range_admission_report` validates an introduced range against a target ref's branch-role
policy, the commit grammar, signatures through the configured trust anchor and the record-marker
verifier. Ref and merge admission call it inside the hook process, which loads the installed
runtime. Proof gate providers receive the checkout's `current_head` and run under candidate
execution; a provider error records `gate_provider_error` and a timeout `unknown`.

## Goals / Non-Goals

Goals: the full proof of the ETHOS repository fails on a commit that the next publication's hosted
validation would refuse.

Non-Goals: adopters, whose validations already run one runtime; the hosted jobs, which keep
validating the real pushed ranges; network reads.

## Decisions

1. **A provider gate of ETHOS's own registry.** `commit-ranges` is read-only, offline, trust-bearing
   contract evidence that depends on `repository-audit` and has a 300 s bound. Its provider calls
   `commit_range_admission_report` directly; no command mode is added.
2. **Baselines are the observed peer tips.** For each declared peer remote and each of the accepted
   and release branches, the provider passes `refs/heads/<branch>` as the target ref and the
   tracking tip `refs/remotes/<remote>/<branch>` as both the remote head and the trusted baseline.
   A stale tip only widens the range, and a tip that is not an ancestor refuses natively.
3. **Each revision once per target policy.** A revision is validated once for each target ref whose
   range holds it, since the branch role selects the policy.
4. **No evidence is no pass.** A missing tracking ref is the advisory
   `commit_ranges_peer_unobserved:<remote>:<branch>`; when every declared peer is unobserved for
   both branches, the gate refuses with `commit_ranges_unobserved`. An absent trust anchor refuses
   with the native `commit_trust_anchor_missing`.

## Risks / Trade-offs

- A peer that was force-updated refuses until its tracking tip is fetched again, which is the hosted
  outcome too.
