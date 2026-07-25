from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

TARGET_PACKAGES = ("ethos",)
MIGRATION_HOSTS = ()
TARGET_DISTRIBUTIONS = ("distributions/npm",)
RETIRED_PRODUCT_FAMILIES = (
    "ethos-core",
    "ethos-kernel",
    "ethos-governance",
    "ethos-workspace",
    "ethos-agent",
    "ethos-project",
    "ethos-node",
)
RETIRED_PRODUCT_FAMILY_TOKENS = tuple(
    token for family in RETIRED_PRODUCT_FAMILIES for token in (family, family.replace("-", "_"))
)
MIGRATION_DISTRIBUTIONS = {"distributions/npm": {"state": "migrated", "home": "distributions/npm"}}
MIGRATION_DISPOSITIONS = dict.fromkeys(
    RETIRED_PRODUCT_FAMILIES,
    "absorbed into the sole ethos package or its declared distribution adapter",
)
MIGRATION_HOST_LIFECYCLE: dict[str, object] = {}


def package_ontology_report() -> dict[str, object]:
    return {
        "target_packages": list(TARGET_PACKAGES),
        "migration_hosts": list(MIGRATION_HOSTS),
        "target_distributions": list(TARGET_DISTRIBUTIONS),
        "migration_distributions": dict(MIGRATION_DISTRIBUTIONS),
        "migration_dispositions": dict(MIGRATION_DISPOSITIONS),
        "migration_host_lifecycle": dict(MIGRATION_HOST_LIFECYCLE),
    }


def workspace_package_config_report(root: Path) -> dict[str, object]:
    path = root / ".ethos" / "workspace.toml"
    if not path.exists():
        return {
            "ok": True,
            "path": path.relative_to(root).as_posix(),
            "packages": [],
            "required_gaps": [],
        }
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return {
            "ok": False,
            "path": path.relative_to(root).as_posix(),
            "packages": [],
            "required_gaps": [f"workspace_config_invalid_toml:{exc}"],
        }
    packages = [item for item in payload.get("package", []) if isinstance(item, dict)]
    names = {str(item.get("name", "")) for item in packages if item.get("name")}
    package_paths = {str(item.get("path", "")) for item in packages if item.get("path")}
    identity = "\n".join(sorted(names | package_paths))
    gaps: list[str] = [
        f"workspace_config_retired_product_family:{retired}"
        for retired in RETIRED_PRODUCT_FAMILY_TOKENS
        if retired in identity
    ]
    gaps += [
        f"workspace_config_missing_target:{package}"
        for package in TARGET_PACKAGES
        if package not in names
    ]
    gaps += [
        f"workspace_config_unexpected_package:{package}"
        for package in sorted(names - set(TARGET_PACKAGES))
    ]
    return {
        "ok": not gaps,
        "path": path.relative_to(root).as_posix(),
        "packages": sorted(names),
        "required_gaps": gaps,
    }
