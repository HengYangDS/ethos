# Design

## Context

See the [proposal](proposal.md). `adoption_plan` composes its file effects as bindings: a path, its
current text, whether it exists and is safe, and the planned text. A binding conflicts when its
file is unsafe or holds other nonempty text, so adoption replaces only an absent or empty file.
`github-pin` (C1) owns the pin's form in `ethos.repository.release.pin`: `bare_entry` renders the
whole entry and `declared_pin` reads a configuration in either form. The repository paradigm's
repair already sets and deletes one TOML key in place, keeping comments and every other line, and
`.config/mise/config.toml` is the documented owner of native tool selections.

`ethos adopt --exit` restores Git configuration and removes runtime selectors under one digest, with
a receipt and compensation; it touches no tracked file today.

## Goals / Non-Goals

Goals:

- A release build's adoption writes its own exact pin into the Mise configuration as one previewed,
  digest-bound step, and replaces no authored line.
- The exit removes the key that adoption wrote and nothing else.

Non-Goals:

- Moving an existing pin to another version: that is the bump Change of the same family.
- Replacing an `http:ethos` table: the adopter's migration lane does that once.
- Running `mise lock`, or reading the lock: adoption names the command and fetches nothing.
- A pin for a formed repository: formation stays offline and plans none.
- A second carrier: the pin lives only in `.config/mise/config.toml`.

## Decisions

1. The application layer names the release. `adopt_existing` reads the invoking build identity and
   passes its product version to `adoption_plan` only for a release build; a development build is
   no version that Mise could install. Formation calls the planner without a release, so it keeps
   its behavior. The result's `pin` field holds the version, or says `none:development_build`.
2. The pin is a third binding of the same plan. Its planned text is `bare_entry` for an absent or
   empty file. Otherwise each key of that entry is added through the paradigm repair's in-place
   setter where the file lacks it and kept where the file holds the same value; a key with another
   value is a conflict. The planned text must then read back, through `declared_pin`, as exactly
   the bare entry, which refuses a configuration that holds both pin forms or cannot take the lines.
   The entry is the one source of both keys, so the planner names neither.
3. Every plan step carries a unified `diff` of its file, empty for a conflict. A step that adds to
   a nonempty file has the action `extend_existing`; the generic rule that a nonempty file is a
   conflict stays for the profile and the OpenSpec configuration.
4. `relock` in the plan is true when an apply changed the Mise configuration, and the application
   layer then renders `mise lock` as the next action, since the planner owns no public next action.
   The command carries no directory: the release-candidate design fixes its text, and the
   continuation requirement now says that the caller runs it in the adopted root.
5. The exit plan names the bare pin's file and key and the file's text without that line, under the
   plan digest. The apply writes that text before it marks the receipt applied, and the file's prior
   bytes join the compensation set. The provenance setting stays: Mise applies it to every tool and
   no record says who set it, so removing it could weaken a repository that had set it itself. A
   pin in the options form or an `http:ethos` table is the repository's own and stays.
6. A failed apply removes every directory it made. The planner created one missing parent before;
   `.config/mise/` needs two, so each missing ancestor is recorded and removed leaf first.
7. The package acceptance learns the release case. A release build's brownfield adoption plans three
   files, so the brownfield check takes whether its artifact is a release build, and the MCP check
   requires the two bindings and verifies every planned file by hash.

## Risks / Trade-offs

- A release build now blocks adoption, runtime selection through `adopt --select-runtime` included,
  in a repository whose Mise configuration still holds an `http:ethos` table or another version.
  The conflict names the file; the repair is the bare entry of that release and `mise lock`.
- `mise lock` names no directory, so a caller outside the adopted root must change into it first.
- The provenance setting that adoption added stays after an exit and makes Mise verify every
  attested tool of that repository at install.
- Only `.config/mise/config.toml` is read: a pin in a root `mise.toml` is not seen as a conflict.
- An equal key written with a trailing comment is kept, but a file with CRLF line endings gets the
  new lines with LF endings.
- The release case of the package acceptance runs only in a release build's install smoke, so the
  unit tests cover it and no ordinary proof does.
- The product costs about 81 line-equivalents against a planned 55, because the exit, the nested
  directory compensation and the step diff were not in the estimate; tests cost about 161 against
  60, and tools about 5 against none.
