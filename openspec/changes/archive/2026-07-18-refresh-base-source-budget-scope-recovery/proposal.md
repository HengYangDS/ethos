# Preserve Candidate-Authoritative Source-Budget Scope Correction

## Why

An owned Work Lane can contain an older source-budget proof-scope correction
while `candidate/dev` already contains the later, independently governed and
archived correction. Replaying the older commit conflicts only in the correction
implementation and regressions. Treating that exact duplicate as a generic
source conflict blocks local closeout even though candidate is the declared
authority for the correction.

## What Changes

- Recognize only the three source-budget proof-scope conflict paths when an
  archived, claim-bound candidate carrier declares all of them.
- Preserve candidate stage-2 content only when it proves the global-compression
  scorecard projection and the default-versus-full proof-floor contract.
- Keep exact semantic recovery diagnostics separate from stale generated parity
  projection diagnostics.
- Keep all other path sets, missing archive/claim evidence, and incomplete
  candidate semantics fail-closed.

The recovery retains `source-budget` in the full proof. The default proof remains
the fine-grained admission floor; neither proof set reclassifies a budget result
as local code correctness.

## Capabilities

- `repository-governance`: subject=work-lane-refresh-source-budget-scope; reuse=extend; change=modify; facet:lifecycle=mutation,validation; facet:surface=cli,quality; facet:authority=source,test,openspec,claim,evidence

## Impact

The Change is a narrow refresh conflict classifier. It does not weaken
source-budget measurement, change proof floors, modify source-budget allowance
policy, or authorize remote publication.

## Out Of Scope

- Resolving arbitrary Python or test conflicts by choosing candidate content.
- Waiving source-budget breaches, altering its global measurement, or absorbing
  any foreign Work Lane.
