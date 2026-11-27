# Design

## Context

See the [proposal](proposal.md). The paradigm fixed Python 3.12 in two places: the Python module
row's `floor = "3.12"` and the Ruff row's fixed setting `target-version = "py312"`. Render and check
load the shipped Ruff carrier and the repository's carrier, run Ruff once for each and refuse with
`native_formatter_policy_conflict` when the outputs differ. The pre-commit hook formats each staged
file with one policy, the repository's carrier when it has one, and the static gate already judges
at the declared target. This release may only admit: nothing that passes on its predecessor is
refused (DR-0029, DR-0035).

## Goals / Non-Goals

**Goals:**

- Any single `>=` clause of `requires-python` that names a version conforms, in place of the text
  `3.12`.
- A repository's Ruff carrier declares its own `target-version`, with any value.
- Where the shipped and the repository's settings render a file differently only because of the
  target, the file renders at the repository's target and passes.

**Non-Goals:** each of these would change a verdict, so each reports for one release first, after
0.2.0.

- One reader of `requires-python` for every runner.
- Refusing Python with no declared target.
- Refusing a carrier target that differs from the `requires-python` lower bound.
- Any change to the hook or the static gate.

## Decisions

1. **The module row names a key, not a version.** `floor = "3.12"` becomes
   `version_key = "project.requires-python"`. The report raises `module-floor` unless that key holds
   exactly one `>=` clause that parses as a version specifier (`packaging`'s `Specifier`), and its
   repair text names the key. `>=abc` and two `>=` clauses stay gaps; a lower bound below 3.12 is
   admitted.
2. **The Ruff row declares the target as a key that the carrier sets.** `FormatterBinding` gains
   `declared`: keys the carrier must set to any value, each with the value that the repair writes
   when it is missing. The Ruff row keeps `settings = { line-length = 100 }` and declares
   `target-version = "py312"`. A missing target keeps today's gap and repair; any declared value of
   the default's kind, a string, passes, and a value of another kind counts as no declaration.
3. **Only render changes, and only after today's refusal.** When the two configurations disagree,
   render reads the repository carrier's target and, when there is one, runs both again with that
   `--target-version`; it returns the output when they now agree and raises today's refusal
   otherwise. A render that passes today never enters this branch, so its bytes are unchanged. The
   check, which marks files clean in bulk, is unchanged.
4. **One reader of the carrier's target.** `python_target.carrier_target(root, paths)` starts at the
   paradigm carrier `.config/checks/ruff/ruff.toml` when it is listed, follows `extend` with the
   existing chain reader over a working-tree view, and returns nothing when the chain cannot be
   read. It runs only on a conflict, after the carrier's place has already been admitted.
5. **The hook and the static gate do not change.** The hook already formats with the repository's
   carrier, and its comment now says so. The shipped carrier keeps `py312`, ETHOS's own bound.
6. **The route to 3.14 for a repository.** One commit sets `requires-python = ">=3.14"` and the
   carrier's `target-version = "py314"` and is formatted under its parent's carrier; the next commit
   reformats. A carrier target above the `requires-python` lower bound is refused by the static
   gate, as today.

## Risks / Trade-offs

- Two readers of `requires-python` remain, the module report's one-clause parse and the static
  gate's, and they differ on texts such as `>=3.12,!=3.12.*` or `~=3.12`. One reader is a later
  change that reports first.
- A repository without a carrier is formatted at the shipped `py312` while the static gate lints at
  its lower bound.
- Render's retry costs two more Ruff runs, and only on a conflict that is refused today.
