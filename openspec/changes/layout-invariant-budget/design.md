# Design

## Context

The source-budget gate sums `effective_code_lines_for_source` per category
(`src/ethos/domain/source_budget/measurement.py:166-168`) and compares the sums with
`[source_budget].terminal` (`:466-472`). That measure counts physical lines that hold a token, so a
formatter collapse that keeps the syntax tree lowers it. The same line measure also feeds the
native `scc` cross-check (`:384-462`) and the 500-line per-file ceiling that every governed
repository shares (`src/ethos/repository/paradigm/size.py`).

Measurements on 11-07 with the existing line measure and a prototype token count
(`build/runtime/work/size-measure/ratio.py`):

| Tree                         | Category |  Lines |  Tokens | Tokens per line |
| ---------------------------- | -------- | -----: | ------: | --------------: |
| `44c3bd5a1`                  | tests    | 94,867 | 691,974 |          7.2941 |
| `214133da5` (formatter only) | tests    | 94,692 | 691,974 |          7.3076 |
| `c3ca98963`                  | product  | 73,100 | 517,133 |          7.0743 |
| `c3ca98963`                  | tests    | 93,395 | 697,284 |          7.4660 |
| `c3ca98963`                  | tools    |  8,300 |  59,218 |          7.1347 |
| `e00d2d8f5` (formatter only) | product  | 70,868 | 517,135 |          7.2972 |

## Goals / Non-Goals

Goals:

- Enforce the Python ceilings on a measure that formatting cannot move.
- Keep the ceilings' numbers and the 5,000-step rule readable as line-equivalents.
- Leave adopters, the per-file ceiling and the cross-check unchanged.

Non-Goals:

- New measures for other languages; they stay observations.
- Enforcing a declared growth per Change; proposals state it, reviewers read it.
- Reducing the tests; the Git port that would retire patch-based tests is 0.3.0 work (resolution R2).

## Decisions

1. **Count layout-invariant code tokens.** Tokenize the source after masking standalone string
   expressions (the existing `_without_string_expressions`), then drop comments, `NL`, `NEWLINE`,
   `INDENT`, `DEDENT`, `ENDMARKER`, `ENCODING`, statement semicolons and a comma whose next token is
   a closing bracket. Alternatives: an AST node count is fully layout-invariant but is not what the
   committee approved, and node shapes differ across Python minor versions; tokens of `ast.unparse`
   are invariant too but depend on the interpreter's unparser. Residual: the formatter may add or drop
   a pair of grouping parentheses when it rewraps an assignment; across the 192 collapsed product
   modules that moved the count by 2 of 517,133 tokens.
2. **Ceilings in line-equivalents through declared ratios.** `[source_budget].tokens_per_line`
   declares one ratio per Python category. An enforced coordinate is `ceil(tokens / ratio)`. The
   ratios come from the trees before the formatter-only collapses, so the 2,002 formatter lines earn
   nothing: product at `c3ca98963` (7.0743), tests at `44c3bd5a1` (7.2941), tools at `c3ca98963`
   (7.1347). A ratio changes only through a Change with a decision record, like a ceiling.
   Alternative: ceilings in raw tokens, which loses the readable numbers and the 5,000-step rule.
3. **Two measures, each where it belongs.** Every Python file keeps its line count, which the `scc`
   cross-check and the per-file ceiling read; the token count is added beside it, and only the
   terminal comparison reads the line-equivalents. A category without a ratio is enforced on lines,
   so an adopter's policy needs no change.
4. **One test step and a tools ceiling.** The tests measure 697,284 tokens, 95,596 line-equivalents,
   above 95,000. The real reductions of this period were small: `test-budget-densify` removed 486
   tokens and `result-contract-budget` 123. The remaining space is RC-blocking acceptance from the
   committee's resolution, so DR-0019's necessity review takes the test ceiling to 100,000 and names
   the 0.3.0 Git port as the reduction that follows. Tools get 10,000, the first 5,000 boundary above
   their 8,300.

## Risks / Trade-offs

- A ratio fixed today ages as coding style shifts; DR-0019 names the revisit trigger.
- The report gains a token metric beside the line metric; readers that compare `metrics` with
  `enforced_metrics` must not expect equality for Python categories.
- The raised test ceiling gives about 4,400 line-equivalents of space; at this period's growth that
  lasts days, not weeks, unless the 0.3.0 reductions land.
