# Design

## Context

See [proposal.md](proposal.md). Design revision 5.1 (`build/runtime/work/architecture-realization/product-architecture.md`, "Adopter counterexamples") names the three defects, their owners and their acceptance. The receipts are machine-local:

- row 1: `alphasim-dmgr-fix-b3-work-refresh-external-parity-20260715/build/evidence/workflow/closeout/retention/runtime-binding-20261027/taplo-live-owner-sole-file-repro.json`;
- row 2: the same directory, `native-openspec-reference-retirement-consumers-prewrite-0846.json` and `gitlab-ci-local-477-pin-prewrite-native-0818.json`;
- row 3: `di-effect-worktrees/20261008-serena-activation-ownership/build/evidence/runtime-binding-20261027/pre-push-single-owner-prewrite-0831.json`, with its repair `pre-push-single-owner-repair-0831.patch`.

Constraints:

- **Budget.** `python_product` is 69,987 of 70,000 on `dev`, and `surface-pruning` has not landed. Each repair pays for its own lines inside its owner (agreed with the product lane on 2026-10-28).
- **Final shapes.** `verification-throughput`, `reference-observation-repair` and `change-selection` own the final form of each owner. This Change makes the smallest correct fix and leaves each regression for them.
- **Concurrency.** The product lane runs `surface-pruning` and `shared-quality-obligations`; neither edits these four owners.

## Goals / Non-Goals

**Goals:**

- Each receipt's refused operation is admitted under the same conditions, and the cases that should still refuse still refuse.

**Non-Goals:**

- Changes to alphasim or di-effect. Their owners retry after a release.
- Any allowlist, special case or second parser.

## Decisions

### 1. Carriers are selected among present paths

`quality_source_files` lists `--cached --others`, so it keeps an indexed path that the worktree deleted. The tool reads its configuration from the worktree, so `native_repository_configuration` now selects only among paths present there. A symlink still counts as present, so the existing refusal of a linked carrier still sees it.

Alternatives rejected:

- Changing `quality_source_files` for every caller. Authored source selection keeps deleted candidate paths for its own diagnostics (quality "Configuration selection preserves requested coverage").
- Staging the deletion in the adopter. That hides the case instead of fixing it.

### 2. Release commands own their executables

The release declaration reader reads the local publication command fields that the release model declares (`LOCAL_COMMAND_FIELDS`, made public in `repository/release/publication.py`) and parses them with the existing shell parser. Trusted-prior admission is unchanged: the reader reads the baseline declaration, so a candidate that adds both a command and its reference is still refused.

### 3. Validation repair beside another Change's drift

Template repair already says "Two drifted Changes do not hold each other's repair". The validation-repair context now applies the same rule: a template-drift gap of another active Change is permitted. Drift of the selected Change, and any other gap, still keeps the repair closed. The other Change's drift stays in the required gaps, so plan, proof and closeout still block until that Change is repaired.

The predicate lives in `template_repair.py`, beside the gap grammar it reads.

### Each repair pays for itself

- Row 1 folds the live-path filter into the existing carrier check, at the same line count.
- Row 2 replaces two copies of the command-declaration selector with one, which pays for reading the release commands.
- Row 3 extracts the complete-selected-Change check that the validation-repair and canonical-repair contexts both carried, which pays for the drift predicate several times over.

`python_product` falls by 11 effective lines.

### Spec delta

The repository-governance requirement "OpenSpec Lifecycle Contract Review" is restated with one added clause in its scenario "Official validation requires an active Change artifact repair".

## Risks / Trade-offs

- [A deduplicated check changes behavior] → Both repair contexts keep their existing regressions, and the shared check is a verbatim extraction.
- [Release commands over-admit] → Only executables in the trusted declaration are owned; the regression checks that an undeclared executable stays absent.
- [A drifted Change stays unrepaired] → Its drift remains a required gap of every reader, so it still blocks proof until its own repair.
