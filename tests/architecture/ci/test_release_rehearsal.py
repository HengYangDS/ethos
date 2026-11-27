"""A rehearsal builds, assembles and qualifies a release head before its tag, and writes nothing."""

from __future__ import annotations

from typing import Any

HEAD = (
    "github.event_name == 'workflow_dispatch' && inputs.rehearse_head != ''"
    " && inputs.rehearse_head == github.sha"
)
LEGS = ("rehearsal-platforms", "rehearsal-assets", "rehearsal-journey")
READ_ONLY = {"contents": "read", "attestations": "read"}


def test_a_rehearsal_runs_at_the_dispatched_head_and_in_order(github: dict[str, Any]) -> None:
    jobs = github["jobs"]
    platforms, assets, journey = (jobs[name] for name in LEGS)
    assert platforms["if"] == f"${{{{ {HEAD} }}}}"
    assert (assets["needs"], assets["if"]) == (LEGS[0], f"${{{{ !cancelled() && {HEAD} }}}}")
    assert journey["needs"] == LEGS[1]
    succeeded = "needs.rehearsal-assets.result == 'success'"
    assert journey["if"] == f"${{{{ !cancelled() && {HEAD} && {succeeded} }}}}"
    # The verdict also runs for a dispatch whose head is not the ref's, where no leg ran.
    verdict = jobs["release-rehearsal"]
    assert verdict["needs"] == ["hosted-checks", *LEGS]
    named = "github.event_name == 'workflow_dispatch' && inputs.rehearse_head != ''"
    assert verdict["if"] == f"${{{{ always() && ({named}) }}}}"
    # It writes no receipt: one expression over the jobs it needs is the whole verdict.
    succeeded = " && ".join(f"needs.{name}.result == 'success'" for name in verdict["needs"])
    (step,) = verdict["steps"]
    assert step["env"] == {"REHEARSED": f"${{{{ {succeeded} }}}}"}
    assert step["run"] == 'test "$REHEARSED" = true'
    declared = github["on"]["workflow_dispatch"]["inputs"]["rehearse_head"]
    assert (declared["type"], declared["default"], declared["required"]) == ("string", "", False)


def test_a_rehearsal_leg_is_the_release_leg_but_for_its_source(github: dict[str, Any]) -> None:
    """One declared job builds both: the checkout and the two build requests alone differ."""
    release, rehearsal = (github["jobs"][name] for name in ("release-platforms", LEGS[0]))
    assert rehearsal["strategy"] == release["strategy"]
    pairs = zip(release["steps"], rehearsal["steps"], strict=True)
    differing = {
        index: sorted(key for key in {*ours, *theirs} if ours.get(key) != theirs.get(key))
        for index, (ours, theirs) in enumerate(pairs)
        if ours != theirs
    }
    assert differing == {0: ["with"], 8: ["name", "run"], 9: ["run"]}
    steps = rehearsal["steps"]
    assert steps[0]["with"]["ref"] == "${{ github.event.pull_request.head.sha || github.sha }}"
    request = "-- --release --rehearse --expect-head ${{ github.sha }}"
    for index, session in ((8, "build"), (9, "install_smoke")):
        assert steps[index]["run"] == f"uv run --frozen python -m nox -s {session} {request}"


def test_a_rehearsal_reads_and_writes_nothing(github: dict[str, Any]) -> None:
    """A rehearsal job reads contents and attestations at most, and no input reaches a script."""
    assert github["permissions"] == {"contents": "read"}
    for name in (*LEGS, "release-rehearsal"):
        job = github["jobs"][name]
        assert set(job.get("permissions", {}).items()) <= set(READ_ONLY.items()), name
        assert "environment" not in job, name
        for step in job["steps"]:
            assert "${{ inputs." not in str(step.get("run", "")), (name, step.get("name"))
            assert not str(step.get("uses", "")).startswith("actions/attest"), name


def test_a_journey_leg_takes_its_own_archive_and_the_assembly_checksums(
    github: dict[str, Any],
) -> None:
    """Each declared journey host downloads its build leg's upload and the small assembly files."""
    journey, assets = (github["jobs"][name] for name in (LEGS[2], LEGS[1]))
    assert journey["strategy"]["matrix"]["host"] == ["linux-x64", "linux-arm64", "macos-arm64"]
    home = "build/release/rehearsal"
    taken = [
        step["with"] for step in journey["steps"] if "download-artifact" in step.get("uses", "")
    ]
    assert taken == [
        {"name": "release-runtime-${{ matrix.host }}", "path": home},
        {"name": "rehearsal-assets", "path": home},
    ]
    runs = [step["run"] for step in journey["steps"] if "release_journey" in step.get("run", "")]
    assert runs == [f"uv run --frozen python -m nox -s release_journey -- --rehearse {home}"]
    # The archives stay in the build legs' uploads: only the files that admit them travel.
    sent = assets["steps"][-1]["with"]
    assert sent["name"] == "rehearsal-assets"
    assert sent["path"].split("\n") == [
        "build/release/out/assets/SHA256SUMS",
        "build/release/out/assets/ethos-*.mise.toml",
    ]
