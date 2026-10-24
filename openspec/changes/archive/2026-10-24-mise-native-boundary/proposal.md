# Proposal

## Why

ETHOS resolves native tool supply by running mise in safe mode over a disposable copy of a repository's declarations, then hands the locked tools to admitted repository commands. Two defects share that boundary. mise records every configuration it loads, and every configuration it trusts, in its state directory. ETHOS isolates mise's global and system configuration but not its state, so each resolution and each disposable provisioning leaves a record of a path deleted a moment later. Proofs, gates and tests leave hundreds of these records a day. In addition, the environment handed to admitted commands still carries resolution's safe mode. A repository command that runs its own task through native mise is therefore refused ("running tasks is disabled in safe mode"), and Architecture Publisher's bootstrap fails this way.

## What Changes

- Resolution keeps safe mode and keeps mise's state in its disposable directory. Disposable provisioning keeps mise's state in its disposable root.
- The environment for admitted commands keeps the locked tools, configuration isolation, locked and offline selection, no automatic installation and no prompts. It carries neither resolution's safe mode nor its state. A caller's explicit safe mode and state directory still apply, and trust stays mise's own decision.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: native supply resolution leaves no host mise state, and locked execution keeps native mise policy.

## Impact

Code: `src/ethos/adapters/toolchain/mise.py`, `src/ethos/adapters/repo/runtime/materialization/native_supply.py` and their tests. The test session also keeps mise's state per test. No configuration, lock or command interface changes. Adopters receive the fix with the next public runtime. Records left by earlier runtimes are removed afterwards with mise's own `mise prune --configs`. Out of scope: mise itself, its trust model, and adopters' repositories.
