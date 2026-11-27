+++
title = "Steps removed from an accepted specification are not reported in list form"
state = "open"
since = "v0.2.0-alpha.5"
fixed_in = ""
workaround = "Compare the scenario names of the accepted specifications before and after the edit."
+++

The shape report names `openspec_spec_obligation_removed` for a `WHEN`, `THEN` or `AND` step that an
uncommitted edit removes from an accepted specification, so that a scenario does not leave unnoticed.
It recognises a step only when the line begins with the bold keyword. A step written as a list item,
`- **WHEN** …`, is not recognised, and that is the form OpenSpec writes and every accepted
specification of this repository uses. An edit that removes whole scenarios therefore passes the
report with no gap.

Found on 2026-11-25 by feeding the report's own rule the difference of an edit that removes 26
scenarios: it named none.
