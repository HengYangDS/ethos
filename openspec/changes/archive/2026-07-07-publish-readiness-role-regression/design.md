# Design

`evaluate_mutation` serves multiple transition surfaces. Dry-run land is special
because it asks whether a Work Lane can move to candidate, so it must inspect
role boundaries before saying ready. Publish dry-run asks whether the current
accepted repository is locally publishable, so protected-root status is not a
mutation violation until `--apply` is requested.

The reducer therefore preserves the old dry-run behavior for non-land commands
and keeps the new role-aware readiness for land.
