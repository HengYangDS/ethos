# Design

## Context

The per-file ceilings live in the paradigm contract's `[size]` table
(`src/ethos/contracts/paradigm/paradigm.toml`): `python_effective_lines = 512` and
`markdown_nonblank_lines = 512`. The paradigm report measures every tracked Python file
(`repository/paradigm/report.py`, `python_size_gaps`), docs health measures every current authored
Markdown document (`repository/registry/docs/health.py`, `current_document_length_gaps`), and a
`[quality.code_size]` table in `.ethos/rules.toml` is reported as a restatement. The repository
paradigm requirement says that no repository binding may restate, raise or lower either ceiling.

Commit `472113158` (2026-10-15) moved the Python value from ETHOS's own `.ethos/rules.toml` into the
contract because only di-effect had declared one; the archived repository-paradigm design records
that adopters therefore had none. The retired table also held role capacities
(`test_effective_max_lines`, `surface_effective_max_lines`, `surface_path_globs`), and its comment
ruled them out: "role classification never grants capacity", and exceedance needs semantic
consolidation, "not role reassignment, cosmetic compression, per-file exemptions or raising the
limit to fit existing files".

Two governed repositories later rebuilt the check for their own languages, each pinned at 512:
aigw-cli counts Go code lines with scc (`tools/ci/size.go`, `.config/checks/scc/policy.toml`), and
architecture-publisher binds ESLint `max-lines` to `.config/checks/file-budget/policy.toml`.

On 2026-10-31 the owner set both ceilings to 500 for ETHOS and every governed repository, and asked
that a governed repository may use its own value, with 500 as the default. DR-0012 keeps its rule
that a repository cannot declare an exception.

## Goals / Non-Goals

**Goals:**

- Both ceilings default to 500 in every governed repository that declares nothing.
- A repository may choose its own value for its whole tree, within a bound the contract guarantees.
- A value equal to the default never pins a repository to it: a later default reaches the
  repository.
- One owner resolves the effective ceilings, so the paradigm report and docs health agree.
- ETHOS's own tree meets the new default.

**Non-Goals:**

- Measuring Go, JavaScript, TypeScript or other languages. That is a sink of a business-free
  check into the base and needs its own fleet preview; the shared-ownership design owns it.
- Changing either measure.
- A value for one file, a path or a class of files.

## Decisions

### 1. One law for the ceiling values

| A repository's `[paradigm.size]` value | Effective ceiling | Report |
| --- | --- | --- |
| absent | the default | nothing |
| equal to the default | the default | restatement |
| lower than the default | the declared value | nothing |
| higher, within the bound, with a reason | the declared value | deviation from the default |
| higher without a reason, above the bound, not a positive integer, or an unknown key | the default | gap |

An invalid declaration falls back to the default, because the default is what the contract
guarantees; a malformed or out-of-range value never widens the ceiling. The reason is prose, so it
is not decided. What is decided is the bound and the restatement; the report shows the reason
beside the deviation for review.

### 2. The carrier is the binding's `[paradigm.size]`

The value is a parameter of a paradigm obligation, and `.ethos` is the paradigm's binding root
(`[binding]` in the contract). `.ethos/rules.toml` already holds the repository's rules relative to
ETHOS, so it takes `[paradigm.size]` with the contract's key names and `[paradigm.size.reasons]`
with one string per looser key. The table name mirrors the contract's own `[size]` table under
`paradigm`, so a reader finds each key by the same name in both places.

- Rejected: `.config/checks/<owner>/policy.toml`, the shape architecture-publisher used. Those
  carriers hold a consuming tool's policy; the ceiling is the paradigm's own obligation and has no
  tool.
- Rejected: `.ethos/profile.toml`. It declares what the repository is, not the values of rules.
- Rejected: keeping the retired `[quality.code_size]` name. Its shape held role capacities; a new
  name avoids reading an old declaration as a valid one. The old table stays reported, with the
  repair to declare `[paradigm.size]`.

### 3. The bound is 1000

The bound is the contract's guarantee to every reader of a governed repository: no measured file
exceeds it, whatever the repository declares. It is twice the default and equal to Pylint's default
`max-module-lines`. Only an ETHOS Change moves it, with a fleet preview. One bound serves both
ceilings because both count lines a reader must take in.

### 4. No value narrower than the repository

A value applies to every file its ceiling measures. Generated, vendored and immutable content leaves
the measurement by selection (the contract's immutable roots, declared generated output), never by a
larger ceiling. This keeps DR-0012: a repository-wide value within the contract's bound is a
parameter of the obligation and exempts no file.

### 5. The measures stay, and the later sink inherits a measured instrument choice

Python keeps its exact measure: tokenize over a copy whose standalone string expressions the AST
masked (`ethos/measure.py`). A line-oriented counter cannot always tell a docstring from a string
value. Read-only comparisons on 2026-10-31 (`build/runtime/work/per-file-ceiling/`):

- scc 4.1.0 against the AST measure: 829 of ETHOS's 850 Python files agree, and 21 differ by up to
  66 lines. In ddwg-film, `src/filmkit/narration/thought_groups.py` reads 461 by the AST and 514 by
  scc. A raw-string regular expression on its line 70 desynchronizes scc's quote state, so every
  later docstring counts as code, and the verdict at 500 flips.
- A Pygments 2.21.0 lexer, already in ETHOS's runtime closure through cyclopts and rich, against the
  AST measure: 822 of 850 agree. Against scc on other languages: all 721 Go files of aigw-cli agree,
  and of 107 JavaScript and TypeScript files in five repositories, 102 agree and 5 differ by at
  most 3 lines, none flipping a verdict.

So the sink measures Python with the AST and other languages with an in-process lexer, keeping the
paradigm report a pure function of tracked bytes; scc stays the cross-check it already is for the
source budget. That decision belongs to the sink; this Change records the evidence.

### 6. ETHOS meets the default in this Change

When this Change lands, the incumbent package judges ETHOS's tree with 512. The release that
carries it judges the next proof with 500, and ETHOS is one member of every fleet preview, so ETHOS
brings its 13 Python files above 500 within the default here: seven in `src/`, four in `tests/`
and two in `tools/`. Twelve are split by semantic ownership. `adapters/repo/git.py` instead loses
`exact_rename_target`, which nothing called, in `retire-unreachable-product-code`; that Change also
pays for the imports the splits add to the product source budget. None shortens a file by
compressing it.

### 7. Values follow the running package

A governed repository meets 500 when it rebinds to the release that carries this Change. Until then
its installed ETHOS judges it with 512.

## Risks / Trade-offs

- **Fleet impact.** ETHOS's own checks at 500 over the 12 active repositories
  (`build/runtime/work/per-file-ceiling/exact-preview-500.json`):

  | Repository | Python files | Markdown documents |
  | --- | --- | --- |
  | ethos | 13 | 0 |
  | openai-responses-proxy | 4 | 2 |
  | aigw-cli | 0 | 2 |
  | architecture-publisher | 0 | 2 |
  | ddwg-introduction-film | 0 | 4 |

  All 27 files are between 501 and 512; 8 are exactly 512. The other seven repositories have none.
  ddwg-introduction-film's four are evidence reviews, one of them a captured preimage; whether
  they are current authored documents is that repository's classification. di-effect and alphasim
  stay deferred.
- **Files sit at the ceiling.** Eight files at exactly 512 show that a ceiling becomes a target.
  Lowering it by 12 lines invites trimming. The effective-line measure ignores comments, docstrings
  and blank lines, and the formatter owns layout, so only removing or moving code shortens a Python
  file; the requirement keeps semantic consolidation as the repair.
- **Product budget.** Splitting adds import lines. They are paid by real reductions in the same
  lane, not by raising a budget.
- **A reason is prose.** Review judges it. The bound and the restatement check are what the
  paradigm decides.
- **A repository that wrote 512 to keep its files.** That is the fit-existing-files case the retired
  table ruled out; it needs a purpose to stand, and the report shows it as a deviation.
