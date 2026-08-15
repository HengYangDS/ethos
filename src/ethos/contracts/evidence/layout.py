"""Evidence layout declaration contract."""

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict

from ethos._resources import declaration_text
from ethos._resources import resolve_declaration_path
from ethos.contracts.policy.cel import evaluate_cel_predicate
from ethos.contracts.value import FrozenTuple

DECLARATION_PATH = Path("system/policies/evidence-layout.toml")
_DECLARATION_RESOURCE = "data/evidence_layout.toml"


class KernelEvidenceLayout(BaseModel):
    """Declared kernel evidence layout."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    mode: str = "kernel_evidence"
    allowed_root_files: FrozenTuple[str]
    historical_root_dirs: FrozenTuple[str]
    root_file_not_allowed_gap_prefix: str
    root_dir_not_allowed_gap_prefix: str


class CuratedProfileEvidenceLayout(BaseModel):
    """Declared curated profile evidence layout."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    mode: str = "curated_profile_evidence"
    allowed_root_files: FrozenTuple[str]
    root_file_not_allowed_gap_prefix: str


class EvidenceLayoutDeclaration(BaseModel):
    """Typed declaration for evidence root topology."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    id: str
    schema_version: int = 1
    source_refs: FrozenTuple[str] = ()
    profile_curated_root: str
    root_missing_gap: str
    kernel: KernelEvidenceLayout
    curated_profile: CuratedProfileEvidenceLayout
    freshness_expression: str

    def layout_payload(self, root: str, *, curated_profile: bool = False) -> dict[str, Any]:
        """Return the stable public layout payload for an evidence root."""
        if curated_profile:
            return {
                "root": root,
                "mode": self.curated_profile.mode,
                "allowed_root_files": list(self.curated_profile.allowed_root_files),
                "source_refs": list(self.source_refs),
            }
        return {
            "root": root,
            "mode": self.kernel.mode,
            "allowed_root_files": list(self.kernel.allowed_root_files),
            "historical_roots": [
                f"{root}/{directory}" for directory in self.kernel.historical_root_dirs
            ],
            "source_refs": list(self.source_refs),
        }

    def freshness_ok(self, components: tuple[dict[str, object], ...]) -> bool:
        """Reduce declared evidence facts through the restricted CEL predicate."""
        return evaluate_cel_predicate(
            self.freshness_expression,
            facts={"components": list(components)},
            policy={},
            rule={},
        )


def _declaration_text(path: Path) -> str:
    return declaration_text(
        path,
        resource=_DECLARATION_RESOURCE,
        canonical=Path("system/policies/evidence-layout.toml"),
    )


def load_evidence_layout_declaration(
    path: Path | str | None = None,
) -> EvidenceLayoutDeclaration:
    """Load the evidence layout declaration from TOML."""
    declaration_path = resolve_declaration_path(
        path, canonical=DECLARATION_PATH, module_file=__file__
    )
    payload = tomllib.loads(_declaration_text(declaration_path))
    return EvidenceLayoutDeclaration.model_validate(payload)
