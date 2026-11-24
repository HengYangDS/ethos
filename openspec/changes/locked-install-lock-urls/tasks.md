# Tasks

## 1. The install's mode

- [ ] 1.1 State the rule once and apply it in `install_locked` and in `download_tool`. Done when
      unit tests, driven by native Mise's answer to the trust query, show for both installs no safe
      mode for a trusted root and safe mode for any other, Mise's state inside the disposable copy
      and its search ended at the copy's parent in both, and resolution in safe mode as before.
- [ ] 1.2 Record the repair in the changelog. Done when the Unreleased section's Fixed list names
      it and the checks of the changelog pass.
- [ ] 1.3 Prove the download on hosted runners. Done when the proposal ref's push run passes the
      supply step in every job with the lock unchanged and each job's installed CPython build is
      read from its log, and one typed dispatch with the Windows legs has ended with each leg's
      supply step read.
