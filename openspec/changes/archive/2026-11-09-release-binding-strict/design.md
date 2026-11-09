# Design

## Context

`strict_branch_role_policy_from_release_text` (`contracts/branch/roles.py`) is the only reader of
`[release]` and reads `mirror`. The version source is `VERSION`, read by the release readers, and
the tag rule is `[protected_refs] tags`, judged by the paradigm's release gaps. The workspace
binding's `_restated_field` repair already deletes one field on a line of its own and removes a
table left empty, keeping the result only when it parses as exactly the expected binding.

## Goals / Non-Goals

Goals: report and repair every `[release]` key that no reader consults.

Non-Goals: `[protected_refs]`, `[publication]` and `[host_profile]`, which their readers validate;
the version rule, which `version-identity-universal` owns.

## Decisions

1. **The reader names its keys once.** `contracts/branch/roles.py` declares
   `RELEASE_MIRROR_KEY = "mirror"` and `RELEASE_KEYS = frozenset({RELEASE_MIRROR_KEY})`, and its
   two reads of `[release]` use `RELEASE_MIRROR_KEY` instead of the literal; the paradigm report
   imports `RELEASE_KEYS`, so the reader and the check cannot disagree. The existing
   `RELEASE_MIRROR_FIELD` names the retired workspace field `release_mirror` and is unchanged.
2. **Each unread key is one gap, with or without release tags.** A `release_binding_gaps`
   generator beside `_release_gaps`, called from the report with no tag precondition, yields
   `release-binding` at `<carrier>:release.<key>` for every key of `[release]` outside
   `RELEASE_KEYS`, with the repair "remove <key>; no reader consults it". A `[release]` that is not
   a table is the branch role reader's own refusal.
3. **One line deletion, shared.** The body of `_restated_field` that deletes a field on a line of
   its own, removes a table left empty with the comments above it, and keeps the result only when it
   parses as exactly the expected binding becomes a helper. `_restated_field` keeps its guard and
   calls it; the `release-binding` handler calls it without a guard, since the gap shows the key is
   unread. Beside other keys, a multi-line value, a subtable or a dotted top-level key fails the
   parse check and stays reported; a table whose only key it is goes whole, as a workspace table
   does.

## Risks / Trade-offs

- A repository that kept these keys as notes loses them; the version and tag rules they described
  are already enforced from `VERSION` and `[protected_refs]`.
