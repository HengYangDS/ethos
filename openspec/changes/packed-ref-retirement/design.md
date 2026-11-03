# Design

## Context

See [proposal.md](proposal.md). `_reference_transaction` in
`src/ethos/adapters/repo/hook/protocol.py` reads Git's prepared lines, skips refs outside
`refs/heads/` and `refs/tags/` and lines whose equal old and new values are not zero, and passes
every other line to `admit_reference`. The packed backend's transaction runs the hook in its own
process, so the zero-to-zero line cannot be matched with the main transaction's line.

## Goals / Non-Goals

**Goals:**

- A prepared retirement of a packed ref applies under the generated hooks.
- A deletion without an old value stays governed: of a protected branch it is still refused.

**Non-Goals:**

- Changing any ref policy, retirement intent or the absorbed-ref preview.
- Governing the preparing, committed or aborted states, which the protocol does not govern.

## Decisions

- **Resolve the zero old value from the ref.** In the prepared state the ref still holds its
  current value: the main transaction holds the ref's lock, and the packed transaction holds the
  `packed-refs` lock, without having replaced either. `ref_head` reads that value, and the line is
  admitted as the deletion of it. Both lines of a packed deletion therefore claim the same
  prepared intent, which accepts a repeated prepared claim of the same update.
- **Keep the zero value for an absent ref.** `ref_head` returns the zero value when the ref does
  not resolve, so such a line is still refused for its missing policy.
- **Resolve in the protocol.** The zero old value is how Git's hook input says "not given", and the
  protocol owns parsing that input; admission keeps receiving explicit values.

## Risks / Trade-offs

- [A raw deletion of an unprotected ref without an old value is now judged like the same deletion
  with its old value] → That is the existing rule for explicit deletions; protected branches and
  prepared intents still govern both.
