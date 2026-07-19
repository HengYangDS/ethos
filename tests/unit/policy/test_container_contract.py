from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ethos.repository.policy.container_contract import core as container_contract
from ethos.repository.policy.container_contract.core import _contained_file
from ethos.repository.policy.container_contract.core import _evidence_gaps
from ethos.repository.policy.container_contract.core import _output_schema_gaps
from ethos.repository.policy.container_contract.core import _schema_gaps
from ethos.repository.policy.container_contract.core import container_contract_report
from ethos.repository.policy.schema import schema_validation_report

_FIXTURE = Path(__file__).parents[2] / "fixtures" / "container-contract"
_CASES = json.loads((_FIXTURE / "cases.json").read_text(encoding="utf-8"))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _profile(extra: str = "") -> str:
    return (
        'profile_id = "container-contract-test"\n\n'
        '[openspec]\nmaterial_paths = [".ethos/profile.toml"]\n'
        f"{extra}"
    )


def _manifest(digest: str) -> str:
    return f'''schema_version = 1
[delivery]
platforms = ["linux/amd64", "linux/arm64"]
emulation_is_release_evidence = false
oci_image_index = {{ reference = "registry.example/platform/example:v1", digest = "sha256:{"0" * 64}", evidence = {{ path = "evidence/container.json", sha256 = "{digest}" }} }}
sbom = {{ path = "evidence/container.json", sha256 = "{digest}" }}
provenance = {{ path = "evidence/container.json", sha256 = "{digest}" }}
signature = {{ path = "evidence/container.json", sha256 = "{digest}" }}
native_linux_smokes = [{{ platform = "linux/amd64", evidence = {{ path = "evidence/container.json", sha256 = "{digest}" }} }}, {{ platform = "linux/arm64", evidence = {{ path = "evidence/container.json", sha256 = "{digest}" }} }}]

[development]
compose_interface = "required"
native_development_path = "required"
dev_container = "optional"

[trust_profiles]
trusted = {{ network = "declared", credential_mounts = "declared", host_mounts = "declared", privileged = "forbidden", execution_evidence = {{ path = "evidence/container.json", sha256 = "{digest}" }} }}
untrusted = {{ network = "none", credential_mounts = "forbidden", host_secret_mounts = "forbidden", host_mounts = "forbidden", readonly_rootfs = true, capabilities = "drop_all", privileged = false, input_mount = "readonly", execution_evidence = {{ path = "evidence/container.json", sha256 = "{digest}" }}, artifact_return = {{ mode = "allowlist", allowed_paths = ["artifacts/result.json"], output_schema = {{ path = "evidence/container.json", sha256 = "{digest}" }} }} }}

[data_lifecycle]
migration = "required"
seed = "required"
backup = "required"
restore = "required"

[asset_inventory]
complete = true
assets = []
'''


def test_undeclared_container_contract_is_advisory(tmp_path: Path) -> None:
    report = container_contract_report(tmp_path)

    assert report["ok"] is True
    assert report["state"] == "not_declared"
    assert report["required_gaps"] == []
    assert report["advisory_gaps"] == ["container_contract_not_declared"]


def test_declared_container_contract_requires_tracked_digest_matched_evidence(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence/container.json"
    _write(evidence, '{"native": true}\n')
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    _write(
        tmp_path / ".ethos/profile.toml",
        _profile(
            '\n[container_contract]\nschema_version = 1\nmanifest = ".ethos/container-contract.toml"\n'
        ),
    )
    _write(tmp_path / ".ethos/container-contract.toml", _manifest(digest))
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "evidence/container.json"], check=True)

    assert container_contract_report(tmp_path)["state"] == "valid"

    _write(evidence, '{"tampered": true}\n')
    report = container_contract_report(tmp_path)

    assert report["ok"] is False
    assert (
        "container_contract_evidence_digest_mismatch:evidence/container.json"
        in report["required_gaps"]
    )


def _fixture_report(root: Path, case: dict[str, object]) -> dict[str, object]:
    operation = str(case["operation"])
    if operation == "profile_directory":
        (root / ".ethos/profile.toml").mkdir(parents=True)
    elif operation == "profile_symlink":
        profile = root / "inside/.ethos/profile.toml"
        _write(root / "outside.toml", "profile_id = 'outside'\n")
        profile.parent.mkdir(parents=True)
        profile.symlink_to(root / "outside.toml")
        root = root / "inside"
    else:
        shutil.copytree(_FIXTURE / "repository", root, dirs_exist_ok=True)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "evidence"], check=True)
        manifest = root / ".ethos/container-contract.toml"
        if operation == "profile":
            _write(root / ".ethos/profile.toml", _profile(str(case["value"])))
        elif operation == "relaxed_schema":
            schemas = root / "system/schemas/kernel"
            shutil.copytree(Path(__file__).parents[3] / "system/schemas/kernel", schemas)
            _write(schemas / "container-contract.schema.json", "{}\n")
            _write(manifest, "schema_version = 1\n")
        elif operation in {"replace", "manifest"}:
            text = str(case["value"])
            if operation == "replace":
                text = manifest.read_text(encoding="utf-8").replace(str(case["old"]), text)
            _write(manifest, text)
        elif operation == "evidence":
            _write(root / "evidence/container.json", str(case["value"]))
        elif operation == "missing_manifest":
            manifest.unlink()
        elif operation == "directory_manifest":
            manifest.unlink()
            manifest.mkdir()
    return container_contract_report(root)


@pytest.mark.parametrize("case", _CASES.values(), ids=_CASES)
def test_container_contract_fixture_matrix(tmp_path: Path, case: dict[str, object]) -> None:
    report = _fixture_report(tmp_path, case)
    gaps = report["required_gaps"]

    assert (report.get("state"), report.get("ok")) == (
        case.get("state", report["state"]),
        case.get("ok", report["ok"]),
    )
    assert "advisory" not in case or case["advisory"] in report["advisory_gaps"]
    assert all(any(gap.startswith(item) for gap in gaps) for item in case.get("expected", []))
    assert not any(any(gap.startswith(item) for gap in gaps) for item in case.get("forbidden", []))


def test_schema_report_surfaces_declared_contract_failure(tmp_path: Path) -> None:
    _write(
        tmp_path / ".ethos/profile.toml",
        _profile(
            '\n[container_contract]\nschema_version = 1\nmanifest = ".ethos/container-contract.toml"\n'
        ),
    )

    report = schema_validation_report(tmp_path)

    assert report["ok"] is False
    assert (
        "instance:container-contract:container_contract_manifest_missing" in report["required_gaps"]
    )


@pytest.mark.parametrize("mode", ["missing", "unreadable"])
def test_container_contract_product_schema_failures_are_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    class Candidate:
        def is_file(self) -> bool:
            return mode == "unreadable"

        def read_text(self, *, encoding: str) -> str:
            _ = encoding
            raise OSError

        def __truediv__(self, _part: str) -> Candidate:
            return self

    class SchemaPath:
        def resolve(self) -> SchemaPath:
            return self

        @property
        def parents(self) -> tuple[SchemaPath, ...]:
            return (self,)

        def __truediv__(self, _part: str) -> Candidate:
            return Candidate()

    monkeypatch.setattr(container_contract, "Path", lambda _value: SchemaPath())

    assert _schema_gaps(
        "container-contract.schema.json",
        {},
        prefix="container_contract_schema_violation",
    ) == [
        "container_contract_schema_violation:product_schema_unavailable:container-contract.schema.json"
    ]


def test_container_contract_file_and_payload_edges_fail_closed(tmp_path: Path) -> None:
    class BrokenPath:
        def resolve(self, *, strict: bool) -> Path:
            _ = strict
            raise OSError

    assert _contained_file(
        tmp_path,
        BrokenPath(),
        label="container_contract_test",
    ) == (None, "container_contract_test_unreadable")

    outside = tmp_path.parent / "outside-container-contract.toml"
    outside.write_text("sample\n", encoding="utf-8")
    assert _contained_file(tmp_path, outside, label="container_contract_test") == (
        None,
        "container_contract_test_path_escapes_root",
    )

    assert (
        _evidence_gaps(
            tmp_path,
            {"evidence": {"path": "evidence.json", "sha256": 1}},
        )
        == []
    )
    assert (
        _output_schema_gaps(
            tmp_path,
            {},
        )
        == []
    )


def test_container_contract_evidence_io_failures_are_required_gaps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = tmp_path / "evidence.json"
    _write(evidence, "{}\n")
    payload = {"evidence": {"path": "evidence.json", "sha256": "0" * 64}}

    def unavailable(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise OSError

    monkeypatch.setattr(container_contract.subprocess, "run", unavailable)
    assert _evidence_gaps(
        tmp_path,
        payload,
    ) == ["container_contract_evidence_tracking_unavailable:evidence.json"]


def test_container_contract_untracked_and_unreadable_evidence_are_required_gaps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = tmp_path / "evidence.json"
    _write(evidence, "{}\n")
    payload = {"evidence": {"path": "evidence.json", "sha256": "0" * 64}}

    assert _evidence_gaps(
        tmp_path,
        payload,
    ) == ["container_contract_evidence_untracked:evidence.json"]

    def unreadable_read_bytes(_path: Path) -> bytes:
        raise OSError

    monkeypatch.setattr(Path, "read_bytes", unreadable_read_bytes)
    monkeypatch.setattr(
        container_contract.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    assert _evidence_gaps(
        tmp_path,
        payload,
    ) == ["container_contract_evidence_unreadable:evidence.json"]
