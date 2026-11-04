# Design

## Context

The mise adapter, `src/ethos/adapters/toolchain/mise.py`, copies a repository's exact `config.toml`
and `mise.lock` into a disposable directory and runs native Mise there with `MISE_SAFE=1`,
`MISE_LOCKED=1` and `MISE_OFFLINE=1`.

- `locked_tool` returns what `mise which <name>` prints.
- `locked_environment` returns `mise env --json` with the directories from `mise bin-paths`.

Mise's `status.missing_tools` defaults to `if_other_versions_installed`, so a missing tool is
silent unless another version of it is installed.

The experiment of 2026-11-04 ran in an isolated store with the official Mise 2026.11.0 and the
host's 2026.10.25. It used openai-responses-proxy (nine tools, no npm tool) and aigw-cli (a locked
`npm:npm` 12.2.1 whose lock entry references an aube dependency graph). For each tool,
`ls --current --json` reports `version`, `requested_version`, `installed`, `active`,
`install_path` and `source`, the same fields in both releases. A lost aube identity shows up as
`installed=false`, with an `install_path` that no longer exists. Each query takes 0.04 to 0.12
seconds.

## Goals / Non-Goals

Goals:

- A locked tool or environment is used only when the whole declared supply is installed.
- An executable named by a declared tool comes from that tool.
- The refusal names the next action that can help.

Non-goals:

- Refusing a Mise release as such.
- Changing which Mise ETHOS's own CI selects: ETHOS's lock references no dependency graph.
- Carrying lock sidecars, linking global configuration or resolving without safe mode.
- Isolating `MISE_CONFIG_DIR`. The experiment raised it as unverified, and it is a separate gap.

## Decisions

1. **One completeness rule.** After resolution, both functions read `ls --current --json` over the
   same isolated inputs. Each version row must be `installed: true` with an `install_path` that is
   an existing directory. This rule covers both cases: a fresh store, where Mise stays silent, and
   the 2026.11 identity loss, where Mise reports a non-existent path.
2. **Containment per tool, not per supply.** A tool's own executable name is the last segment of
   its key, for example `npm` for `npm` and `syft` for `github:anchore/syft`. That executable must
   resolve inside one of the tool's install paths:
   - `locked_tool` checks its result;
   - `locked_environment` checks the first match on its PATH with `shutil.which`.

   Lying inside any tool's path is not enough: Node's bundled npm lies inside node's. A name that no
   declared tool owns is not constrained, so the proxy's undeclared npm still resolves to Node's.

3. **The next action follows the cause.**
   - If the selected Mise is 2026.11.0 or later and a missing tool's entry in `mise.lock` carries
     `aube`, the refusal names the safe-mode regression and an earlier Mise. The lock is the only
     source of that reference; `ls` does not expose it.
   - Otherwise, an untrusted root names `mise trust`, which the experiment shows selects the
     trust-keyed install under 2026.10.25.
   - Otherwise, the refusal names `mise install --locked`.
4. **No second query on success beyond `ls`.** The check derives everything from `ls` and from the
   `which` or `bin-paths` output that resolution already has. Mise's version is read only on the
   refusal path.

Alternatives:

- Setting `status.missing_tools = always` only adds a warning, and only for tools Mise considers
  missing, so it leaves the wrong-owner case.
- `mise which --plugin` costs one query per executable.

## Risks / Trade-offs

- Every `locked_tool` and `locked_environment` call runs one more Mise query, and with it the trust
  probe that every isolated run carries. A command that resolves several tools pays this once per
  call.
- An executable whose name matches a tool's key but that the tool does not provide could be refused
  wrongly if another tool supplies it. No such tool is known in the fleet. The refusal names the
  executable, so such a case is visible.
- The 2026.11 condition has no upper bound until upstream fixes jdx/mise#15363. The bound moves when
  a fixed release is verified.
