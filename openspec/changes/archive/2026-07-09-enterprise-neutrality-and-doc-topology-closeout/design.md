# Design

The aggregate gate lives under quality policy because it is a hard-floor
readiness read model, not a new transition command. It imports existing owner
reports for workspace status, report scorecard, product boundary, docs topology,
contributor policy, generated artifacts, release policy, generic parity,
governance context, and claim carriers.

Each planning layer maps to one or more owner checks. Required gaps are deduped
and lifted to the aggregate result, so downstream proof and report can fail on
the original owner gap names.

The gate explicitly states nonclaims: remote publication is separate, foreign
Work Lanes are observe-only without handoff or break-glass evidence, private
adopters belong only in profile/evidence boundaries, and identity authority is
external role policy rather than a single author.
