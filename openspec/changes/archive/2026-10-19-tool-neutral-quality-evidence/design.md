## Context

See [proposal.md](proposal.md). The gate contract accepts six native formats, five of them produced
by Python tools, and requires one Nox report plus, per session, a Python runtime report with
pytest, JUnit and coverage.py output or with Ruff JSON. The verifiers then read those shapes only.
`code_quality` runs ETHOS's own checks per language and blocks every gate on a language without one,
so a script's behavior cannot be evidenced at all.

Facts the design depends on, observed on 2026-10-18:

| Producer          | Standard output                         | What it lacks                                              |
| ----------------- | --------------------------------------- | ---------------------------------------------------------- |
| Ruff 0.17.0       | SARIF 2.1.0 with results                | `artifacts`, so no list of the files it read               |
| ShellCheck 0.11.0 | checkstyle, diff, gcc, JSON, quiet, tty | SARIF                                                      |
| kcov (master)     | Cobertura with per-line hits            | `branches-valid`; `branches-covered` is the constant `1.0` |

## Goals / Non-Goals

**Goals:**

- Judge behavior and static evidence from any language through JUnit, Cobertura, LCOV and SARIF.
- Keep every existing falsifier of the Python producer reports when they are declared.
- Let several gates jointly cover one axis, with the existing obligation compiler as the only
  completeness authority.

**Non-Goals:**

- Classifying code in new languages, changing ETHOS's own checks or the quality floor.
- Translating ShellCheck or Ruff output into SARIF inside ETHOS.

## Decisions

### Formats are standards; Python producer reports are optional custody

`NativeOutput.format` lists `junit-xml`, `cobertura-xml`, `lcov` and `sarif`, plus `nox-json`,
`pytest-jsonl` and `python-runtime-json`. The gate validator keeps unique paths and producers, no
nested paths and, for a declared Nox report, its `--report` argument and session coverage. It no
longer requires a Nox report or a per-session bundle. The removed names fail validation rather than
being aliased, so one vocabulary stays authoritative.

### One judge, scoped by its caller

`native/evidence.py` owns judgment of a retained attempt: custody (identity, outputs, exact source
and head, exit status), declared Nox sessions, declared Python runtimes, and then the axis.
`code_quality` passes every language; `python_quality` passes Python only. The Python producer
models stay in `native/python.py`. Report parsing stays in the repository policy layer, with
Cobertura in `quality_reports.py` and LCOV and SARIF in `quality/lcov.py` and `quality/sarif.py`.

### Behavior: tests pass and measured files ran

Every JUnit report needs a test case and no failure or error, and the tests must not all be
skipped. A declared pytest event report still pairs with its session's JUnit. Each coverage output
shares its session with a JUnit output, so execution comes from a tested session. Coverage files
must resolve to tracked files in the repository. An applicable file is claimed when some coverage
output shows one of its lines executed or measures no executable line; a measured file whose lines
never ran blocks. Cobertura root line counts are required; branch counts are read only when
`branches-valid` is present, which accepts kcov without guessing its constant.

### Static: SARIF results and a scan inventory

A result is adverse when its kind is `fail` and its level, defaulting to the rule's configured
level and then to `warning`, is `warning` or `error`. A failed invocation or an error or warning
notification also blocks. The inventory is the run's `artifacts` whose `roles` are absent or
include `analysisTarget`, and, for a session that also declares a Python runtime report, the files
its recorded Ruff launch read. Without either, scope is unknown and the gate blocks. Generated and
upstream files in scope are claimed as artifacts, as ETHOS's own check claims them.

Alternatives rejected: result locations as scope (a clean file has none) and command arguments as
scope (configuration can exclude files).

### Claims, not completeness, per provider

A provider reports the applicable files its evidence covers and lists the rest as unclaimed. The
obligation compiler already unions every contributing gate of an axis and requires that union to
equal the applicable files, so completeness keeps one owner. A provider that covers no applicable
file blocks. ETHOS runs its own checks only for a gate with no native outputs, and only for
languages it supports.

## Risks / Trade-offs

- Ruff SARIF alone cannot prove scope. A Python repository either declares the Python runtime
  report that records its Ruff launch or uses ETHOS's own static check.
- ShellCheck cannot produce SARIF, so scripts keep ETHOS's own ShellCheck for static analysis.
- Union coverage across sessions accepts a file that runs in one Python version only; per-session
  completeness was stricter, but behavior is a property of the subject, not of every session.

## Migration Plan

ETHOS ships the new vocabulary without aliases. An adopter's pinned runtime keeps its old contract
until the adopter moves its pin; at that point openai-responses-proxy renames `coverage-xml` to
`cobertura-xml` and writes Ruff SARIF in place of JSON in the same profile change. Ordo adds a
kcov-measured gate that contributes script behavior and removes `excluded_script_paths`. Both
migrate through their own lanes and acceptance.
