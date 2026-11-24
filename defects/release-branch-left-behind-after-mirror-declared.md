+++
title = "After the landing that declares the release mirror, the release branch stays behind and no result names the step"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Run the closeout once more at the landed head: `ethos land --closeout --expect-head <head> --candidate-head <head> --json`, then the same with `--apply --authorize`; it answers `accepted_current` and fast-forwards the release branch."
+++

A landing whose tree first declares `[release] mirror = "accepted_ff"` is closed out under the
policy of the accepted head before it, so the closeout advances the accepted branch and leaves the
release branch where it was. Afterwards `ethos status` at the accepted root answers `pass`,
`ready`, and names no step, although the release branch no longer equals the accepted branch as
the declaration requires. A second closeout at the same head moves it. Measured in a temporary
repository with the candidate of `ca4a7fb62` on 2026-11-23.
