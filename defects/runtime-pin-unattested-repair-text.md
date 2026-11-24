+++
title = "The `runtime_pin_unattested` repair asks for an attestation of a checksum-bound release"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "For a release that a checksum alone binds, read \"checksum\" in the repair text: `mise lock` records it."
+++

The repair text of `runtime_pin_unattested` asks for an attestation also where a release is bound by
a checksum alone. For such a release read "checksum": `mise lock` records it.
