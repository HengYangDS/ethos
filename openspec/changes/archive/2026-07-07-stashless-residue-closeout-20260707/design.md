## Context

Stash is a Git-local hidden stack. It is useful for a solo developer, but it is
not a repository truth surface: it is not reviewed, claimed, evidence-bound,
HEAD-bound, or visible to foreign Work Lane readers. In ETHOS terms it creates a
parallel Change carrier without a Subject, Evidence, Claim, or Chronicle.

## Design

Keep the rule minimal and upstream:

1. Mutation rules define the formal residue choice: absorb into an owned Work
   Lane or revert from the protected root after classification.
2. Pre-run hook admission rejects stash mutation commands before they can create
   or consume hidden change carriers.
3. Repository hygiene prevents current docs, rules, skills, and notes from
   teaching agents to use stash as a backup or closeout path.
4. Observation remains legal: `git stash list` and `git stash show` can reveal
   hidden state during forensics, but they do not authorize using stash as the
   carrier.

This adds no new entity. It removes a hidden carrier and forces dirty work back
into the existing kernel chain: Work Lane -> evidence -> claim -> chronicle, or
revert.

## Proof Strategy

- Unit tests cover `git stash push`, `git -C <repo> stash pop`, and
  observation-only `git stash list` in pre-run admission.
- Repository hygiene runs over tracked text and fails on positive stash guidance.
- OpenSpec validation confirms the carrier is complete before archive closeout.
