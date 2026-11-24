+++
title = "The paradigm report proposes a `VERSION` text that is refused when it is no SemVer"
state = "open"
since = "v0.2.0-beta.10"
fixed_in = ""
workaround = "Write the SemVer spelling of the version in `VERSION`."
+++

The paradigm report's repair for a missing version source proposes the manifest's version as
written. Where that spelling is no SemVer, `VERSION` with that text is refused as
`product_version_invalid`. Write the SemVer spelling.
