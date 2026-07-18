## Context

The current equal GitLab/GitHub topology adds behavior after most shared budget
slack was consumed. The preserved behavior must fit the existing hard floor.

## Decision

Use a compact `remotes = ["origin", "github"]` declaration, shared peer
projection, and small reducers. Retain the verbose `[[publication.remote]]`
input for adopters that already use it. Do not relax admission, lifecycle, or
no-push evidence boundaries.

## Consequences

Malformed, duplicate, unnamed, candidate, work, and unknown remote targets
continue to fail. Local and provider observations remain separate.
