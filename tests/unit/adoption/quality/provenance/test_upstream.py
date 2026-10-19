"""Verify locked upstream bytes without executing or extracting upstream code."""

from __future__ import annotations

import base64
import gzip
import hashlib
import importlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

import ethos.adapters.gates.provenance.observation as source_observation
import ethos.adapters.repo.content.observation as content_observation
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.repository.policy.quality.sources import locked_archive
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile


@pytest.mark.parametrize(
    "defect",
    [
        "none",
        "archive-bytes",
        "artifact-bytes",
        "duplicate",
        "link",
        "traversal",
        "no-integrity",
        "unsupported",
        "after-eof",
        "partial-header",
        "nested-gzip",
        "cache-multihash",
        "expanded-budget",
        "long-path",
        "metadata-budget",
        "input-budget",
        "raw-budget",
        "native-list",
        "native-unmatched",
    ],
)
def test_upstream_archive_qualification_uses_native_sri_and_complete_tar(
    tmp_path: Path, defect: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Versions and labels cannot substitute for complete authentic archive members."""
    repo = init_git_repo(tmp_path / "repository")
    content = b"import math\nVALUE = 42\n"
    member = (
        "package/" + "nested/" * 18 + "source.py"
        if defect in {"long-path", "metadata-budget"}
        else "package/source.py"
    )
    archive = repo / "upstream.tgz"
    original = _archive_data(archive, member, content, defect)
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(original).digest()).decode()
    metadata = {"version": "1.0.0", "resolved": "file:upstream.tgz"}
    if defect != "no-integrity":
        metadata["integrity"] = integrity
    if defect == "cache-multihash":
        metadata = _cache_metadata(tmp_path, archive, original, integrity, monkeypatch)
    (repo / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": {"node_modules/example": metadata}})
    )
    (repo / "snapshot.py").write_bytes(
        content if defect != "artifact-bytes" else content + b"# drift\n"
    )
    if defect == "archive-bytes":
        archive.write_bytes(original + b"changed")
        assert archive.read_bytes() != original
    reference = "package-lock.json#packages/node_modules/example"
    write_test_profile(
        repo,
        profile_id="example",
        proof={
            "gate_registry": "system/gates.toml",
            "source_contracts": [
                {
                    "kind": "upstream",
                    "input_refs": [reference],
                    "members": {"snapshot.py": [reference, member]},
                    "integrity_gate": "integrity",
                }
            ],
        },
    )
    commit_fixture(repo, "declare exact locked archive member")
    observer = importlib.import_module("ethos.adapters.gates.provenance.observation")
    budgets = {
        "expanded-budget": ("expanded_bytes", 512),
        "metadata-budget": ("metadata_bytes", 1),
        "input-budget": ("input_bytes", 1),
        "raw-budget": ("raw_bytes", 1),
    }
    if defect in budgets:
        key, value = budgets[defect]
        monkeypatch.setattr(
            observer, "_ARCHIVE_LIMITS", {**vars(observer)["_ARCHIVE_LIMITS"], key: value}
        )
    if defect in {"native-list", "native-unmatched"}:
        monkeypatch.setattr(
            observer,
            "run_command",
            lambda _root, command, **_options: subprocess.CompletedProcess(
                command, 0, "[]" if defect == "native-list" else '{"matched": []}', ""
            ),
        )
    report = observer.integrity_report(repo)
    if defect in {"none", "cache-multihash", "long-path"}:
        assert report["verdict"] == "pass", report
        observed = report["source_integrity"]
        assert isinstance(observed, dict)
        assert observed["members"] == {
            "snapshot.py": {"kind": "upstream", "input_ref": reference, "member": member}
        }
    else:
        assert report["verdict"] != "pass", report
        assert report["required_gaps"]
    if defect in {"input-budget", "raw-budget"}:
        assert report["diagnostics"] == [{"reason": "source_upstream_request_size_exceeded"}]
    if defect in {"native-list", "native-unmatched"}:
        assert report["diagnostics"] == [{"reason": "source_upstream_native_result_invalid"}]


def _archive_data(archive: Path, member: str, content: bytes, defect: str) -> bytes:
    with tarfile.open(archive, "w:gz") as stream:
        entry = tarfile.TarInfo(member)
        entry.size = len(content)
        if defect == "link":
            entry.type = tarfile.SYMTYPE
            entry.linkname = "outside"
            entry.size = 0
        stream.addfile(entry, io.BytesIO(content))
        if defect == "duplicate":
            stream.addfile(entry, io.BytesIO(content))
        if defect == "traversal":
            invalid = tarfile.TarInfo("package/../escape.py")
            invalid.size = 1
            stream.addfile(invalid, io.BytesIO(b"x"))
        if defect == "unsupported":
            invalid = tarfile.TarInfo("/outside.py")
            invalid.type = b"V"
            stream.addfile(invalid)
    original = _framing_mutation(archive.read_bytes(), defect)
    archive.write_bytes(original)
    return original


def _framing_mutation(original: bytes, defect: str) -> bytes:
    if defect not in {"after-eof", "partial-header", "nested-gzip"}:
        return original
    raw = gzip.decompress(original)
    if defect == "after-eof":
        raw += tarfile.TarInfo("package/../outside.py").tobuf()
    elif defect == "partial-header":
        raw = raw[:1024] + b"partial header"
    else:
        raw = original
    return gzip.compress(raw)


def _cache_metadata(
    root: Path, archive: Path, raw: bytes, integrity: str, monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    native = resolve_node_runtime()
    cache = root / "npm-cache"
    monkeypatch.setenv("npm_config_cache", str(cache))
    command = [
        str(native.executable),
        "-e",
        (
            "const r=require('node:module').createRequire(process.argv[1]);"
            "r('cacache').put(process.argv[2],'fixture',"
            "require('node:fs').readFileSync(process.argv[3]))"
            ".then(()=>{},e=>{console.error(e.message);process.exitCode=1})"
        ),
        str(native.npm),
        str(cache / "_cacache"),
        str(archive),
    ]
    subprocess.run(command, check=True, stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
    return {
        "version": "1.0.0",
        "resolved": "https://registry.example.test/example.tgz",
        "integrity": "sha256-"
        + base64.b64encode(hashlib.sha256(raw).digest()).decode()
        + " "
        + integrity,
    }


def test_local_archive_identity_is_relative_to_its_native_lock() -> None:
    """Normalize an in-repository parent reference without allowing root escape."""
    reference = "locks/package-lock.json#packages/node_modules/example"
    metadata = {"resolved": "file:../upstream.tgz", "integrity": "sha512-example"}

    def material() -> bytes:
        return json.dumps(
            {"lockfileVersion": 3, "packages": {"node_modules/example": metadata}}
        ).encode()

    assert locked_archive(reference, material()).archive_path == "upstream.tgz"
    metadata["resolved"] = "file:../../outside.tgz"
    with pytest.raises(ValueError, match="source_upstream_archive_outside_root"):
        locked_archive(reference, material())


@pytest.mark.parametrize("archive_count", [1, 2])
def test_native_archive_metadata_budget_is_shared_across_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, archive_count: int
) -> None:
    """One legal metadata body cannot reset the invocation's remaining budget."""
    repo = init_git_repo(tmp_path / "repository")
    packages = {}
    for number in range(archive_count):
        name = f"input{number}"
        archive = repo / f"{name}.tgz"
        content = b"native member\n"
        with tarfile.open(archive, "w:gz") as stream:
            entry = tarfile.TarInfo("package/source.py")
            entry.size = len(content)
            entry.pax_headers = {"comment": "c" * 300}
            stream.addfile(entry, io.BytesIO(content))
        raw = archive.read_bytes()
        packages[f"node_modules/{name}"] = {
            "version": "1.0.0",
            "resolved": f"file:{name}.tgz",
            "integrity": "sha512-" + base64.b64encode(hashlib.sha512(raw).digest()).decode(),
        }
    _write_source_relationships(repo, packages)
    observer = importlib.import_module("ethos.adapters.gates.provenance.observation")
    limits = dict(vars(observer)["_ARCHIVE_LIMITS"])
    limits["metadata_bytes"] = 512
    monkeypatch.setattr(observer, "_ARCHIVE_LIMITS", limits)
    report = observer.integrity_report(repo)
    if archive_count == 1:
        assert report["verdict"] == "pass", report
    else:
        assert report["verdict"] == "unknown", report
        diagnostics = report["diagnostics"]
        assert isinstance(diagnostics, list)
        assert "archive_metadata_budget_exceeded" in diagnostics[0]["reason"]


@pytest.mark.parametrize("selected_size", [1, 2])
def test_native_cache_growth_is_rejected_before_allocating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected_size: int
) -> None:
    """Native availability cannot authorize growth beyond selected or remaining bytes."""
    repo = init_git_repo(tmp_path / "repository")
    local = repo / "upstream.tgz"
    local_raw = _archive_data(local, "package/source.py", b"native member\n", "none")
    archive = tmp_path / "cache-input"
    raw = b"x" * selected_size
    archive.write_bytes(raw)
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(raw).digest()).decode()
    cached = _cache_metadata(tmp_path, archive, raw, integrity, monkeypatch)
    packages = {
        "node_modules/local": {
            "version": "1.0.0",
            "resolved": "file:upstream.tgz",
            "integrity": "sha512-" + base64.b64encode(hashlib.sha512(local_raw).digest()).decode(),
        },
        "node_modules/cached": cached,
    }
    _write_source_relationships(repo, packages)
    native_selections = []

    def select_then_grow(*args, **kwargs):
        result = run_command(*args, **kwargs)
        request = json.loads(kwargs["stdin"])
        assert request["select_cache"] is True
        assert result.returncode == 0, result.stderr
        selected = json.loads(result.stdout)["selected"][0]
        assert selected["size"] == selected_size
        native_selections.append(selected)
        Path(selected["path"]).write_bytes(b"xxxx")

        def forbidden_allocation(*_args, **_kwargs):
            pytest.fail("a grown cache object must be rejected before reading")

        monkeypatch.setattr(content_observation.os, "fdopen", forbidden_allocation)
        return result

    monkeypatch.setattr(source_observation, "run_command", select_then_grow)
    report = source_observation.integrity_report(repo)
    assert len(native_selections) == 1
    assert report["verdict"] == "unknown", report
    assert report["diagnostics"] == [{"reason": "archive_size_exceeded"}]


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("count", "source_upstream_native_selection_invalid"),
        ("identity", "source_upstream_native_selection_invalid"),
        ("budget", "source_upstream_request_size_exceeded"),
        ("shrunk", "archive_content_changed"),
    ],
)
def test_native_cache_selection_is_exact_bounded_and_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, reason: str
) -> None:
    """Only one exact selection within the remaining budget can supply unchanged cache bytes."""
    repo = init_git_repo(tmp_path / "repository")
    archive = tmp_path / "cache-input"
    raw = b"xx"
    archive.write_bytes(raw)
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(raw).digest()).decode()
    cached = _cache_metadata(tmp_path, archive, raw, integrity, monkeypatch)
    _write_source_relationships(repo, {"node_modules/cached": cached})

    def select(*args, **kwargs):
        result = run_command(*args, **kwargs)
        assert result.returncode == 0, result.stderr
        observed = json.loads(result.stdout)
        selected = observed["selected"]
        if fault == "count":
            selected.clear()
        elif fault == "identity":
            selected[0]["reference"] = "package-lock.json#packages/node_modules/other"
        elif fault == "budget":
            limits = vars(source_observation)["_ARCHIVE_LIMITS"]
            monkeypatch.setattr(source_observation, "_ARCHIVE_LIMITS", {**limits, "raw_bytes": 15})
        else:
            Path(selected[0]["path"]).write_bytes(b"x")
        return subprocess.CompletedProcess(result.args, 0, json.dumps(observed), result.stderr)

    monkeypatch.setattr(source_observation, "run_command", select)
    report = source_observation.integrity_report(repo)
    assert report["verdict"] == "unknown", report
    assert report["diagnostics"] == [{"reason": reason}]


def _write_source_relationships(repo: Path, packages: dict[str, dict[str, str]]) -> None:
    """Declare exact native lock relationships for the selected fixture inputs."""
    (repo / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": packages})
    )
    members = {}
    for location in packages:
        name = location.rsplit("/", 1)[1]
        artifact = f"{name}.py"
        (repo / artifact).write_bytes(b"native member\n")
        reference = f"package-lock.json#packages/{location}"
        members[artifact] = [reference, "package/source.py"]
    write_test_profile(
        repo,
        profile_id="example",
        proof={
            "gate_registry": "system/gates.toml",
            "source_contracts": [
                {
                    "kind": "upstream",
                    "input_refs": [reference for reference, _member in members.values()],
                    "members": members,
                    "integrity_gate": "integrity",
                }
            ],
        },
    )
    commit_fixture(repo, "bind selected native archive inputs")
