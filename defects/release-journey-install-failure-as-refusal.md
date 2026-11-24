+++
title = "The release journey counts any failed install of a rebound lock as a refusal by Mise"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "The journey's receipt records each refusal's text under `refusals`."
+++

The release journey counts any failed install of a rebound lock as Mise's refusal. It does not yet
require the refusal to name its cause, so a failed download would read as a refusal. The journey's
receipt records each refusal's text under `refusals`.
