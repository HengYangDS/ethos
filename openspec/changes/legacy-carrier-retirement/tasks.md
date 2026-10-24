# Tasks

## 2. Evaluation

- 2.16 Withdrawn by DR-0016 (environment). Retire the docs registry's comment-wrapped metadata reader for documents under the docs root once no adopter tracks such a document; docs health tests cover plain front matter only.
- [x] 2.21 Extend the legacy role migration to a legacy release root and legacy topic prefixes before di-effect rebinds to the paradigm runtime: accepted closeout renames a declared legacy release branch such as `master` to `main` with its worktree, and publication retirement deletes a published legacy release ref and refs under a legacy proposal prefix such as `submit/`, each judged from the committed table; focused tests cover both.
- 2.19 Withdrawn by DR-0016 (environment). Retire the legacy role rename, its Git admission and the legacy role ref retirement after 2.21, once no adopter declares a legacy role name or publishes a legacy role ref.

## Workflow follow-up

- Moved verbatim from `repository-paradigm` on 2026-10-18. Task 2.16 waits on data-department-work-guidelines; task 2.19 waits on di-effect's own later migration.
- On 2026-10-24 [DR-0016](../../../docs/decisions/dr-0016-change-closure-scope.md) withdrew the tasks that this Change did not deliver from 0.2.0; their lines stay in this file without checkboxes.
