"""Evidence layout declaration contract."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict

from ethos_core._resources import declaration_text
from ethos_core._resources import resolve_declaration_path
from ethos_core.contracts.cel import evaluate_cel_predicate

DECLARATION_PATH = Path("system/policies/evidence-layout.toml")
_DECLARATION_RESOURCE = "data/evidence_layout.toml"


class EvidenceRequiredSubroot(BaseModel):
    """Declared required evidence subroot and its gap id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    gap: str


class KernelEvidenceLayout(BaseModel):
    """Declared kernel evidence layout."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: str = "kernel_evidence"
    allowed_root_files: tuple[str, ...]
    allowed_root_dirs: tuple[str, ...]
    claim_file_glob: str
    nested_claim_file_glob: str
    chronicle_record_glob: str
    flat_chronicle_glob: str
    parity_artifact_glob: str
    root_file_not_allowed_gap_prefix: str
    root_dir_not_allowed_gap_prefix: str
    claim_nested_file_gap_prefix: str
    chronicle_flat_markdown_gap_prefix: str
    required_subroot: tuple[EvidenceRequiredSubroot, ...]


class CuratedProfileEvidenceLayout(BaseModel):
    """Declared curated profile evidence layout."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: str = "curated_profile_evidence"
    allowed_root_files: tuple[str, ...]
    root_file_not_allowed_gap_prefix: str


class EvidenceLayoutDeclaration(BaseModel):
    """Typed declaration for evidence root topology."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    schema_version: int = 1
    source_refs: tuple[str, ...] = ()
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
                "allowed_root_dirs": ["*"],
                "claims_root": "",
                "chronicle_root": "",
                "parity_root": "",
                "source_refs": list(self.source_refs),
            }
        return {
            "root": root,
            "allowed_root_files": list(self.kernel.allowed_root_files),
            "allowed_root_dirs": list(self.kernel.allowed_root_dirs),
            "claims_root": f"{root}/claims",
            "chronicle_root": f"{root}/chronicle",
            "parity_root": f"{root}/parity",
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
