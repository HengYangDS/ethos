# Tasks

## 1. Producer

- [x] 1.1 Report a byte mismatch as `block` with its own code, and keep every other refusal as
      `unknown`. Done when the generated-observer and received-archive tests show `block` with the
      mismatch code for drifted bytes and `unknown` otherwise, and a mutation that reports
      mismatches as `unknown` fails them. The generated-observer, received-archive, public and CUE
      input tests pass, 140 provenance and projection tests in all; reporting mismatches as
      `unknown` again fails three of them.

## 2. Specification and notes

- [x] 2.1 Add the `quality` requirement. Done when strict validation and the cumulative archive
      simulation pass. Strict validation passes, and the archive simulation of both Changes in order
      finds 12 of 12 specifications valid.
- [x] 2.2 Name the change in the Unreleased notes. Done when `changelog_errors` reports nothing. It
      reports nothing before and after the edit.
