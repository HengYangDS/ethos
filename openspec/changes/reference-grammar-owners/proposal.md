# Proposal

## Why

`0.2.0-alpha.20` still refuses governed repositories' patches for at least 20 references that no
executor runs or that a declaration supplies, in 5 roots of the fleet survey. Three causes account
for all of them:

- ETHOS's POSIX reading mis-pairs quotes inside `"$(…)"` and reads `$((…))` as a command.
- Documentation metasyntax (`<name>` placeholders, `--mode a|b|c` synopses) is read as executable
  shell.
- Mise `[tools]` and a repository's package tree supply executables and first-party modules that
  ETHOS ignores.

An adopter proof also never runs the semantic closure, so latent gaps surface one touched carrier at
a time.

## What Changes

- **POSIX nesting.** Single quotes are opaque. Inside double quotes, `$(…)`, backticks and `$((…))`
  nest with their own quoting. Arithmetic words are values, while a command substitution inside
  arithmetic is still read. An executable identity contains a letter or digit, and only a `$ `
  prompt marker is stripped.
- **Documentation metasyntax, in documentation carriers only.** `<name>` is a placeholder value, a
  placeholder in command position is never followed by a command, and `--flag a|b|c` is an
  alternation of values.
- **PowerShell steps through retention.** A retention entry matches a step by file, job and digest,
  whatever POSIX shape its text reads as.
- **A Mise tool owns its executable name.** It owns its `rename_exe`, otherwise the last segment of
  its identity, on every platform.
- **The package tree owns first-party names.** A tracked module's package root contributes its
  top-level name, and deptry's `[tool.deptry]` `known_first_party` is read.
- **Adopter closure at proof is reported** beside the audit reports, without changing the proof
  verdict.
- Consolidation in the reference observation funds the additions within the product ceiling.
- **CHANGELOG.** One entry under `[Unreleased]`, which names the newly visible references inside
  double-quoted substitutions.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`:
  - shell references follow POSIX nesting;
  - documentation metasyntax is not a command;
  - toolchain and package declarations own what they supply;
  - adopter proofs report the semantic closure.

## Impact

- **Product code.** `src/ethos/repository/policy/references/` and the audit's proof context change;
  product Python stays within 70,000 lines.
- **Governed repositories.**
  - The 20 observed false refusals disappear.
  - References inside double-quoted `$(…)` and backticks become visible, and the touched carriers
    must own them.
  - Adopter proofs list latent closure gaps without failing.
- **Follow-ups outside this Change:** console-script command identities; a PowerShell reader once a
  repository declares runner shells; blocking closure at proof, bound to a named release.
