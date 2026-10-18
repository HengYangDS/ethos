# Proposal

## Why

ETHOS accepts native quality evidence only in shapes that Nox, pytest, coverage.py and Ruff
produce: a gate that declares native outputs needs one Nox report and, per session, a Python
runtime report with pytest or Ruff output. A repository whose tests or analyzers are not Python
cannot supply evidence, so Ordo excludes its 26 shell scripts from quality, and a script's behavior
always reports `native_language_unsupported:script`. Issue #1 asks for one evidence boundary in the
existing owners: a repository's own tools and configuration produce the evidence, and ETHOS judges
it by property.

## What Changes

- **BREAKING** Declared native outputs use tool-neutral formats: `junit-xml`, `cobertura-xml`
  (renamed from `coverage-xml`), `lcov` and `sarif`. `ruff-json` is removed, so static analysis
  evidence is SARIF only. A profile that still names a removed format is invalid.
- A Nox report, pytest events and a Python runtime report are optional and are checked only when
  declared. A gate no longer needs a Nox report or a fixed set of outputs per session.
- Behavior evidence passes when every JUnit report passes with at least one test case and every
  applicable file that a coverage report measures was executed. Static evidence passes when SARIF
  reports no warning or error and its scan inventory lists the files it covers. SARIF without an
  inventory leaves its scope unknown and blocks.
- A verifier claims only the files its evidence covers. ETHOS runs its own checks only for a gate
  that declares no native outputs, and leaves a language it cannot check to another contributor.
  The quality obligation still requires every applicable file.

Out of scope: discovering code in languages beyond the current subject classification, changing the
quality floor, and migrating adopter profiles, which their own owners do.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: declared native outputs use tool-neutral formats with optional Python producer
  reports, and native evidence is judged by property and claims only the files it covers.

## Impact

The gate contract and its published schema, the native attempt and its verifiers (`code_quality`
for every language, `python_quality` for Python), the report parsers and the profile contract
documentation. openai-responses-proxy is the only adopter that declares native outputs; it renames
`coverage-xml` and replaces `ruff-json` with SARIF when it adopts a runtime with this Change. Ordo
replaces `excluded_script_paths` with kcov evidence through its own lane. Routing remains the
`quality` owner.
