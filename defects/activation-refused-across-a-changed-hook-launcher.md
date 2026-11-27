+++
title = "A rollback across a release that changed the hook launcher is refused"
state = "open"
since = "v0.2.0-alpha.19"
fixed_in = ""
workaround = "none is needed today: the launcher has not changed since v0.2.0-alpha.19."
+++

`ethos hook install` writes the hook launchers that the running build declares and then judges them
against the declaration of the runtime it selects. When the two builds declare different launchers,
the activation ends with `hook_runtime_activation_invalid`, names a `launcher_drift` gap for each
hook and `hook_generation_digest`, and puts the earlier selection back. The one supported rollback,
the current runtime activating the held one, is such an activation, so a release that changes the
launcher cannot be rolled back from.

No release since v0.2.0-alpha.19 changed the launcher, so no rollback has met this.

Found on 2026-11-25 by running an activation whose running build differed from the selected
runtime in one alternative of the launcher's path pattern.
