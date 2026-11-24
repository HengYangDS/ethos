# Design

## Context

Each release's changelog entry carries a "Known open defects" list, copied by hand from release to
release. A defect has no file of its own: no lane records it with the work that found it, no lane
closes it with the work that repairs it, and no reader reviews its text. The owner decided on
2026-11-19 (「按照 A」) that the record is a carrier inside the repository, complete and usable with no
remote, and that the two Forges' tickets are at most projections of it.

## Goals / Non-Goals

Goals:

- The 62 known defects of this repository enter as tracked text, one file each, in the form the
  carrier's design fixed.
- Both Markdown tools that the product's gates run read the entries: `markdown-lint` already does,
  and a direct `markdownlint-cli2` run must agree with it.
- Vale reads the prose and the fields of an entry, and refuses nothing that the form itself puts
  there.

Non-goals:

- No command reads the entries yet (`ethos defect list`), and no gate refuses a malformed one: both
  are later Changes.
- No Forge ticket, no importer and no sync between Forges.
- No product code and no requirement changes.

## Decisions

### The entry's form

`defects/<id>.md`. The id is the file's name, chosen once from the defect's subject: lowercase words
joined by hyphens, never a counter and never renamed. Line 1 is exactly `+++`; the fields end at the
next line that is exactly `+++`; the rest is prose.

```toml
title = "A pruned history-repair source refuses later retirements"
state = "open"            # open | closed
since = "v0.2.0-beta.10"  # the earliest released tag known to have it
fixed_in = ""             # the tag whose release first carries the repair; empty while open
workaround = "…"          # text, or "none"
```

The five fields are required and each holds a string. An optional table `[tickets]` maps a peer's
name to a ticket number; no entry holds one today, and no Forge is written by this Change.

Who writes what: the lane that finds a defect adds its entry with the work that found it; the lane
that repairs it sets `state = "closed"`; the change that writes a release's entry fills `fixed_in`
for the entries closed since the previous tag, and fills an empty `since` with that release's tag
when the defect is still there. No open entry is edited at a release.

### The reading rules

An entry, or the directory, is malformed when:

- its text is not UTF-8 or starts with a byte-order mark;
- its first line is not exactly `+++`, or no later line is exactly `+++`;
- the lines between the two do not parse as TOML;
- one of the five fields is missing, or a key is neither one of the five nor `tickets`;
- a value has the wrong type: each of the five is a string, and `tickets` is a table whose values
  are whole numbers above zero;
- `title` is empty; `workaround` is empty (it holds text or "none"); `state` is neither `open` nor
  `closed`; `fixed_in` is set while `state` is `open`;
- a peer name in `tickets` has a dot, slash, colon or at sign;
- its id is not lowercase words joined by hyphens; two ids differ only by case; one ticket number of
  one peer is claimed by two entries;
- the directory holds any other file, at any depth.

An empty `since` is not malformed: no released tag is known to carry the defect, which is the case
of a defect found in code that has not been released.

Until the read command exists, these rules are checked when an entry is written, not by a gate. The
check that names a malformed entry enters later as a reporting obligation, as every new obligation
does.

### The two configuration lines

The product's `markdown-lint` gate takes every authored `*.md` file through Git's own pathspec, so
it reads the entries without a change. A direct run of `markdownlint-cli2` reads only its `globs`,
and `defects/*.md` joins them so that both read the same files.

Vale lints TOML front-matter fields as text. In a `title` or a `workaround`, a code span such as
`` `ethos host run` `` is plain text, and the rule that writes the product's name in capitals
refuses it. The file already ignores seven front-matter keys of other documents for the same
reason. No other tracked Markdown under `docs`, `rules`, `openspec/specs` or `.agents` uses a
`title` or a `workaround` front-matter key, so the two scopes touch only the entries.

### The entries of this Change

62 entries, read against the rules above on 2026-11-25 by a script: none malformed, 55 open, 7
closed, one with an empty `since` (`retire-supply-release-absent-ignores-grace-days`: its switch
ships first with the next release). Every tag named by a `since` resolves in this repository. An
entry is closed when `dev` carries its repair; its `fixed_in` stays empty until a release carries
it.

## Risks / Trade-offs

- The entry text becomes public when it lands. Each entry states a defect of this repository and,
  where one exists, how to work around it; the texts were written for that audience, and the
  private-address preview runs before the proof.
- An entry can go stale: nothing yet notices when a repair lands without closing its entry. The
  changelog's release change closes the entries it repairs, and the read command's later Change
  makes the state visible.
- A wide TOML field line (32 entries carry one) is allowed by `markdownlint-cli2`, which has no
  line-length rule, and by Prettier, which does not reflow a front-matter block.

## Migration Plan

The directory appears at once, with every entry; nothing reads it yet, so no reader changes. If the
Change is withdrawn before its landing, the directory and the two configuration lines are removed
with it.
