# Design

## Context

The release journey qualifies one published prerelease on each declared host. At the base its
children get their environment in two ways. A child that is handed one receives the install
smoke's minimal environment: on the preparing host that is `HOME`, `PATH`, `TMPDIR` and `USER`,
with a path of the two whole directories that hold Git and the signing tool. Those directories
hold 1,643 and 934 entries there, so that many names resolve for a child. A child that inherits
receives everything: the forge's client, the Git commands that build the fixture adopters, the
Git initialization of each Mise project, and the reads of Mise's version. The preparing host's
environment holds 139 variables. The figures were measured there on 2026-11-15 by calling the
base's `independent_host_environment` and counting the entries of the two directories on the
path it returns.

The forge token had two paths: the forge's client inherited it, and the Mise helper read it from
the process environment for a pin's lock and install. The product's own Git adapter copies every
variable that is not a Git variable into its children, so a token in the process reaches them too.

Network use was spread over the journey: the prerelease was downloaded, locked and installed
first, and each predecessor was locked and installed from the forge between the upgrade steps.

The archived `rc-plan` design, appendix B.5, names the remedy. This Change implements it for the
journey and leaves a proof's gates to the `gate-environment` row.

## Goals / Non-Goals

Goals:

- Every child of the journey receives one declared environment, whether it inherits it or is
  handed it.
- The network is reached in one stage, whose output is a manifest of verified archives.
- Qualification depends on that manifest alone, checks its own environment before its first
  child, and installs only bytes that still match.
- The forge token reaches the two kinds of child that need it and no other.

Non-Goals:

- Counting a venue toward qualification, and signed local receipts. The receipt records the venue
  and nothing reads it.
- Windows beyond the Git variables. No journey leg runs there.
- Binding Git, the signing tool, the forge's client or the downloader by identity. The links name
  what the launcher's path resolves; `gate-environment` owns that question.
- A network sandbox. Qualification is offline by construction, as decision 6 says.
- The install smoke, which keeps its minimal environment.

## Decisions

1. **One owner replaces the process's environment for the length of a stage.**
   - **Rests on:** the inheriting children listed in the context. Three of them start inside
     functions that take no environment: the read of Mise's version, the preparation of the Mise
     executable, and the product's read of the Git common directory.
   - **Considered:** handing a mapping to every call, which cannot reach those three without
     changing product signatures; and running each stage as a subprocess with an empty
     environment, which needs a new entry point and carries the receipt and the stage events
     across a process boundary.
   - **Chosen because:** one place decides what every child sees, and a child that inherits and
     one that is handed the mapping see the same thing. The cost is a change to process state: a
     stage must not share its process with other threads, and the host's environment returns
     in a `finally` block.
   - **Applies to:** the journey's two stages. The owner also resets Python's remembered
     temporary directory on both sides, or a later caller in the same process would be given a
     directory that the journey removed.
2. **The declared environment is seven variables and a path of links.**
   - **Rests on:** appendix B.5's list. A child of the new owner on the preparing host shows the
     seven declared variables and two that its own runtime adds, `LC_CTYPE` and
     `__CF_USER_TEXT_ENCODING`; a child of Git through its link runs. The hook launcher uses
     shell builtins and an absolute interpreter (`src/ethos/adapters/repo/hook/binding.toml`),
     and the product finds its process and open-file tools on the system's default path, so no
     product child needs a neighbor of Git.
   - **Considered:** keeping the two directories, which keeps every neighbor in reach; and
     copies in place of links, which break an executable that finds its own files beside itself.
   - **Chosen because:** a link gives a child the declared name and nothing beside it. The
     global Git configuration is an empty file under the owner's root, not the null device, so a
     write to it can be seen. Mise is not on the path: the journey calls the executable of the
     repository's tool supply by its absolute path, and that executable is bound by digest.
   - **Applies to:** POSIX hosts. On Windows the owner adds the Git variables to the install
     smoke's minimal environment and links nothing; its path also names the directory of each
     declared executable, since the minimal path holds Git and the signing tool alone and the
     forge's client is installed elsewhere. The journey's own `XDG_DATA_HOME`, which
     gives each upgrade its own host store under the work tree, stays: B.5 excludes the host's
     desktop variables, and this one is the product's declared input for the store's place.
3. **The forge token is handed to two kinds of child and inherited by none.**
   - **Rests on:** the two paths in the context. With the token in acquisition's process, five
     children would inherit it: the forge's client, two reads of Mise's version, the downloader
     and the product's Git read.
   - **Considered:** keeping it in the process and removing it call by call, which the product's
     calls cannot do; and one mapping that carries it, which hands it to Git as well.
   - **Chosen because:** the journey reads the token once, before the first stage, and the stage
     never holds it. The forge's client receives it as one added variable, and Mise receives it
     for a pin's lock and install as before. The cost is one parameter on ten signatures.
   - **Applies to:** acquisition. Qualification has no token to hand. Acquisition's process
     holds three variables that say where the host's tool supply is only while it prepares
     Mise from that supply. The commands of that preparation can read them, no later child
     can, and none is a credential. The first form of this Change kept them for the whole
     stage, where the forge's client inherited them.
4. **Acquisition proves the pins; the steps run on offline installs of the acquired archives.**
   - **Rests on:** B.5, which has qualification hash again before each install. Mise's lock and
     locked install of the pin reach the forge. The install smoke already installs a local
     archive offline from a local table in the pin's layout, through `install_archive`.
   - **Considered:** running the steps on the pin's installation, which leaves nothing to hash
     before an install and makes qualification depend on a Mise home that the networked stage
     wrote; and an offline install of the pin from Mise's download cache, which depends on that
     cache's layout and is unproven.
   - **Chosen because:** the bytes the steps run on are the bytes the manifest names: the
     journey hashes the archive again, and Mise is given the manifest's digest as the
     archive's checksum, so it refuses bytes that change after that check. The cost
     is that each release is installed twice, and that the console and the uninstall are
     exercised on the local table's installation. The pin's installation is checked for its
     console in acquisition and then removed as a tree, not through Mise.
   - **Applies to:** a release whose archive names its runtime directory with 16 digits, which
     `CHANGELOG.md` dates to 0.2.0-alpha.24. An older predecessor is refused by the archive
     reader with `shared_supply_generation_ambiguous`.
5. **The manifest is a file that qualification reads strictly.**
   - **Rests on:** the five fields of `PublishedRelease`. The release rehearsal, a later row,
     supplies its own archives to the same stage.
   - **Considered:** passing the releases in memory, which gives a later caller no input to
     write; and signing the manifest, which the plan puts out of scope.
   - **Chosen because:** a file is an input that another stage can produce. The reader refuses
     one that is absent, unparsable or empty, an entry with a missing or added field, and an
     archive outside the manifest's directory.
   - **Applies to:** one journey process and its work tree. The manifest is not authenticated:
     it guards against a change by accident or by a child, not against a writer who can replace
     the manifest and the archive together.
6. **Qualification checks its environment before its first child, by reading it back.**
   - **Rests on:** B.5's refusal, `journey_environment_not_hermetic:<what>`, and 13 cases in the
     owner's test.
   - **Considered:** the same check in acquisition, whose first children, the preparation of
     Mise, are shown the three supply variables; and a network sandbox, which differs by
     platform and is not in the plan.
   - **Chosen because:** the check reads the process environment and the directories, not the
     owner's intent, and names the first variable, directory or path entry that differs.
   - **Applies to:** the moment before the first child. After it, children write to the home
     and the temporary directory as they must. Qualification is offline because its path holds
     no client of the forge, no child holds a token and Mise runs in offline mode; a child that
     opened a connection by itself would not be stopped.
7. **The venue is `ci` or `local`, read from the declared `CI` input.**
   - **Rests on:** `system/surfaces.toml`, which declares `CI`, and the product-boundary test,
     which refuses a tool that reads an environment name that file does not declare.
   - **Considered:** a forge's runner-kind variable, which needs a new declared input in a
     shared file; and an option that the operator sets, which records an assertion.
   - **Chosen because:** it is the smallest reading that separates a runner from a local host.
   - **Applies to:** the receipt's `venue` key. A self-hosted runner reads `ci` as well. Only
     the values `true` and `1` read `ci`, as both forges' runners set the input; a host that
     exports `CI=false` is local.

## Risks / Trade-offs

- Nothing in this Change's preparation ran Mise, the forge's client or a full proof. The unit
  tests replace them. The first real run is a journey dispatch, which the tasks name; until then
  the claim that every child finds what it needs rests on the reading in decision 2.
- A child loses `USER` and `UV_PYTHON_INSTALL_DIR`, which the minimal environment passed on. No
  product module reads `USER`, and pinning an installed runtime copies its tree and starts no
  package installer; a gate of the fixture adopter that needed either would fail the leg.
- A host that reaches the forge through a proxy cannot run acquisition: no proxy variable is
  forwarded. Mise's forge calls had none before either.
- A host now needs the forge's client and a downloader on its path even where the Mise supply is
  present, because the links are made before the stage knows.
- The tests of the owner are skipped on Windows, so its Windows branch is unverified. One test
  replaces the owner's view of the operating system to read that branch's path; nothing runs
  it on Windows.
- Each release is installed twice. The time is unmeasured; the tasks ask the dispatch to read it.
