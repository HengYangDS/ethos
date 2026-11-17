# Design

## Context

`authored_source_files` joins the inputs that `ethos lane format` and the source-format, Markdown,
prose, link and configuration gates read. Since this release's fix for vendored and generated
paths it leaves out what `received_paths` names, and that reader asks `git check-attr`, which
answers from every attribute source that Git knows.

Measured with Git 2.56.1 under the product's observation environment, in scratch repositories,
these sources reach the answer: a `.gitattributes` file of the worktree, tracked or not; the
index copy of a tracked one whose worktree file is deleted; the `info/attributes` file of the Git
directory, which a linked worktree shares with its repository; and a file that
`core.attributesFile` names in the repository's configuration or in the caller's configuration
overlay. A global and a system attributes file do not reach it. Git has no option that leaves
`info/attributes` out: a reading from the index, from a named tree or with `attr.tree` still
reads it.

A proof binds the commit, the index and the worktree. It binds neither `info/attributes` nor the
configuration, so one local line took a committed document out of the prose gate while the source
binding held.

Five readers followed Git's reading at 0.2.0-beta.10 and still do: path admission, the staged
size check, the staged text check, the paradigm report and its repair. The format gate's text
validity check skipped a marked path at 0.2.0-beta.10 and lost that reading when the selection
took it over.

## Goals / Non-Goals

Goals:

- The format command and the gates judge every path that no `.gitattributes` file of the
  worktree marks, whatever the Git directory holds.
- A path that such a file marks stays out, as this release's fix intends.
- No reader of 0.2.0-beta.10 changes its answer, and no tree that passed it meets a new refusal.

Non-Goals:

- Binding or reporting local Git state. The five older readers keep Git's reading; their use of
  local state is the subject of the draft `local-git-state-binding`.
- A note in a result that names a local mark.
- Reading marks from the commit alone. An uncommitted `.gitattributes` file of the worktree
  counts, as it did before this Change.

## Decisions

1. **The authored selection reads its marks through an empty Git directory of its own.**
   - **Rests on:** the measurement of sources in Context, and twelve local states measured for
     four candidate readings and for this Change's reader: a mark in the worktree's file, in the
     local file, in both, a local line that takes a mark back, one that applies a tracked macro,
     a configured attributes file, a linked worktree and a SHA-256 repository among them. This
     reader gave the answer of the worktree's files in all twelve.
   - **Considered:** taking no mark while the local file holds a line that names one, which was
     wrong in five states: a worktree mark stops counting on a host whose local file marks any
     other path, so the format command rewrites a vendored license there again, and the wrong
     pass stays through `core.attributesFile` and through a local line that applies a tracked
     macro. Taking a mark unless the untracked sources alone give it, which was wrong in three
     states and leaves the macro's wrong pass. Parsing `.gitattributes` in the product, which is
     a second reader of Git's pattern, macro and nesting rules.
   - **Chosen because:** Git stays the one reader of attribute syntax, the product opens no
     attributes file, and where the reading differs from Git's it judges more. Accepted: one
     temporary directory and two more Git processes in each selection.
   - **Applies to:** `authored_source_files` alone, so the format command and the gates named
     in Context. The five older readers are not covered.
2. **The repository's case rule is handed to the reading.**
   - **Rests on:** a measurement: Git writes the case rule of the volume into a directory that
     it makes, and under the temporary volume's rule a pattern that differs in case from its
     path marked that path in a repository whose own rule is exact case.
   - **Considered:** keeping the temporary directory's rule; reading the repository's
     configuration file in the product.
   - **Chosen because:** Git's own configuration reader answers `core.ignoreCase` in one
     process, with Git's default where the repository does not set it, and the answer goes to
     the reading as a command-line setting. Cost, as means of ten calls on this repository's
     1,516 listed Markdown paths: 6.5 ms for the case rule's read and 8.4 ms to make and remove
     the directory, so the selection's reading takes 25.2 ms where Git's took 11.0 ms. One whole
     selection of the prose gate's inputs took 85 ms at its least before this Change and 87 ms
     after it, five calls each on a loaded host, which is inside its spread.
   - **Applies to:** `core.ignoreCase`. No other setting of the repository reaches the reading.
3. **The directory is temporary and bare of a template, and Git's refusal keeps its own error.**
   - **Rests on:** the product's temporary workspaces, which leave through a context manager;
     the four entries that Git makes without a template, none of them a hook, an exclude file
     or an attributes file; the product's Git runner, which starts Git in the resolved root, so
     the reading names that directory as its work tree whatever form the caller's root has; and
     the consumers' existing handlers: the prose, Markdown, link and configuration gates answer
     a refused Git read with `quality_input_inventory_unavailable` and the verdict unknown, and
     the format gate and command answer it as blocked with Git's error.
   - **Considered:** the older reader's rule, under which an unavailable observation marks
     nothing. For a check that judges more. For `ethos lane format --apply` it would rewrite
     received bytes after a read that failed. A gap code of its own, which the law freeze does
     not admit.
   - **Chosen because:** a selection that cannot read its marks does not know what is received,
     and every consumer already says so in words that exist.
   - **Applies to:** a Git that cannot start, and a refused directory or attribute read. A read
     that succeeds with output that cannot be parsed marks nothing, as before.
4. **The format gate's text validity check keeps Git's own reading.**
   - **Rests on:** `authored_text_files` at 0.2.0-beta.10, which left out what `received_paths`
     names. This release's fix removed that because the selection had already left those paths
     out. Under decision 1 a path that only the Git directory marks is selected again, and its
     bytes would meet a check that 0.2.0-beta.10 did not apply to it.
   - **Considered:** the worktree's reading here too, and no skip at all. Under either, the
     check reads a locally marked path that it skipped at 0.2.0-beta.10, and refuses one whose
     bytes are binary or are not UTF-8 with `authored_text_binary` or `authored_text_encoding`.
   - **Chosen because:** no tree that passed the predecessor may meet a new refusal. Accepted:
     this one check follows local state, in the predecessor's direction, and joins the older
     readers.
   - **Applies to:** `authored_text_files`, which the format gate and command call before a
     formatter runs. The text check of the Markdown and prose gates reads every selected
     Markdown file, as at 0.2.0-beta.10.
5. **The requirement names the source that counts, and no result names a local mark.**
   - **Rests on:** the accepted requirement, whose words "the repository's Git attributes" do
     not say which source counts.
   - **Considered:** a note in each gate's result; no delta.
   - **Chosen because:** the requirement and the release entry are where a reader looks for the
     rule, and a report of local Git state is a subject of its own.
   - **Applies to:** the requirement "Received paths are not authored inputs" and one added
     scenario. The requirements on received names and on code size are unchanged.
6. **The reading sees only the attribute files that Git tracks or would add.**
   - **Rests on:** the release lead's probe of the gate's verdict, run at three trees with
     each tree's own code. With a `.gitattributes` file beside the document that the Git
     directory's exclude file hides, the prose gate passes at the release head and at the
     release head with decisions 1 to 5; it blocks at 0.2.0-beta.10. Git's status does not
     name the file and the source binding holds.
   - **Considered:** stating that route as a known defect of the release; reading the marks
     from tracked files alone, which fails the cause's own test, whose attributes file is
     never staged, and ignores a file that the next commit would carry.
   - **Chosen because:** a release that still passes a proof on a file it did not read is
     the defect this Change exists for. The files that Git lists with `--cached --others
--exclude-standard` are those the source binding can see. They are copied, without
     following a link, into the reading's temporary directory, and Git resolves the marks
     there; no attributes file is parsed by ETHOS.
   - **Applies to:** `worktree_received_paths`. Where Git gives no listing, as outside a
     repository, the reader receives nothing and every name stays judged.

## Risks / Trade-offs

- An untracked `.gitattributes` file that Git would add still marks, as a tracked one does: a
  proof's source binding sees it, and the next commit can carry it. One that an exclude rule
  hides marks nothing since decision 6.
- A mark in an indexed `.gitattributes` file whose worktree file is deleted is not taken, so
  its paths are judged. Measured. A proof's source binding refuses that worktree. A sparse
  checkout that leaves a `.gitattributes` file out is the same case and was not measured.
- A refused read stops a check that the release head let judge everything. The prose gate
  already makes a temporary directory in each run; the format gate's own code made none.
- The reading takes its root as the work tree. Measured at the reader: for a root that is a
  subdirectory of its repository it reads no `.gitattributes` file above that root, so more is
  judged; for a root outside every repository it reads that directory's own file, where Git's
  reading marked nothing. The command line resolves its root to the top level of the worktree,
  so neither reaches a command or a proof.
- The reading ran on one Git version, 2.56.1, on macOS and on Python 3.14. It starts processes
  and makes a directory, so the two older interpreters and Windows need their own runs.
