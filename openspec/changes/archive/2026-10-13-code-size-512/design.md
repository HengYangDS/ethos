## Context

The size policy is compiled by `CodeSizePolicy` in the rules configuration owner. Its `_LineLimit` type admitted only positive multiples of one hundred, so the user's 512 ceiling could not be declared.

## Decisions

1. Port the exact hunks of 693c15f23 that concern the ceiling: the declared value, the limit type and the size-gate tests. Leave its other contents to their own owners.
2. Keep every other strictness rule. Limits remain strict integers with no coercion, unknown fields or per-file exemptions, and malformed declarations still block.
