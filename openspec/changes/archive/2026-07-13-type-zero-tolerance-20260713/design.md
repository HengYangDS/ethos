## Context

The type gate has one policy owner, `.config/checks/ty/policy.toml`, and one
execution owner, `ethos.adapters.gates.ty`. Its existing two-tier policy lets
`packages/ethos` retain a count-based ratchet. The adapter loses the subprocess
return code and treats output without a terminal diagnostic count as zero;
therefore a checkout-bound runtime missing `ty` can falsely pass the gate.

## Decision

The gate will model tool execution explicitly. A successful `ty` process with
`All checks passed` yields zero diagnostics. A completed diagnostic process
must yield a terminal count. Missing tools, launch failures, malformed output,
or any other indeterminate result yield a stable blocking execution gap; an
unknown result is never coerced to zero.

The final policy contains a single zero-tolerance package set. Once the
existing diagnostics are removed, `packages/ethos` moves into that set and the
ratchet table is deleted. The command registry, proof graph, and provider
projections retain one owner command and do not duplicate type policy.

## Alternatives

Keeping a zero-valued ratchet would preserve an obsolete exception shape.
Treating missing tools as zero diagnostics confuses an execution failure with a
clean result. Using ignores, baselines, or compatibility wrappers would hide
the debt rather than remove it. All are rejected.

## Proof Strategy

Add regressions for unavailable and malformed tool results before changing the
adapter. For each existing diagnostic cluster, retain or add a behavioral test,
then apply the narrowest type-safe correction. Prove the direct `ty` run, the
owner gate, policy/CLI/CI projections, strict OpenSpec lifecycle, Claim
integrity, parity freshness, and a head-bound executed proof. Candidate landing,
accepted-root closeout, Work Lane retirement, and remote publication are later
distinct transitions.
