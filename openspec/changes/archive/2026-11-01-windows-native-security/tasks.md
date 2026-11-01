# Tasks

## 1. Dependency

- [x] 1.1 Declare `pywin32>=312; sys_platform == 'win32'`, exempt it from deptry's unused-dependency
      rule because it is imported by name, and parse requirements with `packaging` in the
      declaration check. Done when the dependency hygiene gate passes and a requirement with two
      bounds is still refused.
- [x] 1.2 Admit the hosted `supply_image` build from a proposal ref. Done when the projected
      workflow's condition accepts `refs/heads/proposal/` and the projection check passes.
- [x] 1.3 Build the supply image from the lane's lock commit and bind its digest. Done when a GitLab
      pipeline of the lane's proposal passes its supply manifest check (pipelines 13597 and 13599).

## 2. Native Windows calls

- [x] 2.1 Observe trust-anchor protection from the native security descriptor. Done when the owner,
      writer, inherit-only, null-DACL and unavailable cases pass with replaced facts on every hosted
      platform (GitHub run 41344413371).
- [x] 2.2 Protect a trust anchor with an exclusive protected DACL. Done when the Windows case plants
      a foreign writer natively and the anchor reads unprotected in a hosted Windows run of the
      lane's proposal (GitHub run 41344413371).
- [x] 2.3 List process command lines through WMI on Windows. Done when a hosted Windows run of the
      lane's proposal lists its own command line and the unavailable case fails closed elsewhere
      (GitHub runs 41341527693 and 41344413371).
- [x] 2.4 Capture Windows stderr in a file and delete the post-kill `communicate()`. Done when a
      timed-out command whose descendant holds its output returns within its bound on every hosted
      platform (GitHub run 41344413371).
- [x] 2.5 Delete `windows_powershell`, its diagnostic and the UTF-8 preamble. Done when no product
      or tool code starts PowerShell, and only the paradigm's and the CI projection's shell
      vocabulary names it.
- [x] 2.6 Run the Windows cases in the hosted host proof. Done when `HOST_CASES` lists them and the
      delivery pipeline test passes.
- [x] 2.7 Import pywin32 where a call needs it. Done when a hosted Windows run of the lane's
      proposal builds the editable package, whose version source imports ETHOS modules without
      pywin32 (GitHub runs 41338070143 and 41344413371).

## 3. Specifications

- [x] 3.1 Write the `command-plane`, `runtime-activation` and `quality` deltas. Done when strict
      validation passes.

## Workflow follow-up

- Before landing, the GitHub Windows jobs and the GitLab pipeline of the proposal at the lane's last
  code commit pass; the archive commit changes only OpenSpec documents, which its own proof checks.
  GitHub issue #25 receives the result.
