from __future__ import annotations

from pathlib import Path

from ethos.surface.cli import quality as q


def _capture(monkeypatch):
    emitted = []

    def capture_emit(result, *, json_output=False, enforce=True):
        _ = (json_output, enforce)
        emitted.append(result.to_dict())

    monkeypatch.setattr(q, "emit", capture_emit)
    monkeypatch.setattr(q.tool_results, "emit", capture_emit)
    monkeypatch.setattr(q, "resolve_root", lambda root: root or Path.cwd())
    return emitted


def test_quality_tool_surfaces_delegate_to_configured_adapter(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(q._gitio, "git_files", lambda _repo, *patterns: [f"file{patterns[0]}"])

    def fake_report(**kwargs):
        return {"ok": True, "required_gaps": [], "state": "passed", **kwargs}

    monkeypatch.setattr(q.tool_results, "quality_tool_report", fake_report)
    q.markdown_links(root=tmp_path, json_output=True)
    q.shell_quality(root=tmp_path, json_output=True)
    q.toml_quality(root=tmp_path, json_output=True)
    q.yaml_quality(root=tmp_path, json_output=True)

    commands = [item["command"] for item in emitted]
    assert commands == [
        "quality markdown-links",
        "quality shell",
        "quality toml",
        "quality yaml",
    ]
    assert emitted[0]["data"]["tool"] == "lychee"
    assert emitted[1]["data"]["command"][:2] == ["bash", ".config/ci/scripts/run-shell-lint.sh"]
    assert emitted[2]["data"]["command"][:2] == ["bash", ".config/ci/scripts/run-config-lint.sh"]
    assert emitted[3]["data"]["command"][:2] == ["bash", ".config/ci/scripts/run-config-lint.sh"]


def test_quality_code_size_and_npm_project_reports(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(
        q._prove, "code_size_report", lambda _repo: {"ok": False, "required_gaps": ["too_big"]}
    )
    monkeypatch.setattr(
        q,
        "module_layout_report",
        lambda _repo: {
            "ok": False,
            "state": "blocked",
            "summary": {"suffix_module_count": 1},
            "required_gaps": ["module_layout_suffix_module:x"],
        },
    )
    monkeypatch.setattr(
        q.tool_results,
        "quality_tool_report",
        lambda **kwargs: {"ok": False, "required_gaps": ["npm_bad"], **kwargs},
    )
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    q.code_size(root=tmp_path, json_output=True)
    q.module_layout(root=tmp_path, json_output=True)
    q.npm_quality(root=tmp_path, json_output=True)

    assert emitted[0]["command"] == "quality code-size"
    assert emitted[0]["state"] == "blocked"
    assert emitted[0]["required_gaps"] == ["too_big"]
    assert emitted[1]["command"] == "quality module-layout"
    assert emitted[1]["state"] == "blocked"
    assert emitted[1]["summary"] == {"suffix_module_count": 1}
    assert emitted[2]["command"] == "quality npm"
    assert emitted[2]["data"]["files"] == ["package.json"]


def test_quality_release_commit_sbom_and_attestation_surfaces(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(
        q,
        "signature_policy_report",
        lambda _repo: {"required_gaps": [], "head_subject_ok": False, "head_signature_ok": False},
    )
    monkeypatch.setattr(
        q.repository_audit_module,
        "release_files_report",
        lambda _repo: {"ok": False, "missing": ["LICENSE"]},
    )
    monkeypatch.setattr(
        q,
        "release_policy_report",
        lambda _repo: {
            "ok": False,
            "required_gaps": ["policy_gap"],
            "host_profile": {"provider": "gitlab"},
        },
    )
    monkeypatch.setattr(q, "sbom_projection", lambda _repo: {"packages": [{"name": "ethos"}]})
    monkeypatch.setattr(q._gitio, "current_head", lambda _repo: "abc123")

    def fake_release_attestation(root, head, evidence_digest):
        return {"predicate": {"tag": "v1"}, "head": head, "digest": evidence_digest}

    monkeypatch.setattr(q, "release_attestation", fake_release_attestation)

    q.commits(enforce_head=True, root=tmp_path, json_output=True)
    q.release(root=tmp_path, json_output=True)
    q.release_policy(root=tmp_path, json_output=True)
    q.sbom(root=tmp_path, json_output=True)
    q.release_attestation_command(evidence_digest="sha256:x", root=tmp_path, json_output=True)

    assert emitted[0]["required_gaps"] == [
        "head_subject_not_conventional",
        "head_signature_not_good",
    ]
    assert emitted[1]["command"] == "quality release"
    assert emitted[1]["next_actions"] == ["uv build --all-packages"]
    assert emitted[2]["command"] == "quality release-policy"
    assert emitted[2]["next_actions"] == ["ethos quality release-attestation"]
    assert emitted[3]["summary"] == {"package_count": 1}
    assert emitted[4]["summary"] == {"tag": "v1"}


def test_quality_coverage_reports_policy_and_latest_artifact(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    report = {
        "ok": True,
        "state": "clean",
        "policy": {"current_hard_floor": 95.0},
        "latest_artifact": {"line_percent": 96.0},
        "required_gaps": [],
    }
    monkeypatch.setattr(q, "coverage_quality_report", lambda _repo: report)

    q.coverage(root=tmp_path, json_output=True)

    assert emitted[0]["command"] == "quality coverage"
    assert emitted[0]["ok"] is True
    assert emitted[0]["summary"] == {
        "current_hard_floor": 95.0,
        "latest_line_percent": 96.0,
    }
    assert emitted[0]["data"] == report


def test_quality_docstrings_reports_policy_coverage(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    report = {
        "ok": False,
        "state": "blocked",
        "coverage_percent": 50.0,
        "fail_under": 95.0,
        "documented_count": 1,
        "public_count": 2,
        "missing": [
            {
                "path": "pkg/mod.py",
                "qualified_name": "mod.public",
                "kind": "function",
                "line": 3,
            }
        ],
        "required_gaps": ["docstring_coverage_below_minimum:50.00<95.00"],
    }
    monkeypatch.setattr(q, "docstring_coverage_report", lambda _repo: report)

    q.docstrings(root=tmp_path, json_output=True)

    assert emitted[0]["command"] == "quality docstrings"
    assert emitted[0]["ok"] is False
    assert emitted[0]["state"] == "blocked"
    assert emitted[0]["summary"] == {
        "coverage_percent": 50.0,
        "documented_count": 1,
        "public_count": 2,
        "style_issue_count": 0,
        "advisory_missing_count": 0,
    }
    assert emitted[0]["required_gaps"] == ["docstring_coverage_below_minimum:50.00<95.00"]
    assert emitted[0]["data"]["missing"][0]["qualified_name"] == "mod.public"
