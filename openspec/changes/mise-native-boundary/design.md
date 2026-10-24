# Design

## Context

ETHOS runs mise in three roles. Resolution observes native supply: `run_mise` copies a repository's declarations into a disposable directory, and `repository_mise_files` discovers idiomatic version files there. Provisioning (`download_tool`) installs locked supply in a disposable root. Execution gives admitted repository commands the locked tools through `locked_environment`. `_mise_environment` owns the mise environment of all three, and it isolates global and system configuration and the configuration ceiling.

mise 2026.10.18 records every configuration it loads under its state directory, and it persists trust when a command that runs project code trusts its active configuration automatically (`run`, `exec`, `install`). Safe mode refuses tasks and skips untrusted code-running configuration. Outside CI, `env`, `bin-paths` and `config ls` refuse an untrusted configuration that needs trust; in CI mode mise skips the untrusted parts and persists nothing.

## Goals / Non-Goals

**Goals:**

- Resolution and disposable provisioning leave no record in the host's mise state.
- Admitted commands run under native mise policy with the locked tools, so a repository's own tasks run.
- A caller's explicit safe mode and state directory apply in execution.

**Non-Goals:**

- Changing mise, its trust model or its CI behaviour; trusting any configuration.
- Removing records left by earlier runtimes. `mise prune --configs` does that once the successor runtime is active.
- Changing adopters' repositories.

## Decisions

- **One owner, two roles.** `_mise_environment` gains an execution role instead of a second environment builder. Resolution adds `MISE_SAFE=1` and a `MISE_STATE_DIR` inside its disposable directory; execution adds neither.
- **Caller policy passes through as given.** `MISE_STATE_DIR` and `MISE_SAFE` join the caller's storage inputs. Resolution overrides both; execution keeps them. mise accepts several spellings of safe mode, such as `1`, `true` and `yes`, so execution passes the caller's value unchanged rather than only `1`.
- **Provisioning keeps state with its data.** `download_tool` already places data and cache in its disposable root; the state joins them.
- **Tests keep state per test.** Admitted commands may now auto-trust fixture configurations. A per-test `XDG_STATE_HOME` keeps those records with the test.
- **Rejected alternatives.** Pruning after each call would race with other processes and delete records ETHOS does not own. Trusting the repository, or setting `MISE_TRUSTED_CONFIG_PATHS`, would grant trust that is mise's or the user's decision. Keeping safe mode in execution and running tasks through an ETHOS executor would duplicate mise, and Architecture Publisher's accepted boundary excludes it. Forcing CI mode would change the behaviour of every child tool.

## Risks / Trade-offs

- [Execution leaves safe mode, so admitted commands may run their repository's mise tasks] → Only admitted commands run, with the locked tools and no installation. A caller can still select safe mode, and untrusted code-running configuration still never runs.
- [An admitted `mise run` trusts its repository's configuration in the caller's state] → This is mise's documented behaviour for commands that run project code. The record names a real repository path, not a deleted one.
- [Records from earlier runtimes remain until pruned] → They are removed with `mise prune --configs` after the successor runtime is active, not before, because earlier runtimes keep adding them.
