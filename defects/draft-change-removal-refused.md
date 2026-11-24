+++
title = "No command removes a draft Change, and a prewrite refuses the removal of its files"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "none"
+++

No command that removes a draft Change was found. Measured on 2026-11-18: a prewrite refuses the
removal of a draft's files under its own selector, `openspec_requested_change_missing`, and under
another Change, `openspec_change_path_mismatch`.
