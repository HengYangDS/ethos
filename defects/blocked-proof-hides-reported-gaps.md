+++
title = "A blocked proof result hides reported gaps and names one repair for many gaps"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Read the paradigm report itself; `ethos lane repair-paradigm --json` previews it."
+++

Found 2026-11-22 from a governed repository's preview of `ethos prove --full` under
0.2.0-beta.11: verdict `block`, 67 required gaps of two kinds (66
`repository_paradigm_authored_name`, 1 `repository_paradigm_configuration_carrier`).

- The result's `data` is empty. The paradigm report's `reported_gaps` and `name_admissions` are
  not in it, so a reader cannot tell from the result whether an obligation that stopped blocking
  in this release is still reported.
- The result's one `next_action` is the repair of the configuration carrier. Sixty-six of the 67
  gaps are of another kind, and their repair is not named.
- The authored-name repair text names a rename or a `linguist-vendored` or `linguist-generated`
  mark. It does not name the profile's `identifier_sources`, which the same release ships for a
  name that an upstream data contract fixes.

The workaround's command is named from the source (`adapters/mutation/paradigm_repair.py` reads
the same report); it was not run on that repository.
