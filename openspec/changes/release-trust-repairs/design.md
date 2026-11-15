# Design

## Context

See the [proposal](proposal.md) and the [delta](specs/runtime-activation/spec.md).

- `_selection` (`src/ethos/adapters/repo/runtime/pin_selection.py`) reads the lock entry of the
  host's platform where the transition would select the pinned bytes. Decision 4 of the archived
  `pin-selection` design calls the lock a precondition; the code required the entry only outside
  the checksum class. `follow_accepted_pin` has three call sites in two modules: the adoption plan
  and its apply, and the hook activation that `hook install`, `lane start` and the candidate
  bootstrap share.
- The provenance page (`docs/governance/provenance-and-attestation.md`) defines the checksum
  class: a release without an attestation, or one whose attestation names another commit than its
  tag. Only its checksums bind its files.
- The shared conformance script (`tools/ci/delivery/acceptance/mcp.py`) runs in two places: from
  source in one unit test, and in the installed environment's own interpreter during package
  acceptance. Its function `_adoption` is pinned at its score of 16 in
  `tests/fixtures/decision-density-baseline.json`.

## Goals / Non-Goals

Goals:

- No class of pinned release is selected without the lock entry that binds it.
- The conformance refuses a planned file that the build should not plan, and a missing one.

Non-Goals:

- The explicit release transition's finding, which `release-acceptance` decides with the
  transition's first caller.
- Comparing an installed release with its lock entry. Mise installs, and the hosted journey admits
  the lock.
- A new gap code or a new option.

## Decisions

1. **Every class needs the lock entry of the host's platform, and the checksum class needs its
   checksum.**
   - **Rests on:** decision 4 of the archived `pin-selection` design; the provenance page's
     definition of the class; `LockEntry`, whose fields are empty where the lock records none
     (`src/ethos/repository/release/pin.py`); and three cases of
     `test_a_transition_follows_the_accepted_pin_forward_only`: no lock, an entry for another
     platform only, and an entry without a checksum.
   - **Considered:** requiring the entry alone, although an entry that records neither provenance
     nor a checksum binds nothing, and the hosted journey's lock admission requires the checksum
     in every class. Checking the checksum's form or comparing it with the installed bytes,
     although the lock is read and never trusted, ETHOS holds no archive at selection and the
     digest algorithm is Mise's choice. Refusing every checksum-class pin, although an accepted
     scenario selects one and the journey is built to install such a predecessor from its pin
     line.
   - **Chosen because:** in this class the recorded checksum is the only thing that binds the
     bytes, so its absence is a missing observation. One helper states the rule for both classes,
     and the selection's complexity score falls from 14 to 12 (complexipy, which
     `tests/architecture/test_decision_density.py` reads).
   - **Applies to:** a transition without `--runtime`, at the point where it would select the
     pinned bytes, for all three call sites. It does not prove that the install matches the entry.
2. **The state keeps the name `runtime_pin_unattested` and its repair.**
   - **Rests on:** the state's consumers: the adoption plan reports it, as a required gap when
     nothing is selected; hook activation keeps `CURRENT` or refuses by it; and `hook install`
     names its repair as the next action. None of them reads the release's class. The repair's
     command, `mise lock`, records a checksum where it records no provenance: the product's own
     lock holds 12 platform entries of the GitHub backend without provenance, each with its
     checksum (`.config/mise/mise.lock`).
   - **Considered:** a code of its own, which costs a registry row, a second repair text and the
     same cases in each consumer for one command. A changed repair text, which every reader of
     the attested class's state would see too.
   - **Chosen because:** no consumer would act differently, and these repairs add a gap code only
     where a fix needs one. The accepted cost is a name that says "unattested" for a release that
     has no attestation; the delta and the local-state page state what the name covers.
   - **Applies to:** the two new refusals of the checksum class. The attested classes keep their
     meaning.
3. **The conformance reads the release from the invoking build and checks one exact list in a
   named function.**
   - **Rests on:** the adoption operation, which plans the pin exactly when the invoking build is
     a release; the script's two launches, each in the interpreter of the build it checks; the
     equality of the three surfaces' previews, which the script asserts before the apply; the
     pinned score of `_adoption`; and `prove_brownfield`, which keeps the same exact list.
   - **Considered:** passing the release from package acceptance through the script's arguments,
     as the brownfield proof receives it, which changes three signatures and the argument list
     between two tools for a value that the script's interpreter holds. Reading the build from
     the applied result's own summary, with which the result under test supplies its
     expectation. A branch inside `_adoption`, which may not grow past its pinned score.
   - **Chosen because:** it is the smallest change that restores the exact list. No caller's
     signature changes, and the list is tested without a transport.
   - **Applies to:** the adoption of each of the three surfaces, from source and installed. The
     expectation is the product's own reading of its build. Package acceptance compares the
     console's version with the installed package's identity before the script runs, and its
     brownfield proof takes the release from the selected wheel, so a build that misread
     itself fails there.

## Risks / Trade-offs

- The exact list of a release build runs only where a release build is installed, as in the
  release run's package acceptance. No tag contains `44d0a756a`, so no release run has exercised
  this check or the brownfield list on a release build. A unit test covers the list for both
  kinds of build.
- `runtime_pin_unattested` and its repair speak of an attestation for a release that has none.
  `mise lock` is the right command in both classes. No hosted journey has locked a
  checksum-class release through the pin yet: the journey that proved the pin installed two
  attested predecessors.
- The lock entry is still only read. An install that Mise made from other bytes is selected once
  the accepted lock records a checksum for the platform; the hosted journey's two refusal cases
  are the evidence that a locked install refuses such bytes.
- The other review repairs of this batch edit `CHANGELOG.md` too, and one of them works in a
  module that calls the pin selection. The lane merges the shared hunks by meaning.
