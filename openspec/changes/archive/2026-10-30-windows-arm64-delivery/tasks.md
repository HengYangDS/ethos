# Tasks

## 1. The Interpreter's Machine

- [x] 1.1 Add `process_machine()` to `manifest.py` and read it at the seven call sites: the runtime
      environment default, runtime selection, native-tool supply, Node supply and its wheel tag,
      the Python image observation, and the CI Mise target and cache path. Done when tests show an
      emulated x64 interpreter on Windows ARM64 naming `AMD64` and selecting its runtime, and
      native hosts naming what `platform.machine()` names.
      (`test_runtime_identity_names_the_machine_its_interpreter_executes`,
      `test_selection_compares_the_interpreter_not_the_cpu_a_host_reports`,
      `test_an_emulated_x64_interpreter_reads_the_x64_archive_and_tag` and the Mise target cases
      at `a2fdaa7d8`; on the hosted `windows-11-arm` leg the receipt names architecture
      `x86_64`.)

## 2. Host-Keyed Publication

- [x] 2.1 Name each archive and Mise platform for the host its release leg declares, refuse a
      runtime of another operating system, publish wheels only where host and runtime agree, and
      require the three required platforms natively. Done when the release publication tests cover
      an emulating `windows-arm64` leg, a foreign runtime and an emulated required platform.
      (`test_an_emulating_host_publishes_the_archive_it_qualified` at `a2fdaa7d8`.)

## 3. Hosted Qualification

- [x] 3.1 Declare one host per release leg, add the `windows-11-arm` leg with the x64 CPython to
      host conformance for Python 3.14 and to the release matrix, and regenerate the workflow with
      `ethos lane project`. Done when a test pins every leg's host to its runner and interpreter,
      and the job identity and projection tests pass.
      (`test_each_release_leg_declares_the_host_its_runner_provides`, the job identity test and
      `lane project --check` at `a2fdaa7d8`.)
- [x] 3.2 Publish the proposal to GitHub and record the `windows-11-arm` leg's result and duration,
      and which `ssh-keygen` it resolves. Done when the leg passes.
      (Run 40985443017 at `a2fdaa7d8`: the leg passed in 77 min, the longest of the run, against
      30–56 min for `windows-latest`; its wheel conformance took 73 min. Its observed `PATH` is
      Git's `bin`, then `C:\Windows\System32\OpenSSH`. Git for Windows ships `ssh-keygen` only in
      `usr\bin`, so signing resolves Windows OpenSSH by inference; the log does not name the
      binary.)

## 4. Contract Texts

- [x] 4.1 Modify `distribution`'s platform requirement. Done when strict validation passes and the
      simulated archive leaves every spec valid.
      (At `a2fdaa7d8` the `openspec` gate passed and the simulated archive validated all 12 specs.)
- [x] 4.2 Record the change under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown-lint` and
      `prose` pass.
      (`markdown-lint` and `prose` passed at `a2fdaa7d8`.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out and publish `dev` and
  `main` to GitHub and GitLab.
- Release `0.2.0-alpha.21`, then rebind DDWG to it. DDWG's GitLab Windows job installing it on
  `ci-windows-arm64-shell` accepts the platform for its consumer.
