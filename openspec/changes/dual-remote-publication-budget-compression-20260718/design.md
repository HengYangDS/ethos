## Context

Equal GitLab/GitHub topology is a release-governance concern. Source-budget debt
measures whole-repository compression and does not establish the semantic
correctness of one topology Change.

## Decision

Use a compact `remotes = ["origin", "github"]` declaration and shared peer
projection. Retain the verbose `[[publication.remote]]` input for adopters that
already use it. The proof floor retains correctness, lifecycle, and no-push
admission gates; source-budget stays a separately invocable, repository-wide
compression report.

## Consequences

Malformed, duplicate, unnamed, candidate, work, and unknown remote targets
continue to fail. Local and provider observations remain separate. A source
budget breach remains visible through `ethos quality source-budget`, but does
not impersonate a topology correctness failure.
