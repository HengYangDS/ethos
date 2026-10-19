"""Installed agent guidance is a projection of the selected product."""

import hashlib
import shutil
import tomllib
from pathlib import Path

import pytest

import ethos.repository.release.resources as resource_owner
from ethos.adapters.repo.dependency_acceptance import product_audit_snapshot
from ethos.repository.context import repository_context
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_POLICY_PATH
from ethos.repository.policy.quality.dependency_acceptance import product_audit_projection
from ethos.repository.policy.references.markdown import markdown_tokens
from ethos.repository.release.identity import build_identity


def test_repository_context_exposes_portable_installed_guidance(tmp_path: Path) -> None:
    """Agents discover guidance without an ETHOS checkout or vendor-specific host."""
    context = repository_context(tmp_path)
    guidance = context["agent_guidance"]
    assert isinstance(guidance, dict)
    packaged = Path(guidance["path"])

    assert guidance["media_type"] == "text/markdown"
    assert guidance["authority"] == "product_projection"
    assert packaged.is_file()
    content = packaged.read_text(encoding="utf-8")
    assert guidance["sha256"] == hashlib.sha256(content.encode()).hexdigest()
    assert "ethos status" in content
    assert "next_action" in content
    assert "uv run" not in content
    assert "/Users/" not in content
    sources = guidance["sources"]
    assert {source["role"] for source in sources} == {
        "product-meaning",
        "rules",
        "agent-method",
        "documentation",
        "adoption",
        "release",
        "recovery",
        "commands",
        "resources",
    }
    assert all(source["origin"] == "product" for source in sources)
    assert all(
        source["sha256"] == hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest()
        for source in sources
    )
    for source in sources:
        tokens = markdown_tokens(Path(source["path"]).read_text(encoding="utf-8"))
        assert tokens is not None
        headings = {
            tokens[index + 1].content
            for index, token in enumerate(tokens)
            if token.type == "heading_open"
        }
        assert set(source["sections"]) <= headings
    assert "agent_guidance.sources" in content


def test_repository_context_canonicalizes_the_installed_guidance_path(
    monkeypatch, tmp_path: Path
) -> None:
    """SDK and subprocess status agree despite an editable-install dot-segment path."""
    package = _installed_package(tmp_path)
    guidance = package / "resources/skills/ethos-repository-work/SKILL.md"
    (package / "subdirectory").mkdir()
    monkeypatch.setattr(resource_owner, "files", lambda _name: package / "subdirectory/..")

    context = repository_context(tmp_path)["agent_guidance"]
    assert isinstance(context, dict)
    observed = context["path"]
    assert observed == guidance.resolve().as_posix()
    sources = context["sources"]
    assert all(Path(source["path"]).is_relative_to(package) for source in sources)
    assert all(source["origin"] == "product" for source in sources)


def test_installed_context_exposes_the_documentation_owner_without_source_checkout(
    monkeypatch, tmp_path: Path
) -> None:
    """An adopter can open the selected docs contract from package-owned bytes."""
    package = _installed_package(tmp_path)
    monkeypatch.setattr(resource_owner, "files", lambda _name: package)

    context = repository_context(tmp_path)
    guidance = context["agent_guidance"]
    assert isinstance(guidance, dict)
    documentation = next(
        source for source in guidance["sources"] if source["role"] == "documentation"
    )
    path = Path(documentation["path"])
    assert path.is_relative_to(package)
    assert path.is_file()
    assert documentation["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()

    path.unlink()
    with pytest.raises(FileNotFoundError):
        repository_context(tmp_path)


@pytest.mark.parametrize("installed", [False, True])
@pytest.mark.parametrize("relative", ["system/schemas/contract.json", AUDIT_POLICY_PATH])
def test_resource_locator_uses_loaded_product_not_caller(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, relative: str, *, installed: bool
) -> None:
    """Source and installed readers retain their selected owner when cwd changes."""
    product = tmp_path / "product"
    package = product / ("installed/ethos" if installed else "src/ethos")
    resources = package / "resources"
    canonical = (resources if installed else product) / relative
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(b"selected product input\n")
    resources.mkdir(parents=True, exist_ok=True)
    caller = tmp_path / "caller"
    lookalike = caller / relative
    lookalike.parent.mkdir(parents=True)
    lookalike.write_bytes(b"unrelated caller input\n")
    monkeypatch.setattr(resource_owner, "files", lambda _name: package)
    monkeypatch.chdir(caller)

    assert resource_owner.canonical_resource(relative) == canonical
    assert resource_owner.canonical_resource(relative).read_bytes() == canonical.read_bytes()
    assert resource_owner.packaged_resource() == resources
    canonical.unlink()
    assert resource_owner.canonical_resource(relative) == canonical
    assert not resource_owner.canonical_resource(relative).exists()


@pytest.mark.parametrize("fault", ["missing", "noncanonical"])
def test_installed_product_policy_refuses_missing_or_local_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """An installed product never substitutes caller policy or host-local approvals."""
    package = tmp_path / "selected/ethos"
    product = package / "resources" / AUDIT_POLICY_PATH
    product.parent.mkdir(parents=True)
    source = Path(__file__).resolve().parents[3] / AUDIT_POLICY_PATH
    raw = source.read_bytes()
    product.write_bytes(product_audit_projection(raw))
    monkeypatch.setattr(resource_owner, "files", lambda _name: package)
    build = build_identity(product="0.0.0", source_commit="a" * 40, source_tree="b" * 40)
    selected, _binding = product_audit_snapshot(build=build)
    assert all(record.scope == "production-release" for record in selected.dispositions)
    if fault == "missing":
        product.unlink()
        with pytest.raises(FileNotFoundError):
            product_audit_snapshot(build=build)
    else:
        product.write_bytes(raw)
        with pytest.raises(ValueError, match="dependency_audit_product_policy_noncanonical"):
            product_audit_snapshot(build=build)
    assert source.read_bytes() == raw


def test_packaged_resource_requires_a_contained_relative_input(tmp_path: Path) -> None:
    """A supplied package anchor is not permission to escape its resource closure."""
    package = tmp_path / "ethos"
    resources = package / "resources"
    resources.mkdir(parents=True)
    external = tmp_path / "outside"
    external.mkdir()
    with pytest.raises(ValueError, match="product_resource_path_invalid"):
        resource_owner.packaged_resource("../outside", package=package)
    with pytest.raises(ValueError, match="product_resource_path_invalid"):
        resource_owner.packaged_resource("C:/outside", package=package)
    (resources / "escape").symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match="product_resource_path_invalid"):
        resource_owner.packaged_resource("escape/input", package=package)


@pytest.mark.parametrize(
    "relative",
    [
        ".config/checks/prettier/prettier.toml",
        ".config/checks/codespell/codespell.toml",
        ".config/checks/taplo/taplo.toml",
        ".config/checks/yamllint/.yamllint.yaml",
        ".config/checks/format-selection/policy.toml",
        ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml",
        ".config/checks/lychee/lychee.toml",
    ],
)
def test_installed_document_quality_preserves_shipped_native_policy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, relative: str
) -> None:
    """Installed quality reads native policy bytes without a source checkout."""
    root = Path(__file__).resolve().parents[3]
    package = _installed_package(tmp_path)
    monkeypatch.setattr(resource_owner, "files", lambda _name: package)
    policy = resource_owner.canonical_resource(relative)
    assert policy == package / "resources" / relative
    assert policy.read_bytes() == (root / relative).read_bytes()
    declaration = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert relative in declaration["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]


def _installed_package(tmp_path: Path) -> Path:
    """Stage resources from the native package declaration, not another source map."""
    root = Path(__file__).resolve().parents[3]
    package = tmp_path / "package"
    guide = package / "resources/skills/ethos-repository-work/SKILL.md"
    guide.parent.mkdir(parents=True)
    shutil.copyfile(root / "src/ethos/resources/skills/ethos-repository-work/SKILL.md", guide)
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    for source, target in project["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"
    ].items():
        if not target.startswith(resource_owner.WHEEL_RESOURCE_ROOT.as_posix() + "/"):
            continue
        destination = package / target.removeprefix("ethos/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if (root / source).is_dir():
            shutil.copytree(root / source, destination)
        else:
            shutil.copyfile(root / source, destination)
    return package


def test_installed_navigation_preserves_required_links_without_source_checkout(
    tmp_path: Path,
) -> None:
    """Required document edges resolve; labelled source references stay optional."""
    resources = _installed_package(tmp_path) / "resources"
    unresolved = []
    for path in sorted(resources.rglob("*.md")):
        tokens = markdown_tokens(path.read_text(encoding="utf-8"))
        assert tokens is not None
        for block in tokens:
            children = block.children or ()
            for index, token in enumerate(children):
                if token.type != "link_open":
                    continue
                if token.attrGet("title") == "source-only":
                    assert "source" in children[index + 1].content.casefold()
                    continue
                href = token.attrGet("href") or ""
                assert isinstance(href, str)
                if not href or href.startswith(("#", "https:", "http:", "mailto:")):
                    continue
                target = (path.parent / href.split("#", 1)[0]).resolve()
                if not target.is_relative_to(resources.resolve()) or not target.exists():
                    unresolved.append(f"{path.relative_to(resources)} -> {href}")
    assert not unresolved, "Unresolved required installed navigation: " + "; ".join(unresolved)
