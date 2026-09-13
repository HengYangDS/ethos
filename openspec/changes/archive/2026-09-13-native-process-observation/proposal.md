## Why

The accepted runtime reclamation contract requires preserving active process
dependencies. GitLab's Linux verification of `3472cdad` found one violation:
the native process listing silently omitted a long dependency argument.
The same Linux `ps` loses that argument when `COLUMNS` is narrow even though
it exits successfully. Presentation width must not determine destructive facts.

## What Changes

- Request unbounded command width from the existing native process observer.
- Preserve native executable selection, process population, error propagation
  and the existing deadline; do not introduce another process parser.
- Exercise real long arguments under narrow display settings, then verify
  runtime retention while the process lives and reclamation after it exits.

## Capabilities

### Modified Capabilities

- `repository-governance`: enforce the existing live-consumer retention contract
  independently of terminal presentation.

## Impact

The unique observer in `src/ethos/adapters/process.py`, its direct tests, the
existing runtime retirement consumer tests and the canonical terminal plan.
No specification delta is required: this repairs a violation of the accepted
generation-reclamation requirement rather than changing its meaning.

## Non-Goals

No new process registry, fd/mmap analysis, platform framework, global environment
override, deadline increase, host-security change or adopter code change.
