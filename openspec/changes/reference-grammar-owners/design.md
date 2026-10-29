# Design

## Context

The fleet survey with the `0.2.0-alpha.20` source leaves at least 20 false refusals in 5 roots, each
reproduced by a one-line input. They fall into three groups:

- incomplete POSIX nesting in `commands.py`: shlex opens no quoting context at `$(`, and `((…))`
  becomes a command segment;
- documentation metasyntax, such as `<name>` and `--mode a|b|c`, read as a `bash` fence;
- declarations that supply references and are ignored: Mise `[tools]`, a package tree outside the
  root and `src/`, and retained PowerShell steps.

Adopter proofs run no semantic closure. A committee of three reviewers cut the original draft to
the moves below. The product Python ceiling is 70,000 lines, and 69,971 are used.

## Goals / Non-Goals

**Goals:**

- No false refusal from the observed classes, and no new false refusal anywhere in the fleet.
- Every new owner is a declaration the adopter already authors.
- Product Python stays within its ceiling, funded by consolidation.

**Non-Goals:**

- Routing `-c` interpreter code, a PowerShell reader, and console-script command identities.
- Blocking adopter proofs on closure gaps.
- Declaring the adopters' true gaps.

## Decisions

- **A quote-aware substitution scanner.** Before a shell line is split, each `$(…)`, backtick
  command and `$((…))` is replaced by one word, and the commands it runs become separate lines.
  Arithmetic contributes only the substitutions nested inside it. The scanner honours single quotes
  as opaque and pairs double quotes within each nesting level. `shfmt --to-json` was declined:
  `shfmt-py` ships no `win_arm64` wheel, and prewrite must run on every platform the runtime ships
  to.
- **Executable identities contain a letter or digit**, and only a `$ ` prompt marker is stripped. So
  neither `+` nor `$PYTHON` becomes an executable.
- **Documentation metasyntax is rewritten before shell reading, in documentation carriers only.**
  - `<name>` becomes a placeholder variable word. As a value it is inert; in command position it is
    a variable command, which yields nothing.
  - A `|`-joined run of words after a long option becomes one value.
  - Scripts keep POSIX semantics.
- **Retention owns a step by location and digest.** The record already binds the file, the job and
  the step's SHA-256; matching no longer requires that the step read as an inline POSIX program.
- **A Mise tool owns its executable name**, from its `rename_exe` or the last segment of its tool
  identity. No install layout is read, so the verdict does not depend on the auditing host.
- **The package root owns first-party names.** A tracked module's nearest ancestor without
  `__init__.py` contributes its top-level name, which subsumes the root and `src/` cases. deptry's
  `[tool.deptry]` `known_first_party` is read beside the deptry policy.
- **The closure is a report beside the audit reports.** It runs in adopter proofs, lists every gap
  with its carrier and leaves the verdict unchanged. A later Change that names a release may make it
  blocking.

## Risks / Trade-offs

- [Correct nesting reveals hidden true references] → They are true. The CHANGELOG names the change,
  so adopters declare what their touched carriers run.
- [A tool name over-owns a phantom executable] → Nothing runs a phantom, and companion executables
  stay refused.
- [The package-root rule hides a third-party import of the same name] → The fleet survey gate
  requires that no true gap is lost.
- [The closure adds proof time] → It is measured on the largest adopter before landing.
