## Context

See [proposal.md](proposal.md). At accepted commit
`c9a32bfc54f0d8f01ca28549dd0ace3057c6bba9`, both GitLab exact-HEAD pipelines
and every GitHub macOS, Linux, and Windows Python matrix job reach the same
boundary: package-only hook activation runs from a lock-provisioned virtual
environment, `uv python find --managed-python` does not admit the runner's base
interpreter, and the resolver then calls `uv python install` while
`python-downloads = "never"` is in force. Quality gates pass independently;
the first failing owner is runtime interpreter resolution.

After resolving the base interpreter directly, real host conformance reached a
second boundary: strict offline dependency installation requested
`annotated-types==0.8.0` from a registry because the base interpreter does not
contain the invocation environment's installed packages. The failure exposed
the deeper model error. One Python path had been asked to own both the native
image and dependency bytes, while a Git-common uv cache had become an accidental
correctness prerequisite. Git history already contained the intended invariant,
but a later acceptance-owner refactor had removed its implementation.

After separating dependency supply, host conformance reached a third boundary:
the local virtual environment reported a Homebrew framework executable as its
base. That executable had the correct Python identity but loaded the framework
from an absolute Cellar path, and its standard library contained a package-tree
link outside the framework root. Copying it therefore could not create an
immutable relocatable image. An already-installed standalone interpreter with
the same identity did have a prefix-relative native layout. This proved that
base ancestry is a candidate relation, not image capability.

## Goals / Non-Goals

**Goals:**

- define interpreter eligibility from observed Python identity and filesystem
  closure rather than installer provenance;
- preserve four distinct authorities: lock selection, invocation-environment
  dependency bytes, admitted native-image bytes, and the sealed runtime;
- make cache state irrelevant to activation correctness and reuse one
  dependency-supply owner in runtime materialization and package acceptance;
- support ordinary source and installed-package virtual environments on native
  macOS, Linux, and Windows runners;
- require hosted toolchain owners to establish one exact native-image supply
  before invoking package-only activation;
- preserve an entirely offline materialization phase and exact immutable
  runtime post-observation;
- remove the unreachable Python-install fallback and duplicate delivery supply.

**Non-Goals:**

- no CI-provider condition inside runtime activation, environment-variable
  escape, PATH fallback, network retry, Python-version relaxation, wheelhouse,
  or second cache;
- no change to dependency selection, wheel identity, runtime digest, selector,
  hook/state activation transaction, or supported Python versions;
- no unrelated repository-layout, temporary-resource, or lane-lifecycle work.

## Decisions

### Interpreter provenance is an observed relation, not a package-manager brand

The invoking executable is already selected by the caller's locked execution
boundary. ETHOS asks that executable for its executable, base executable,
prefix, base prefix, ABI, version, implementation, architecture, and native
layout facts. Its reported base is the first candidate, not an authority. ETHOS
admits it only when a second observation proves the same runtime identity, a
direct independent prefix, and a copyable platform-native image layout.

If that first candidate lacks image capability, the authenticated invoking
Python runs the locked uv module only to enumerate already-installed
interpreters with network, downloads, cache writes, and project configuration
disabled. ETHOS sorts the candidate paths, observes each candidate itself, and
admits the first one satisfying the same identity and image-capability
contract. uv's listing supplies candidate facts; it neither grants authority
nor selects the result. A directly invoked admissible interpreter avoids this
fallback entirely.

Requiring `uv-managed` provenance was rejected because the generated ETHOS
runtime does not retain or depend on uv's installation metadata. It caused
identical, valid runner interpreters to fail solely because another installer
provided them.

### Ownership begins at the generated image boundary

The source interpreter remains an external, read-only construction input.
ETHOS ownership begins only after its native runtime files are copied into the
Git-common staging generation, dependencies and the exact wheel are installed,
the payload is sealed, the manifest and runtime digest are computed, and the
new executable reports the generated root as both prefix values.

Calling the source interpreter “owned” before that transition was rejected: it
confused provenance with lifecycle ownership and motivated the unnecessary
managed-Python installation path.

### Dependency selection, byte supply, and image supply are separate

`uv.lock` remains the only dependency-selection authority. Before any runtime
generation is built, the invoking Python runs the locked uv module to check its
active environment against that lock and export one hashed production
requirements file. That environment, not uv cache state, supplies the installed
distribution bytes.

The admitted congruent interpreter supplies only the native Python image. The
dependency-supply owner validates that source and target observations have the
same ABI, version, implementation, and architecture; rejects aliases,
out-of-prefix files, symlinks, and observed hash drift; copies the observed
distribution files; then runs strict hash-required offline sync against the
exported requirements and installs the exact ETHOS wheel with `--no-deps`.

Package acceptance consumes the same owner. Its former delivery-specific
installer and cache path are deleted rather than retained as a facade or
fallback.

### Cache is not an authority

Runtime materialization disables persistent uv cache use. Cache may help the
external process that originally provisioned the invoking environment, but it
does not select the closure, supply activation bytes, or appear in runtime
identity. An empty or unrelated cache therefore cannot change a valid
activation result.

### Host toolchain provisioning precedes activation

Runtime activation consumes an already-installed image source; it does not own
networked interpreter acquisition. The hosted CI template is the existing
owner of provider-native toolchain preparation. GitHub host-conformance jobs
therefore use the pinned setup-uv action to select the matrix version, install
that version into one job-scoped `UV_PYTHON_INSTALL_DIR`, and only then create
the lock-current project environment. GitLab host conformance consumes the
direct, prefix-contained Python supplied by the digest-pinned uv/Python image.

These are native projections of one prerequisite, not product branches: before
activation begins, a congruent image candidate must already exist and remain
discoverable by the authenticated invoking Python. The activation resolver
still performs the same observation and admission on every provider and never
trusts a CI declaration by itself.

### Failure is bounded and leaves no published effect

If neither the reported base nor any already-installed candidate has the
required identity and native-image capability, resolution fails with the
existing interpreter-unavailable boundary before creating a runtime generation.
Candidate discovery never installs or downloads Python. A lock-current check
fails before wheel or generation construction.
Dependency-supply validation fails before incompatible bytes are copied; any
later failure remains inside the owned staging generation, which the enclosing
runtime or package-acceptance transaction removes. There is no fallback
installation or network retry.

### Native path identity has one Python-environment owner

Python prefix comparison and runtime-identity congruence belong with Python fact
observation. Runtime post-observation, interpreter-source validation, and
dependency-supply validation consume those same relations, avoiding competing
interpretations of ABI identity or Windows case and separator equivalence.

## Risks / Trade-offs

- **A Python distribution reports an unusable base executable** → enumerate
  already-installed candidates through the authenticated locked tool, admit
  only a congruent copyable image, and otherwise fail before effects.
- **macOS framework or Windows path aliases differ textually** → compare native
  normalized identity and require the resolved executable to remain inside the
  observed base prefix.
- **An identity-congruent distribution cannot be copied into a relocatable
  image** → reject it as an image source; image construction and
  post-observation remain fail-closed and no provenance label overrides them.
- **The invoking environment is not lock-current** → fail before exporting,
  building the wheel, or creating a generation; do not repair the environment.
- **Installed dependency bytes are symlinked, outside their prefix, changed
  after observation, or target a different Python identity** → reject the
  supply and let the enclosing staging transaction remove any partial copy.
- **A selected immutable ETHOS runtime upgrades itself** → the same observed
  relation admits its independent runtime Python and reuses its validated
  package closure; wheel, lock, and source identity checks remain unchanged.
- **A hosted runner exposes only a framework or otherwise non-copyable Python**
  → its toolchain projection provisions the exact requested standalone image
  before environment synchronization; activation still rejects absent or
  incapable candidates rather than downloading one.

## Migration Plan

1. Add RED contracts proving a virtual environment prefers a congruent,
   copyable base, falls back only to already-installed congruent images, and
   fails without installation when no candidate qualifies.
2. Extend Python fact observation with executable and native-layout identity,
   move Python path equality to that owner, and make image selection a
   capability-first relation rather than managed-Python provenance.
3. Add RED contracts separating dependency supply from image supply; restore
   lock-current environment projection, strict offline pruning, and exact wheel
   installation as one shared owner.
4. Delete installation expectations, delivery-specific supply, cache authority,
   and every active materialization reference to `uv python install`; retain
   only read-only installed-candidate enumeration as a bounded fallback.
5. Add a hosted-projection contract requiring native image provisioning before
   package-only activation, project it to GitHub and GitLab through their
   existing template owners, and keep provider syntax outside product code.
6. Prove focused runtime tests, package-only host conformance, strict OpenSpec,
   quality gates, exact-HEAD proof, archive/reproof, candidate/accepted CAS,
   immutable runtime readback, and both hosted CI planes.
