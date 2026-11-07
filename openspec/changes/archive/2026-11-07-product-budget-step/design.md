# Design

## Context

Two facts are checked in many places with copied code. `ETHOS_ACTOR` is read directly 47 times in 32
product modules, with the local-process default inlined 12 times and four reads that skip `.strip()`
(`rg -n ETHOS_ACTOR src/ethos`, 2026-11-07). Hexadecimal identities, SHA-256 digests and Git object
IDs, are checked procedurally by about 30 hand-written expressions such as
`len(value) == 64 and not set(value) - set("0123456789abcdef")`. The function
`mapped_retag_receipt` (`src/ethos/adapters/mutation/accepted/retag.py`) has had no caller since it
was added. The product sits at 73,163 of its 75,000 line-equivalent ceiling (DR-0019).

## Goals / Non-Goals

Goals:

- One owner for the process actor and one for hexadecimal identity checks, used by every product
  reader.
- Delete the dead receipt reader.
- A fresh necessity review for one product step, recorded in DR-0020.

Non-Goals:

- Injecting a typed actor into operations; that is the catalog's `environment-entry` Change, which
  moves this owner into the application's invocation.
- Replacing Pydantic field patterns with shared types; that belongs to the 0.3.0 typed seams.
- Changing a check's accepted lengths or alphabets, except the four actor reads that now strip.

## Decisions

1. **The actor owner lives in `ethos.adapters.actor`.** Reading the environment is an adapter
   concern, and both surfaces and adapters already import adapters. It exposes `ACTOR_VARIABLE`,
   `LOCAL_ISSUER`, `process_actor()` and `process_issuer()`; each call reads the environment, so
   tests that set the variable keep working. Continuation texts that name the variable use the
   constant.
2. **The identity checks live in `ethos.contracts.digest`.** They are pure and dependency-free, so
   every layer may import them. `is_sha256_hex(value)` accepts 64 lowercase hexadecimal characters
   and `is_object_id(value)` 40 or 64. A check with another shape (a prefix, bytes, a 16-character
   index) keeps its own code.
3. **One step, after the removal.** DR-0020 records what this Change removed, why the catalog,
   pin and rehearsal Changes still need the space, and that further reduction is structural (the
   0.3.0 typed facts and Git port), then moves the product ceiling to 80,000.

## Risks / Trade-offs

- The mechanical replacement touches about 50 modules; the whole suite and the type checker cover
  it, and no accepted value changes except the stripping.
- The step gives about 6,800 line-equivalents of space against about 2,900 planned for the RC; the
  next step needs its own review.
