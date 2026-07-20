## Context

`prewrite_guard` resolves effective replay context from Git metadata so that a
sanctioned `ethos lane refresh-base` can use the original Work Lane identity
while Git has detached `HEAD`. The lease was created for that named Work Lane
ref, not for an intermediate replay commit.

## Design

The guard retains `current_head` as the actual Git `HEAD`. For ordinary writes,
that observation is also `binding_head`. Only when the effective context source
is the validated Git rebase `head-name`, the guard resolves
`refs/heads/<branch>` and uses that ref as `binding_head` for the lease
comparison. The evidence surface always states `current_head`, `binding_head`,
and `head_source`.

This is a narrow correction to the binding relation, not a special admission
mode. Root, role, runtime, editor-root, target-path, holder, lease-id, and epoch
checks remain unchanged. A missing branch ref yields an empty binding and fails
closed through the existing stale-head rejection.

## Alternatives

Comparing the lease to detached `HEAD` is false during a replay and blocks the
operation it is meant to protect. Rewriting `expected_head` during rebase would
erase the lease's issuance fact and create hidden mutable authority. A second
rebase lease would duplicate coordination truth. The selected design instead
uses the already authoritative named ref and makes both observations explicit.

## Proof Strategy

The regression test creates a detached commit, declares validated rebase
context, and proves that admission observes the detached commit while binding
the lease to the unchanged Work Lane ref. Focused unit tests, Ruff/format,
claim integrity, OpenSpec lifecycle, and candidate-head proof provide the
promotion evidence. Failed ref resolution or head mismatch remains covered by
the existing lease contract.
