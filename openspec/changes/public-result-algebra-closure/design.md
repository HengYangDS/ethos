## Context

`EthosResult` is the public typed owner. Internal decisions may keep rationale
in `why`. `lane status` wrongly reads a facts-only mapping as another verdict.

## Decision

- `unknown` requires a named missing fact or evidence gap.
- `block` requires a named gap or adverse diagnostic.
- `pass` remains incompatible with either.
- `lane status` reduces workspace validation plus explicit gaps only.

## Deletion

Delete the facts-only verdict input and reasonless public fixtures. Add no
fallback gap, inferred error, or parallel result helper.
