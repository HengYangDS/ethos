# Design

## Context

See the [proposal](proposal.md). One governed repository binds sqlfluff with an explicit
configuration file, which it keeps under another name in the catalogued directory. That
repository's session ran a proof preview with the 0.2.0-beta.11 product on 2026-11-22, without a
bind, and reported the catalog's missing row as the one gap that its own declarations cannot
close. The same preview showed a second, smaller thing: a name that an upstream contract fixes is
admitted by the profile's `identifier_sources`, and the gap's repair text names two ways out and
not that third one.

The readings below were taken on 2026-11-22 at `dev` `024c217bf`: the paradigm's answers for five
trees with the row added to a copy of the packaged declaration in memory, and each tool's
resolution of relative paths from its own source, documentation or a run. The tests of this
Change repeat the paradigm's answers at the lane's head.

## Goals / Non-Goals

Goals:

- The carrier `.config/checks/sqlfluff/.sqlfluff` is admitted.
- The authored-name gap names every repair that the product admits.
- The configuration reference says how sqlfluff, Ruff and coverage.py resolve the relative paths
  of an explicit configuration file.

Non-Goals:

- A sqlfluff gate. ETHOS runs none; the row admits a carrier.
- A refusal of a root `.sqlfluff` or of a `[tool.sqlfluff]` table. The row declares neither
  `root_names` nor `manifest_tables`.
- A carrier in TOML. sqlfluff reads a file given by path as INI unless its base name is
  `pyproject.toml`.

## Decisions

1. **The row declares its carrier and nothing else.**
   - **Rests on:** the five readings: with the row, the carrier passes; `config.ini` beside it
     stays refused; `policy.toml` alone, a root `.sqlfluff` and a `[tool.sqlfluff]` table keep
     today's answers. Two further answers change, and neither refuses a tree that passes today.
     A `.sqlfluff` elsewhere under the configuration root is still refused, now with the
     repair that names the carrier. And a gate may declare `sqlfluff` as its tool, which the
     gate contract refused for an unknown id; the carrier is then that gate's policy source and
     the only tracked file of its name.
   - **Considered:** `root_names = [".sqlfluff"]`, which would name the carrier in the root
     catalog's repair, and `manifest_tables = ["sqlfluff"]`.
   - **Chosen because:** a root name would turn the root catalog's gap into a move obligation and
     a manifest table would refuse a table that passes today; the law freeze admits a narrowing
     and no new refusal.
   - **Applies to:** `src/ethos/contracts/paradigm/paradigm.toml`.
2. **The carrier keeps the tool's own file name.**
   - **Rests on:** sqlfluff's loader, which chooses TOML only for the base name `pyproject.toml`
     and reads every other file as INI.
   - **Considered:** `.config/checks/sqlfluff/sqlfluff.toml`, the form of the other rows.
   - **Chosen because:** the tool cannot read it.
   - **Applies to:** the row's `carrier`.
3. **The authored-name repair names the declaration of an identifier source.**
   - **Rests on:** `identifier_sources`, shipped with 0.2.0-beta.11, which admits a name that a
     tracked manifest repeats; the gap's text named a rename and a `linguist-*` mark only.
   - **Considered:** a separate gap code for names that look like upstream identifiers.
   - **Chosen because:** the product cannot tell such a name from a misspelt one; the text can
     say what the repository may declare.
   - **Applies to:** `src/ethos/repository/paradigm/names.py` and its test.
4. **The statement on relative paths has one owner, this Change.**
   - **Rests on:** two drafts named it: this one for sqlfluff, Ruff and coverage.py, and
     `configuration-reference-gaps` for Ruff and coverage.py.
   - **Considered:** leaving it to the other draft, whose remaining items wait for a whole-suite
     run.
   - **Chosen because:** the three facts are established and the carrier's entry needs
     sqlfluff's; a statement kept in two drafts would be written twice.
   - **Applies to:** `docs/reference/configuration.md` and the other draft's proposal.

## Risks / Trade-offs

- A repository that keeps `config.ini` in that directory, as the reporting one does today, renames
  its file in the commit that binds the release that carries the row; the gap it sees until then
  is today's. That repository's session ran its own file under the name `.sqlfluff` through
  sqlfluff 4.5.0 on 2026-11-22 and reported identical output.
- A repository that declares the tool in a gate and keeps sqlfluff's per-directory files beside
  its SQL meets the gate contract's refusal of a second file of the carrier's name. The binding
  flags make the tool ignore those files, so they hold no policy; the repository removes them
  when it declares the tool.
- The reference's three statements on path resolution describe the tools as they were on
  2026-11-22 (Ruff's documentation, sqlfluff's source on its main branch, coverage.py 7.17.3 by a
  run). A later release of a tool can change them; the reference says which base each tool uses
  and does not promise it.
