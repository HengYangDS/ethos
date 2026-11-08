# Tasks

## 1. Catalog

- [x] 1.1 Declare the 29 root operations and the six request models. Done when the table test shows
      unique well-formed IDs, described keyword-only fields, a kind and a verdict exit for every
      write, operations under `ethos.application` and keyword signatures equal to the models. At
      14:15:08 the precheck's 295 impacted test files passed at `1355ead0b` (5,854 passed, 2
      skipped); at 15:07:25 the catalog table test passed again at `d4e015cd8` among 170 tests: 29
      operations with unique IDs, described keyword-only fields, a kind and a verdict exit for every
      write, operations under `ethos.application` and SDK signatures equal to the six request
      models.
- [x] 1.2 Select through one function for every transport. Done when a test shows a receipt apply
      with `--peer` refused alike through the CLI, the SDK and the MCP `publish` tool before any
      read, and `--readiness` alone refused alike through `ethos prove` and `prove_repository`. At
      14:15:08 a receipt apply naming `--peer` refused alike with `command_field_refused:peer_ids`
      through the CLI, `publish_repository` and the MCP `publish` tool on a directory that is not a
      repository, so nothing was read, and `--readiness` alone refused alike through `ethos prove`
      and `prove_repository`.
- [x] 1.3 Partition every field per entry. Done when the table test enumerates every selector
      assignment of `prove`, `land`, `publish` and `adopt` and pins the unmatched sets (6, 8, 9,
      23). At 14:15:08 the table test enumerated every selector assignment: none selects two
      operations, and 6, 8, 9 and 23 select none for `prove`, `land`, `publish` and `adopt`.

## 2. Command line

- [x] 2.1 Build the six root commands from the catalog. Done when each operation's example argv
      parses and selects alike through Cyclopts and the kernel, and the converted CLI tests pass
      through the generic adapter with each operation's exit. At 14:15:08 every operation's example
      argv parsed and selected alike through Cyclopts and the kernel, every field's kernel spelling
      parsed, and the converted CLI tests passed through the generic adapter with each operation's
      exit.
- [x] 2.2 Report usage as results. Done when a subprocess journey shows `land --closeout --release`,
      `land --tag v1` and `land --bogus` exit 2 with schema-3 JSON on stdout, and a closed stdout
      exits 3. At 14:15:08, at `1355ead0b`, `land --closeout --release`, `land --tag v1`,
      `land --bogus`, `land true`, `land --no-apply`, `publish --apply` and `adopt --create` without
      `--root` exited 2 through the console with a schema-3 `usage_refused` result on stdout, the
      parser's message reached stderr, and the closed and full-pipe stdout tests exited 3; at
      15:07:25, at `d4e015cd8`, the same refusals passed in process with their human frame on
      stderr.
- [x] 2.3 Print the catalog as help. Done when `ethos --help --json` prints the root catalog within
      its declared help budget and writes no detail. At 14:15:08 `ethos --help --json` printed the
      29 operations within the 48 KiB help budget (40,755 bytes measured) without a `bound`, and
      `ethos land --help --json` printed the land part; at 15:07:25 the in-process console printed
      it too.

## 3. Next steps and removals

- [x] 3.1 Classify root argv through the selected entry. Done when every in-process run's
      `next.form` equals its parse's selection and the retired root rows of the step table are gone.
      At 14:15:08 every in-process run's `next.form` equalled the operation its parsed request
      selects, the root rows of the step table were gone, and `next` for a root argv that selects
      nothing was `opaque`, destructive and `human`.
- [x] 3.2 Remove the direct publish apply. Done when `ethos publish --apply` without `--receipt` and
      the MCP `publish` tool's apply without a receipt refuse, and the converted tests pass. At
      14:15:08 `ethos publish --apply` without `--receipt` refused with
      `command_operation_unmatched:publish`, and the converted publication tests passed by probe and
      receipt apply.

## 4. Acceptance

- [x] 4.1 Pass readiness and the precheck's static checks at the lane head. Done when both pass on
      the committed head, and the precheck's impacted test files have passed at the implementation
      commit, with the tests of each later change passing at the head. Readiness passed its 28 gates
      at `d4e015cd8` at 14:35:08 and the precheck's static checks found nothing there at 15:07:59;
      its 295 impacted test files passed at `1355ead0b` at 14:15:08 (5,854 passed, 2 skipped), and
      170 tests of the files changed since passed at `d4e015cd8` at 15:07:25.
