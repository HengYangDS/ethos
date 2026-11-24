+++
title = "The decision-record rule reads prose hyphens, arrows and code spans as commands"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "In a decision record, name a command in words."
+++

The decision-record rule reads a spaced hyphen or an arrow in prose as a command option, and a code
span of two or more words as a possible invocation, and reports `docs_decision_execution_content`.
In a decision record, name a command in words.
