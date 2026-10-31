# Design

## Context

The paradigm contract's `[size]` table (`src/ethos/contracts/paradigm/paradigm.toml`) holds two
per-file ceilings, `python_effective_lines` and `markdown_nonblank_lines`, each 500 by default with
a bound of 1000, and `.ethos/rules.toml` `[paradigm.size]` may declare a repository's own value
(`src/ethos/repository/paradigm/size.py`). The paradigm report measures every tracked `.py` file
with the syntax-tree measure in `src/ethos/measure.py`, received files included, and docs health
measures current authored documents. No other language is measured.

Two governed repositories measure their own language at 512: aigw-cli counts Go with scc
(`tools/ci/size.go`) and architecture-publisher binds ESLint `max-lines`. The names obligation keeps
its own language list, `[names] module_suffixes = [".go", ".py", ".pyi"]`, so module files and the
directories that hold them keep the names their toolchain fixes. Rust, whose module names Cargo
derives from file paths, is missing from that list.

Pygments 2.21.0 is in ETHOS's runtime closure through Cyclopts and Rich. The per-file-ceiling design
(decision 5) compared it with scc: all 721 Go files of aigw-cli agree, and 5 of 107 JavaScript and
TypeScript files differ by at most 3 lines, none flipping a verdict at 500.

## Goals / Non-Goals

**Goals:**

- Every authored code file of every governed repository stays within one code ceiling, whatever its
  language.
- One registry owns the language facts, and every obligation that needs them reads it.
- The measure is a pure function of tracked bytes and the locked Pygments release.
- A repository's own value follows the existing law; no value applies to a language, path or file.

**Non-Goals:**

- Data and configuration carriers (TOML, JSON, YAML, CUE, locks), media and archives.
- Which formatter judges a suffix; the formatter table keeps that.
- Retiring aigw-cli's `size.go` and architecture-publisher's `max-lines` binding. Each repository
  retires its copy in its own Change after it rebinds.
- Changing which Markdown documents docs health measures.

## Decisions

### 1. One definition of an effective line

An effective line is a physical line that holds at least one token that is not whitespace, a comment
or documentation. Preprocessor directives, Rust attributes and shebangs are code: Pygments types
them `Comment.Preproc`, `Comment.PreprocFile` and `Comment.Hashbang`, and they carry meaning.

- Python keeps its syntax-tree measure. Only the syntax tree tells a docstring from a string value.
- Every other language uses the Pygments lexer that its registry entry names, selected by name, not
  guessed from content, with `stripnl` and `ensurenl` off so that lines stay physical lines.
  `Comment` tokens other than the three code kinds, `String.Doc` and whitespace do not count. A
  lexer's `Error` token counts, so an unrecognized construct can only raise a count.
- A file that is not UTF-8, or Python that does not parse, cannot be measured and is a gap.

### 2. One language registry

The contract gains `[[language]]` entries: an id, its suffixes, its measure (`python-syntax`, or
`lexer` with the Pygments lexer name), `module_names`, which says that the language's toolchain
fixes the names of its module files and of the directories that hold them, and `script`, which marks
the languages whose files conform only as a catalogued generator's recorded output. Shell,
PowerShell and batch carry `script`.

| Language   | Suffixes               | Lexer        | Module names |
| ---------- | ---------------------- | ------------ | ------------ |
| python     | `.py`, `.pyi`          | syntax tree  | yes          |
| go         | `.go`                  | `go`         | yes          |
| rust       | `.rs`                  | `rust`       | yes          |
| javascript | `.js`, `.mjs`, `.cjs`  | `javascript` | no           |
| jsx        | `.jsx`                 | `jsx`        | no           |
| typescript | `.ts`, `.mts`, `.cts`  | `typescript` | no           |
| tsx        | `.tsx`                 | `tsx`        | no           |
| css        | `.css`                 | `css`        | no           |
| scss       | `.scss`                | `scss`       | no           |
| html       | `.html`, `.htm`        | `html`       | no           |
| shell      | `.sh`, `.bash`, `.zsh` | `bash`       | no           |
| powershell | `.ps1`, `.psm1`        | `powershell` | no           |
| batch      | `.bat`, `.cmd`         | `batch`      | no           |
| sql        | `.sql`                 | `sql`        | no           |

The rows cover every code language that the governed repositories and the deferred di-effect and
alphasim track, and their dialects. A census of every path tracked on the `dev` branches of the ten
governed repositories, and on di-effect's and alphasim's current branches, found no other
programming language: the remaining suffixes are documents, data and configuration, notebooks,
media, archives, test data, subtitles and diagram sources. A language a repository adopts later is
one row and a fleet preview in a base Change. A language without a row is not measured, so the
preview is where it becomes visible.

- The size obligation measures a file when one row lists its suffix.
- The names obligation keeps the names of module files and their directories for the rows with
  `module_names`; `[names] module_suffixes` is removed. Rust gains what Python and Go have.
- The scripts obligation recognizes a script by the suffixes of the rows with `script`, or by its
  interpreter line; `[scripts] suffixes`, which listed exactly those suffixes, is removed.
- HTML, CSS and SCSS count as code: markup and style grow in one file as code does, and a generated
  page is marked generated.

### 3. Two ceilings keyed by class

`code_effective_lines` bounds every registered code file, tests and tools included.
`document_nonblank_lines` bounds the current authored documents that docs health selects. Both keep
the default 500, the bound 1000 and the law of the per-file-ceiling design: a lower value applies; a
higher one applies within the bound with a reason in `[paradigm.size.reasons]` and is reported as a
deviation; a restated default, a higher value without a reason, a value above the bound, a value
that is not a positive integer and an unknown key are gaps that leave the default in force.

- Rejected: one key per language. A repository's difference comes from its purpose, not its
  language. A key per language would grant capacity by class of file, which DR-0012 rules out, and
  would need a new key for every new language.
- `document_nonblank_lines`, not `prose_nonblank_lines`: the class is docs health's current authored
  documents, reported as `docs_length_exceeded`, and the prose gate keeps its own name.

### 4. The 0.2.0-alpha.22 keys are retired, not aliased

A declaration of `python_effective_lines` or `markdown_nonblank_lines` is a `size-declaration` gap
whose repair names the class key, and the default stays in force, as for the retired
`[quality.code_size]` table. An alias would keep two names for one value. No governed repository
declares either key: the 0.2.0-alpha.22 notice asked owners to split files rather than declare a
value.

### 5. Received files leave the measurement

A path that Git attributes mark `linguist-vendored` or `linguist-generated` is received, and the
names obligation already keeps its name. The code ceiling no longer measures it either, Python
included: the ceiling bounds what a repository authors. Marking an authored file received misstates
it in the repository's own `.gitattributes`, where review sees it.

### 6. The obligation is `code-size`

The gap names the obligation, not the language: `repository_paradigm_code_size:<path>`. Its repair
is to split the file by semantic ownership into a subdirectory of modules, each within the effective
ceiling: the subdirectory names the subject, and each module one responsibility. Flat siblings that
differ only by a suffix, such as `film-scenes.js` beside `film-labels.js`, or numbered parts, move
the lines without the structure. An unmeasurable file has the repair to make it readable UTF-8, or
parsable Python. Deciding the layout itself, for every file and not only a split one, belongs to the
semantic-layout obligation that a later Change adds to the base.

### 7. Pygments is a declared dependency

The measure imports Pygments directly, so `pyproject.toml` declares it, at the locked 2.21.0 floor.
Installed ETHOS already carries it; adopters need no tool supply. A Pygments release can move a
count, and it reaches a repository only through a dependency move that the proof and the fleet
preview judge. The lock is an input of the GitLab supply image, so the image is rebuilt and bound in
a follow-up binding Change, as for 0.2.0-alpha.22.

### 8. Values follow the running package

A governed repository meets the code ceiling when it rebinds to the release that carries this
Change; until then its installed ETHOS judges only its Python files.

## Risks / Trade-offs

- **Fleet impact.** The preview measured every registered code file on each governed repository's
  `dev` with this Change's measure
  (`build/runtime/work/cross-language-size/fleet-preview-500.json`). 23 files in other languages
  exceed 500 effective lines:

  | Repository                | Files                     | Largest                                          |
  | ------------------------- | ------------------------- | ------------------------------------------------ |
  | `aigw-cli`                | 10 Go tests, 501 to 509   | `internal/domain/model_test.go` 509              |
  | `architecture-publisher`  | 2 JavaScript, 511 each    | `packages/publisher/src/poster/compose.mjs`      |
  | `ddwg-film`               | 1 JavaScript              | `picture/film.js` 6413                           |
  | `ethos-introduction-film` | 1 TypeScript              | `src/motion/introduction.ts` 869                 |
  | `filmkit`                 | 4 JavaScript, 580 to 1359 | `tests/picture/picture.test.mjs` 1359            |
  | `ddwg-introduction-film`  | 5 JavaScript, 580 to 6413 | `src/ddwg_film/picture/composition/film.js` 6413 |

  ETHOS (876 measured files), architecture-publications, DDWG, openai-responses-proxy (whose four
  Python files above 500 0.2.0-alpha.22 already reports) and web-ingestion-benchmark have none in
  other languages. `film.js` needs real module boundaries, a subdirectory of modules by
  responsibility; a reasoned repository value cannot exceed 1000. `ddwg-introduction-film` is headed
  for a private archive.

- **Lexer precision.** A lexer is not a parser: a misread construct can shift a count. The
  comparison with scc bounds the observed difference at 3 lines, and an `Error` token only adds.
- **Unregistered languages.** A language without a row is unmeasured until a base Change adds it.
  Today's census finds none.
- **Proof cost.** Lexing aigw-cli's 729 code files takes about 3 seconds in the proof's audit.
  `ethos status` does not run the paradigm report.
- **Supply image.** The lock change invalidates the GitLab supply image until the binding Change
  lands, as in 0.2.0-alpha.22.
