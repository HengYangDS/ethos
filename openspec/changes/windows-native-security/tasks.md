# Tasks

## 1. Dependency

- [ ] 1.1 Declare `pywin32>=312; sys_platform == 'win32'`, map its modules for deptry, and parse
      requirements with `packaging` in the declaration check. Done when the check passes and a
      requirement with two bounds is still refused.
- [ ] 1.2 Admit the hosted `supply_image` build from a proposal ref. Done when the projected
      workflow's condition accepts `refs/heads/proposal/` and the projection check passes.
- [ ] 1.3 Build the supply image from the lane's lock commit and bind its digest. Done when the
      proposal's GitLab pipeline passes its supply manifest check.

## 2. Native Windows calls

- [ ] 2.1 Observe trust-anchor protection from the native security descriptor. Done when the owner,
      writer, inherit-only, null-DACL and unavailable cases pass on every platform with replaced
      facts.
- [ ] 2.2 Protect a trust anchor with an exclusive protected DACL. Done when the Windows case plants
      a foreign writer with `icacls` and the anchor reads unprotected, on hosted Windows.
- [ ] 2.3 List process command lines through WMI on Windows. Done when the Windows case finds its
      own command line on hosted Windows and the unavailable case fails closed on every platform.
- [ ] 2.4 Capture Windows stderr in a file and delete the post-kill `communicate()`. Done when a
      timed-out command whose descendant holds its output returns within its bound on every
      platform, including hosted Windows.
- [ ] 2.5 Delete `windows_powershell`, its diagnostic and the UTF-8 preamble. Done when no product
      or tool code starts PowerShell, and only the paradigm's and the CI projection's shell
      vocabulary names it.

- [ ] 2.6 Run the Windows cases in the hosted host proof. Done when `HOST_CASES` lists them and the
      delivery pipeline test passes.

## 3. Specifications

- [ ] 3.1 Write the `command-plane`, `runtime-activation` and `quality` deltas. Done when strict
      validation passes.
- [ ] 3.2 Verify on hosted Windows before landing. Done when the GitHub Windows jobs of the lane's
      head pass, and issue #25 receives the result.
