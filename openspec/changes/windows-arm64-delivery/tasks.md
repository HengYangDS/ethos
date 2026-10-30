# Tasks

## 1. The Interpreter's Machine

- [ ] 1.1 Add `process_machine()` to `manifest.py` and read it at the seven call sites: the runtime
      environment default, runtime selection, native-tool supply, Node supply and its wheel tag,
      the Python image observation, and the CI Mise target and cache path. Done when tests show an
      emulated x64 interpreter on Windows ARM64 naming `AMD64` and selecting its runtime, and
      native hosts naming what `platform.machine()` names.

## 2. Host-Keyed Publication

- [ ] 2.1 Name each archive and Mise platform for the host its release leg declares, refuse a
      runtime of another operating system, publish wheels only where host and runtime agree, and
      require the three required platforms natively. Done when the release publication tests cover
      an emulating `windows-arm64` leg, a foreign runtime and an emulated required platform.

## 3. Hosted Qualification

- [ ] 3.1 Declare one host per release leg, add the `windows-11-arm` leg with the x64 CPython to
      host conformance for Python 3.14 and to the release matrix, and regenerate the workflow with
      `ethos lane project`. Done when a test pins every leg's host to its runner and interpreter,
      and the job identity and projection tests pass.
- [ ] 3.2 Publish the proposal to GitHub and record the `windows-11-arm` leg's result and duration,
      and which `ssh-keygen` it resolves. Done when the leg passes.

## 4. Contract Texts

- [ ] 4.1 Modify `distribution`'s platform requirement. Done when strict validation passes and the
      simulated archive leaves every spec valid.
- [ ] 4.2 Record the change under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown-lint` and
      `prose` pass.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out and publish `dev` and
  `main` to GitHub and GitLab.
- Release `0.2.0-alpha.21`, then rebind DDWG to it. DDWG's GitLab Windows job installing it on
  `ci-windows-arm64-shell` accepts the platform for its consumer.
