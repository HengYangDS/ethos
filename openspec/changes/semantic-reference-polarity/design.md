## Context

See [proposal.md](proposal.md). The semantic-closure checker already parses
ordinary Markdown links, but canonical OpenSpec Markdown is handled as raw path
literals. That asymmetry turns the accepted requirement ``docs/index.md SHALL
be absent`` into a false live consumer immediately after archive.

## Goals / Non-Goals

**Goals:**

- Make consumption depend on a typed use relation rather than the presence of a
  path-shaped token.
- Keep canonical and Change OpenSpec text inside the same Markdown syntax
  boundary as other documentation.
- Continue detecting real navigable and executable consumers.

**Non-Goals:**

- No keyword list for negative prose.
- No exception for `docs/index.md` or for one Change.
- No new registry, schema, compatibility path, or persistent state.

## Decisions

### Markdown path consumption is navigability-bound

For every Markdown carrier, including canonical OpenSpec specifications, only
link destinations establish a path-consumer relation. Inline code and prose may
state required presence, required absence, examples, migrations, or history;
their lexical polarity is not a reliable or necessary ownership signal.

This uses the existing Markdown parser and deletes the OpenSpec-specific raw
literal branch. It is preferable to a positive/negative keyword classifier,
which would be language-dependent, incomplete, and another semantic mechanism.

### Executable syntax remains strict

Python imports and the existing typed command, executable, declaration, and
configuration observations remain unchanged. This correction does not weaken
actual runtime-consumer detection.

## Risks / Trade-offs

- **Risk:** an unlinked prose path that was intended as an operational pointer
  is no longer treated as a consumer. **Mitigation:** operational pointers must
  be links, declarations, commands, imports, or configuration so that their use
  is machine-observable rather than inferred from prose.
- **Risk:** a link may appear inside a negative explanation. **Mitigation:** a
  navigable link is still a real dependency and therefore remains blocked until
  removed.

## Migration Plan

1. Add failing canonical-spec regressions for negative prose and navigable
   links.
2. Remove the canonical-OpenSpec raw-literal special case.
3. Run focused semantic-closure tests and exact-HEAD full proof.
4. Archive and reprove this successor before candidate and accepted CAS.
