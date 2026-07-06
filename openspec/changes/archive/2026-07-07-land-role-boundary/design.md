# Design

No new truth store or command is introduced. The existing mutation decision
reducer now evaluates role and dirty-state boundaries for dry-run land just as
apply land does, while keeping mutation-only requirements (`authorize`,
`expect-head`, executed proof) on the apply path.

This reveals a boundary error earlier without making read-only status depend on
proof side effects.
