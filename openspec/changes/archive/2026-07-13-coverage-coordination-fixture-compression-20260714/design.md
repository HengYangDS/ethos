## Design

The repeated export calls have one invariant command envelope: lane identity,
source holder, target holder, leased generation, expected source head, apply
mode, root binding, JSON projection, and working directory. A bounded typed
helper owns that envelope and selects only four case-local facts:

| Fact | Case-local values |
| --- | --- |
| Context source | text or file |
| Dirty disposition | omitted, committed, or preserved |
| Expected result | passing or blocked command envelope |
| Output root | test-local handoff directory |

No generic CLI DSL or production abstraction is introduced. The wave is
accepted only if formatter-clean effective Python source declines, focused
handoff behavior remains equivalent, and global source-budget admission remains
clean.

## Risks and rollback

A helper could accidentally erase a command-specific option. Focused tests keep
all distinct calls and assertions. Revert this one test-file change if parity
fails.
