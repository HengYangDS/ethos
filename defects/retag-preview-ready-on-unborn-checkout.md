+++
title = "A tag re-creation previews as ready from a checkout with no commit"
state = "closed"
since = "v0.2.0-beta.12"
fixed_in = ""
workaround = "Run the re-creation from a checkout that has a commit."
+++

`ethos land --retag` asked from a checkout whose branch has no commit yet answers its preview with
`ready_to_retag` and a plan digest. The apply with that digest is then refused by the plan's
pre-state check (`git_effect_plan_prestate_stale`), and no tag moves. The preview and the apply
disagree, and the refusal names neither the cause nor a step.

Found on 2026-11-25 while testing the repair of tag re-creation from a checkout that is not at the
tag's commit. Before that repair the module that answers the preview,
`adapters/mutation/accepted/retag.py`, was unchanged since v0.2.0-beta.9; earlier releases were
not read, so the entry names the first release known to carry it. The repair refuses such a
checkout by name, `release_retag_checkout_unrelated`, at the preview as at the apply.
