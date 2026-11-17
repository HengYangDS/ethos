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
     temporary directory and several more Git processes in each selection. Measured at the
     lane head on this repository's 1,606 Markdown paths, the least of seven calls on a loaded
     host: 225.6 ms, where Git's own reading takes 13.7 ms; the listing of decision 6 is 28.5 ms
     of it. Before that listing, on a calmer host: 168.8 ms and 11.3 ms.
   - **Applies to:** `authored_source_files` alone, so the format command and the gates named
     in Context. The five older readers are not covered.
2. **The marks are read by exact case on every host.**
   - **Rests on:** a measurement: Git writes the case rule of the volume into a directory that
     it makes, and under that rule a pattern that differs in case from its path marked the
     path. The repository's own `core.ignoreCase` is local state as well: `git init` sets it by
     the volume, so one commit was left out on one host and judged on another.
   - **Considered:** handing the repository's rule to the reading, which the first form of this
     Change did and which a model review named as one more route for local state; keeping the
     temporary directory's rule.
   - **Chosen because:** a proof reads one commit the same on every host. The reading sets
     `core.ignoreCase=false` on its command line. A pattern in another case than its path marks
     nothing, so more is judged.
   - **Applies to:** the reading's own Git call. No setting of the repository reaches it.
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
6. **The marks are read from the tree that the source binding sees.**
   - **Rests on:** the release lead's probe of the gate's verdict at three trees, each with its
     own code: with a `.gitattributes` file beside the document that the Git directory's
     exclude file hides, the prose gate passes at the release head and at the release head
     with decisions 1 to 5, and blocks at 0.2.0-beta.10. A second form of this Change copied
     the attribute files that Git lists into a directory and read them there. A model review of
     it found four more differences from Git: a link in a parent directory read a file outside
     the repository (a case shows it), a file that Git's status hides by an index flag, a file
     absent from a sparse checkout, and a directory name that is not UTF-8.
   - **Considered:** a repair for each of the four, which makes the product a second reader of
     which attribute files count. Reading the marks from the commit's tree alone, which ignores
     an attributes file that the author has written and not yet committed, so the format
     command would rewrite a vendored file in that window.
   - **Chosen because:** one owner already says what a worktree holds for a proof: the source
     binding builds a tree from the head and the worktree as Git would add it. The reading
     asks that owner for the head's tree with the worktree's `.gitattributes` files, and Git
     reads the marks against that tree with `--source`. So a mark counts exactly where the
     binding can see its file, no attributes file is read from disk by ETHOS, and the four
     differences have no place to arise. The owner gains one parameter that limits the paths
     it adds, so a large tree is not hashed for each selection.
   - **Applies to:** `worktree_received_paths` and `observe_worktree_postimage`. A name that
     leaves the tree receives nothing, and its own caller names it invalid. Without a head
     there is no tree, and nothing is received. Git refuses to add a pathspec that names no
     file, so the owner lists each pathspec first, as bytes, and adds only those that name one:
     a repository without an attributes file marks nothing and is refused nothing. The form
     before that listing ended every authored selection of such a repository with Git's error,
     which a third model review found and a case showed; a fourth found that the listing
     decoded a name that is not UTF-8.

## Risks / Trade-offs

- An untracked `.gitattributes` file that Git would add marks, as a tracked one does: a proof's
  source binding sees it, and the next commit can carry it. One that an exclude rule hides
  marks nothing.
- An edit of a tracked `.gitattributes` file that an index flag hides from Git's status
  counts. The source binding sees the same edit, so a proof refuses that worktree. A case
  holds both readings.
- A tracked `.gitattributes` file that is absent from the worktree, deleted or left out by a
  sparse checkout, gives no mark, so its paths are judged. The source binding refuses such a
  worktree. A sparse checkout was not run.
- A pattern that differs in case from its path marked the path on a volume that folds case and
  marks nothing now. A repository that relied on it sees those files judged.
- A refused read stops a check that the release head let judge everything.
- `git check-attr --source` needs Git 2.40 or later. The reading ran on Git 2.56.1 on macOS and
  on Python 3.12, 3.13 and 3.14. Windows and Linux run it in the hosted legs.
- A name that is not UTF-8 ran as an index entry on macOS, whose file system takes no such
  name. A file of that name on Linux was not run.
- Four model reviews each found a state that the cases did not hold, and a case showed each
  before its repair. A state that no review named may remain; the reading fails closed where
  Git refuses, and judges more where it differs from Git's own.
