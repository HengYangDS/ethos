from __future__ import annotations

import hashlib
import importlib
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest
from pydantic import ValidationError

from ethos.repository.adoption.scaffold.core import default_files

ROOT = Path(__file__).resolve().parents[3]
SCAFFOLD_ROOT = ROOT / "packages/ethos/src/ethos/repository/adoption/scaffold"


def _files_digest(files: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, content in sorted(files.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


@pytest.mark.parametrize(
    ("profile", "expected_count", "expected_digest"),
    [
        ("generic", 65, "3c7d9eec0a6b417c016a93bd0b55afc238d83c5a0230d43e2bbba619d2757305"),
        ("github", 66, "799103f823eddc6e6f04169a181928bc59abe5d51118a69aac37c508dbe8c8cf"),
        ("gitlab", 66, "2afab7054df2d7a2e127c0f129afd029e1a9cfc166d3a0bdcd540e0397adbb6c"),
    ],
)
def test_scaffold_template_migration_preserves_default_file_bytes(
    tmp_path: Path,
    profile: str,
    expected_count: int,
    expected_digest: str,
) -> None:
    root = tmp_path / "sample-repo"
    root.mkdir()

    files = default_files(root, profile)

    assert len(files) == expected_count
    assert _files_digest(files) == expected_digest


def test_monorepo_template_preserves_sorted_package_projection(tmp_path: Path) -> None:
    root = tmp_path / "sample-repo"
    (root / "packages/zeta").mkdir(parents=True)
    (root / "packages/alpha").mkdir(parents=True)

    files = default_files(root, "monorepo")

    assert (
        _files_digest(files) == "091914df049991c2194790a95e27c40ba603347cb90edc7b9f7f0bf0ec468572"
    )
    assert files[".ethos/workspace.toml"].index('name = "alpha"') < files[
        ".ethos/workspace.toml"
    ].index('name = "zeta"')


def test_scaffold_templates_use_packaged_jinja_and_strict_typed_contexts() -> None:
    templates = importlib.import_module("ethos.repository.adoption.scaffold.templates")

    expected = {
        "core/project.toml.j2",
        "core/workspace.toml.j2",
        "decisions/record-template.md.j2",
        "documents/agents.md.j2",
        "openspec/spec.md.j2",
        "skills/package.toml.j2",
    }
    assert expected <= set(templates.template_names())

    context = templates.RepositoryTemplateContext(
        project_name="sample-repo",
        profile="github",
        packages=(),
    )
    assert context.model_config["frozen"] is True
    assert templates.render_template("core/project.toml.j2", context) == (
        '[meta]\nname = "sample-repo"\nproduct = "ETHOS"\nversion = 1\n'
    )
    with pytest.raises(ValidationError):
        templates.RepositoryTemplateContext(
            project_name="sample-repo",
            profile="unknown",
            packages=(),
        )
    with pytest.raises(ValidationError):
        templates.RepositoryTemplateContext(
            project_name="sample-repo",
            profile="generic",
            packages=(),
            undeclared=True,
        )


def test_scaffold_template_environment_uses_explicit_autoescape_policy() -> None:
    templates = importlib.import_module("ethos.repository.adoption.scaffold.templates")

    env = templates.environment()

    assert callable(env.autoescape)
    assert env.autoescape("sample.html") is True
    assert env.autoescape("core/project.toml.j2") is False


def test_project_template_preserves_python_json_string_encoding() -> None:
    templates = importlib.import_module("ethos.repository.adoption.scaffold.templates")
    context = templates.RepositoryTemplateContext(
        project_name='sample<repo&"',
        profile="generic",
        packages=(),
    )

    assert templates.render_template("core/project.toml.j2", context) == (
        '[meta]\nname = "sample<repo&\\""\nproduct = "ETHOS"\nversion = 1\n'
    )


@pytest.mark.parametrize(
    "payload",
    [
        {
            "version": 1,
            "artifact": [
                {"path": "same", "template": "one.j2", "renderer": "activation"},
                {"path": "same", "template": "two.j2"},
            ],
            "family": [],
            "skill": [],
        },
        {
            "version": 1,
            "artifact": [{"path": "a", "template": "a.j2", "renderer": "activation"}],
            "family": [
                {
                    "id": "same",
                    "title": "One",
                    "scope": "one",
                    "profile_family": "one",
                    "owner": "one",
                },
                {
                    "id": "same",
                    "title": "Two",
                    "scope": "two",
                    "profile_family": "two",
                    "owner": "two",
                },
            ],
            "skill": [],
        },
        {
            "version": 1,
            "artifact": [{"path": "a", "template": "a.j2", "renderer": "activation"}],
            "family": [],
            "skill": [
                {"id": "same", "capabilities": []},
                {"id": "same", "capabilities": []},
            ],
        },
        {"version": 1, "artifact": [], "family": [], "skill": []},
        {
            "version": 1,
            "artifact": [
                {
                    "path": "package.toml",
                    "template": "package.j2",
                    "renderer": "skill-package",
                    "subject": "missing",
                },
                {"path": "activation.toml", "template": "a.j2", "renderer": "activation"},
            ],
            "family": [],
            "skill": [],
        },
    ],
)
def test_scaffold_template_declaration_rejects_cross_record_drift(
    payload: dict[str, object],
) -> None:
    templates = importlib.import_module("ethos.repository.adoption.scaffold.templates")

    with pytest.raises(ValidationError):
        templates.ScaffoldTemplateDeclaration.model_validate(payload)


def test_scaffold_python_contains_no_embedded_multiline_payloads() -> None:
    sources = sorted(SCAFFOLD_ROOT.rglob("*.py"))

    assert sources
    for source in sources:
        text = source.read_text(encoding="utf-8")
        assert 'return """' not in text
        assert 'return f"""' not in text


def test_scaffold_cutover_removes_payload_generator_modules() -> None:
    removed = (
        SCAFFOLD_ROOT / "decisions/core.py",
        SCAFFOLD_ROOT / "documents/pages.py",
        SCAFFOLD_ROOT / "openspec.py",
        SCAFFOLD_ROOT / "skills/core.py",
    )

    assert all(not path.exists() for path in removed)


def test_scaffold_templates_are_packaged_in_the_ethos_wheel(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--package", "ethos", "--wheel", "--out-dir", str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(tmp_path.glob("ethos-*.whl"))

    with ZipFile(wheel) as archive:
        names = set(archive.namelist())

    suffixes = {
        "ethos/repository/adoption/scaffold/template_files/manifest.toml",
        "ethos/repository/adoption/scaffold/template_files/core/project.toml.j2",
        "ethos/repository/adoption/scaffold/template_files/skills/package.toml.j2",
    }
    assert all(any(name.endswith(suffix) for name in names) for suffix in suffixes)
