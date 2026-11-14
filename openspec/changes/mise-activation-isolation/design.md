# Design

## Context

See the [proposal](proposal.md). `run_command` in `src/ethos/adapters/process.py` builds a child's
environment from the caller's, drops every name that begins with one of `remove_env_prefixes`,
compared without case, and then adds the `env` that the caller supplies. The Mise adapter's
`locked_environment` returns that `env`: the locked tools' paths, a private global configuration,
`MISE_LOCKED`, `MISE_OFFLINE` and their siblings. Eleven call sites pass
`remove_env_prefixes=("MISE_",)`: three in the adapter, one in native supply materialization and
seven in the Python, Go and JavaScript gates. A shell that ran `mise activate` exports seven names
under `__MISE_`, which that prefix does not match.

## Goals / Non-Goals

Goals:

- A child that resolves or runs locked tools sees no mise state of the launching shell.
- The rule is written once, at the adapter that owns Mise.

Non-Goals:

- Any change to the locked environment that ETHOS supplies, to `PATH` composition or to trust.
- A general allow-list for a child's environment; other tools keep their own prefixes.
- A check of the launching shell. The fix removes the dependency instead of reporting it.

## Decisions

1. **One name at the adapter.** `MISE_ENVIRONMENT_PREFIXES = ("MISE_", "__MISE_")` in
   `src/ethos/adapters/toolchain/mise.py`, beside `_CALLER_INPUTS`. The gates already import from
   that module, so no new dependency direction appears.
2. **All eleven sites use it.** A site that keeps its own literal is the defect's shape, so none
   remains; `git grep` for the literal `("MISE_",)` under `src/ethos` returns nothing.
3. **The regression runs a real child.** The unit test sets `MISE_ENV`, `__MISE_DIFF` and one
   shell marker in the parent, starts a child with the adapter's declaration and one supplied
   `MISE_LOCKED`, and requires that the child lists exactly the supplied variable and an unrelated
   one. Two existing assertions of the call options name both prefixes.

## Risks / Trade-offs

- The reported failure itself was not reproduced under ETHOS's own tests: it needs an installed
  mise, two tools whose paths collide and an activation diff that lists them. The adoption
  session's bisect is the evidence, and the acceptance was observed on 2026-11-14 at 23:03: the
  same archived head of that repository, whose proof failed its JavaScript behavior gate at 20:27
  from an activated shell, passed 13 of 13 checks when launched with every `__MISE_` variable
  unset and the repository's test unchanged.
- A caller that sets a variable under `__MISE_` on purpose loses it in the child. mise documents
  none as an input.
- Mise could add activation state under another prefix. The rule then has one place to change.
