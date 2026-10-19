## Context

See [proposal.md](proposal.md). The orchestration obligation reports a CI step as inline shell
whenever its text is a shell program, and its only repair is one native command or toolchain-owner
task. Tracked scripts already have a record-based admission: an output that a catalogued generator
recorded with its version and SHA-256 conforms. The user's native-execution rule reads: "Retain an
official installer, executor-generated script or demonstrably necessary OS glue only with its owner,
necessity, exact scope and actual target-platform evidence."

## Goals / Non-Goals

**Goals:**

- Give necessary glue in a CI step one conforming, reviewable home, bound to the exact text it
  runs.
- Keep orchestration out of retained glue.

**Non-Goals:**

- Verifying that evidence is true or that glue is necessary.
- Retaining shell programs in gates or tracked scripts.
- Converting adopter pipelines.

## Decisions

### A record bound to exact step text

The catalog's `[pipelines.retention]` table names three things:

- the record carrier, `.config/ci/retained-steps.toml`;
- the classes;
- the platforms.

Each `[[step]]` entry gives `file`, `jobs`, `sha256`, `class`, `owner`, `reason`, `platforms` and
`evidence`.

The digest covers the step string as the Forge reads it after YAML parsing. Requoting a step or
switching its block scalar therefore keeps the record current, while any change to what runs
invalidates it. Matching uses file, job and digest rather than a step index, so reordering steps
also keeps the record current.

This follows the tracked-script generator records: a repository records a fact about its own bytes,
under a rule that ETHOS defines and checks the same way everywhere.

### Each listed job is its own claim

A record lists every job that carries the identical step. Each listed job must contain a step with
the recorded digest; a listed job that does not reports `retained-step` for that pair. One sibling
that still matches therefore cannot keep a deleted or drifted copy alive.

### What is never glue

Only two classes are admitted:

- an official installer;
- operating-system glue that a runner needs before a native command or toolchain-owner task can
  run, such as enabling Git long paths on Windows before checkout, or opening an operating-system
  session for a credential store.

Some steps are never glue, and each already has an owner:

| Step                                                                                  | Owner                                                        |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Mode branching and argument assembly                                                  | A product command, or native Forge configuration             |
| Platform and identity preconditions, such as checking the architecture or the user ID | Runner selection already fixes them                          |
| Integrity checks, such as a `sha256sum` comparison                                    | The toolchain owner's locked checksums, or a product command |

Reviewers apply this rule; the class vocabulary is its mechanical part.

Executor-generated scripts are deliberately absent from the classes. They are tracked files, and the
generator record is how they are admitted.

### Gates and tracked scripts stay strict

A gate runs under ETHOS's own controlled execution and never on a fresh runner, so ETHOS can always
invoke the native command directly. A step that runs a tracked script keeps its
`shell-orchestration` gap; the generator record is how such a script is admitted.

### Completeness, not truth

The paradigm checks four things:

- each record is complete;
- it uses catalogued classes and platforms;
- its digest is well formed;
- every listed job carries the step.

It cannot check whether the evidence is real or shows necessity; the review of the adopting
repository's Change judges that.

DR-0012 says a repository cannot declare an exception. A record is not an exception, because it
admits recorded bytes under the evidence that the obligation names, never a repository by identity.
DR-0012's consequence for scripts states this boundary.

## Risks / Trade-offs

- [A record could become a way to keep orchestration] → Two things guard against this. The class
  vocabulary and the rule above are applied in the adopter's review. The record's reason and
  evidence sit beside the pipeline model.
- [A changed generator rewrites the projected step text] → Records digest the parsed string, so
  container formatting does not matter. A real change to the text requires re-justification, by
  design.

## Migration Plan

ETHOS itself has no retained steps. aigw-cli and openai-responses-proxy adopt a runtime that
contains this Change in their own convergence Changes. They convert orchestration and record only
necessary glue.

## Open Questions

None.
