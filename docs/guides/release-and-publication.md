---
subject: ethos:guide:release-and-publication
role: how-to
state: active
relations:
  canonical_for: cutting an ETHOS release and activating a second Forge
---

# Release And Publication

Status: active.

Purpose: cut an ETHOS product release from accepted source, and add a second Forge to a repository's publication topology.

See also: [ETHOS source distribution specification](../../openspec/specs/distribution/spec.md "source-only") for versions, stages and release entries; [ETHOS source repository-governance specification](../../openspec/specs/repository-governance/spec.md "source-only") for publication topology and peers; [Release Rules](../../rules/release.md); and [Command Plane](../reference/command-plane.md).

## Cut A Release

1. **Open a release Change** in its own Work Lane. Move the product version in `VERSION`, its only carrier; no lock records it. Then curate the release entry in `CHANGELOG.md` from the Unreleased notes and every user-visible change since the previous tag. The distribution specification owns the version, stage and entry rules.
   Then commit both and record what the release upgrades from. `ethos lane upgrade-from --json`
   reads, offline, every repository that this host's store records as a consumer: the release it
   has selected and, where its accepted branch declares a pin, the pinned release and the time of
   its last landed bump. It derives the previous release and every release that a subject inside
   the support window names, each with its class. It counts the subjects by pin form and by
   selection alone, and it names no repository. It also counts what it could not read: consumers
   and records under `unread`, pins and selections that cannot be read, and installations that
   record no consumer; read those counts before trusting the set. Record each derived release under
   `[release.upgrade_from]` in `.ethos/release.toml`, as `"<version>" = "<class>"`, commit it, and
   run the command again until it passes. A subject frozen on its runtime takes no release: its
   waiver is [DR-0030](../decisions/dr-0030-candidate-subject-set.md), which names its shape and
   its runtime.
2. **Archive, prove and land.** Archive the Change with `ethos lane archive-change`, then prove the archived head once with `ethos prove --execute --full --expect-head <HEAD> --json`. If that proof fails, `ethos lane archive-change --compensate` returns the lane to its pre-archive head. Then land, close out and bootstrap the accepted root.
3. **Publish the branches.** Publish `dev`, then `main`, to each declared peer with `ethos publish --probe-remote --ref <ref> --peer <id> --expect-head <HEAD> --json`, followed by the receipt action it returns.
4. **Qualify the release head, then tag.** A push runs only the push tier of host conformance, and
   GitLab verifies a published ref by admission and conformance alone, so qualify the release head
   on both Forges before its tag. On GitHub, dispatch `ETHOS CI` on the release lane's proposal ref
   with `qualify_head` set to that head: every supported platform and Python version runs, and
   `hosted checks` reports the result. The same run repeats the test suite on Linux x64 at Python
   3.12 and 3.13, which `hosted checks` needs, and on Windows x64 at Python 3.14, which may fail
   without failing the run. On GitLab, start a `web` or `api` pipeline on the same ref
   with the variable `ETHOS_QUALIFY_HEAD` set to that head: the full gate set runs. A run at any
   other commit qualifies nothing: GitHub's run fails, and GitLab creates no pipeline. When both
   runs pass (the practised order; the distribution specification states what each stage requires),
   create the signed annotated tag: preview `ethos land --release --expect-head <accepted-head>
--release-head <main> --tag v<version> --json`, then apply it with `--apply --authorize`.
   Publish the tag with the same publish probe and receipt.
   In the repository that declares the ETHOS product profile, that probe refuses while the release
   policy holds a gap, such as a missing release file, an invalid version manifest, release tags
   other than `v*`, a missing host surface or an incomplete attestation format, and its next
   action names the repair. The probe reads the policy of the checkout and prints the report
   under `data.release_policy`, so run it while the checkout's head is the tagged commit. A
   governed repository's tag publishes under its role policy and topology, as before.
5. **Build the release.** Dispatch the hosted `ETHOS CI` workflow on `main` with its `release_tag` and `release_head` inputs. Verify the published assets. After publication, the run's `release-journey` job installs the published prerelease through Mise on macOS and Linux and runs the adopter journey that a beta needs; dispatch the workflow with `journey_tag` to run that journey alone for an already published prerelease. A beta's journey must also upgrade from every release that `[release.upgrade_from]` records: name them, comma-separated, in `journey_previous`, and the journey upgrades from and rolls back to each one in its own host store. Name in the release entry each journey that the target does not declare, or whose environment was unavailable.
   Then accept the release on the releasing host. Install the published release as the host's
   global `ethos` through the host's one global owner, download the release's `SHA256SUMS` and
   verify that file's attestation. From the accepted root, preview
   `ethos release accept --checksums <SHA256SUMS> --json` with that installation and run the apply
   that it returns. The acceptance records the release identity once, bound to the checksum file
   and every wheel and archive it lists; a second run changes nothing, and a refusal names its
   repair ([Operational Roots](../reference/operational-roots.md) lists them). A bad global
   release is undone by reinstalling the predecessor as the global `ethos`. Do that before the
   apply: an accepted identity is immutable.

## Activate A Second Forge

1. **Declare the peer** under `[[publication.peers]]` in `.ethos/release.toml`.
2. **Add its projection.** Add its `[[projection]]` and `[[forge_surface]]` entries in `.config/checks/ci-projection/policy.toml`.
3. **Write the generated files.** Preview and apply them with `ethos lane project`.
4. **Check them.** Run `uv run --frozen --offline python -m nox -s ci_templates`.
5. **Prove the head.** Run `ethos prove --execute --full --expect-head <HEAD> --json`.
6. **Observe the hosted run.** Record the hosted run with the `hosted_observation` Nox session in execute mode (`ETHOS_HOSTED_OBSERVATION_EXECUTE=1`) before claiming hosted success. Each Forge's hosted observation stays a separate proof plane.
