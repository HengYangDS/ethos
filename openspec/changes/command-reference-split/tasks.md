# Tasks

## 1. The pages

- [x] 1.1 Move `Native Merge Continuation`, `Retained Candidate Materialization` and
      `Accepted Release Selection` into `docs/reference/integration-and-release.md`, and
      `Native CI Projection` and `Exact Ref Observation For CI` into
      `docs/reference/ci-operations.md`, each page with front matter and an opening that states its
      reader question. Done when each moved section equals its text at the base byte for byte, the
      command reference reads 380 nonblank lines or fewer in the split's commit (373 at 51ba01846;
      the batch's other rows bring it to 393) and every page under `docs/reference/` reads under 500
      at the lane head.
- [x] 1.2 Keep each moved heading in the command reference with one pointer to the section's new
      anchor. Done when the five old anchors and the five pointer targets resolve.
- [x] 1.3 List both pages in `docs/reference/README.md`, and point the link of
      `docs/architecture/runner-and-mutation.md` to `native-merge-continuation` at its new page.
      Done when the Markdown link gate passes over the tree and no tracked link outside the
      archive names a moved anchor at its old place.

## 2. The carried set

- [x] 2.1 Add both pages to the wheel's `force-include` and the source archive's `only-include` in
      `pyproject.toml`. Done when
      `test_installed_navigation_preserves_required_links_without_source_checkout` passes; it
      fails without the two entries.

## 3. The bound

- [x] 3.1 Remove the `[paradigm.size]` table, its reason and its comment from `.ethos/rules.toml`.
      Done when the documentation registry reports `docs_length_exceeded` for a registered
      document of 501 nonblank lines, no gap for one of 500, and no gap on the tree.
- [x] 3.2 Correct the per-file limit that DR-0010 names to the paradigm's 500. Done when DR-0010
      names 500 and no tracked record outside the archive and the changelog states a per-file limit
      of 512: DR-0019's note on that sentence and the proposal of `specification-governance` recount
      the old figure and state none.

## 4. The release entry

- [x] 4.1 Name the five moved anchors and their new pages in one entry of the unreleased
      changelog. Done when the entry names each anchor and Prettier and Vale accept every changed
      document.

## 5. Lane and hosted acceptance

- [x] 5.1 Build the wheel and the source archive in the lane. Done when the wheel-resource tests
      of `tests/unit/release/test_version_identity.py` pass and the built wheel carries both pages
      byte for byte.
- [x] 5.2 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head and the hosted runs of that head pass. The pre-check (472 impacted test modules, 9,555
      passed, 5 skipped, no finding) and readiness (28 gates) passed at `4a5029e96` on 2026-11-17,
      and GitHub's push run 43991816712 and qualification 43991840423 passed there. At `25fec18ea`,
      which adds one comment of the pipeline model and task files to that head, GitHub's push run
      44014352341 passed, and so did GitLab's push pipeline 16172 and its qualification 16189 with
      the 34 gates.
