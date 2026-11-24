+++
title = "One run of an installed release's interpreter without `-B` makes its hook installation fail"
state = "open"
since = "v0.2.0-beta.11"
fixed_in = ""
workaround = "Reinstall the release (for a Mise installation: `mise uninstall` and `mise install` of that version), or delete every `__pycache__` directory below the installation's `runtime` directory."
+++

A runtime image is inventoried file by file against its manifest, and an image that holds a
`__pycache__` directory or a `.pyc` file is a payload mismatch. The consoles run the image's
interpreter with `-B`, so they write none. An installation under a tool manager is not read-only,
though: any caller that runs the image's `python` without `-B` leaves bytecode files in it. From
then on `ethos hook install` and a formation that selects the runtime answer
`hook_install_failed:hook_runtime_payload_mismatch`; the next action is `ethos status`, and nothing
names the files or the repair. A repository that has already selected the release keeps working.
