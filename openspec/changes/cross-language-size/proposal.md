# Proposal

## Why

The repository paradigm bounds two kinds of tracked file: Python files at 500 effective lines and
current authored Markdown documents at 500 nonblank lines. Every other language is unbounded. A
read-only preview over the governed repositories at their `dev` heads on 2026-10-31 found 23
authored code files in other languages above 500 effective lines, from 501 to 6413, in six
repositories. Two repositories rebuilt the check for their own language, each pinned at 512:
aigw-cli counts Go with scc in `tools/ci/size.go`, and architecture-publisher binds ESLint
`max-lines`. A third language, Rust, appears in architecture-publisher with no bound at all.

The owner's direction of 2026-10-31 is that the 500 ceiling applies to ETHOS and every governed
repository, that commonality sinks into the base, and that the answer holds for Rust and every other
language. A ceiling keyed by language cannot do that: each new language would need a new key, a new
counter and a new exception list. The per-file-ceiling-parameters design recorded the instrument
evidence this Change starts from: an in-process Pygments lexer agrees with scc on all 721 Go files
of aigw-cli and differs by at most 3 lines on 5 of 107 JavaScript and TypeScript files, none
flipping a verdict.

Two more lists repeat language facts. The names obligation keeps the module suffixes `.go`, `.py`
and `.pyi` in its own table, so a Rust module file, whose name Cargo derives from the module path,
is judged as a kebab-case name. The scripts obligation keeps the shell, PowerShell and batch
suffixes in another.

## What Changes

- One definition of an effective line for every language: a physical line that holds a token that is
  not whitespace, a comment or documentation. Preprocessor directives, attributes and shebangs are
  code. Python keeps its syntax-tree measure; every other language uses the Pygments lexer that the
  paradigm contract names for it.
- The paradigm contract gains one language registry. It names each code language's suffixes, its
  measure, whether its toolchain fixes module file names and whether its files are scripts. The
  size, names and scripts obligations read it; their separate suffix lists are removed.
- The two ceilings are keyed by class, not language: `code_effective_lines` for every registered
  code file, tests and tools included, and `document_nonblank_lines` for current authored documents.
  Both keep the default 500 and the bound 1000, and the same repository-value law.
- The 0.2.0-alpha.22 keys `python_effective_lines` and `markdown_nonblank_lines` are retired: a
  declaration of either is reported with the rename, and the default stays in force.
- Files that Git attributes mark vendored or generated leave the code measurement, as they already
  keep their names.
- The `python-size` obligation becomes `code-size`, reported as
  `repository_paradigm_code_size:<path>`.
- Pygments becomes a declared runtime dependency; it is already in the runtime closure.
- **BREAKING** for governed repositories: after they rebind, the 23 code files of the preview in the
  design exceed the default.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the Python size ceiling becomes a code ceiling over every registered
  language, and module names follow the registry.
- `quality`: the Markdown ceiling takes the class key.

## Impact

- `src/ethos/contracts/paradigm/paradigm.toml` and `declaration.py`: the registry, the class keys
  and the removed module-suffix list.
- `src/ethos/measure.py`: the lexer measure beside the Python measure.
- `src/ethos/repository/paradigm/size.py`, `report.py`, `names.py` and `scripts.py`, and
  `src/ethos/repository/registry/docs/health.py`.
- `pyproject.toml` and `uv.lock`: Pygments as a direct dependency. The lock is an input of the
  GitLab supply image, so the image is rebuilt and bound after this Change lands.
- Out of scope: retiring aigw-cli's `size.go` and architecture-publisher's `max-lines` binding,
  which each repository does in its own Change after it rebinds.
