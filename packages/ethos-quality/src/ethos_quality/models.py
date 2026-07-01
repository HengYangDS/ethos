from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class QualityAssetClass:
    class_name: str
    role: str
    dimensions: tuple[str, ...]
    default_adapters: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "class": self.class_name,
            "role": self.role,
            "dimensions": list(self.dimensions),
            "default_adapters": list(self.default_adapters),
        }


@dataclass(frozen=True)
class ToolAdapterProfile:
    id: str
    standard: str
    asset_classes: tuple[str, ...]
    dimensions: tuple[str, ...]
    boundary: str
    maturity: str = "mature"

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "asset_classes": list(self.asset_classes),
            "dimensions": list(self.dimensions),
        }


@dataclass(frozen=True)
class QualityGateDescriptor:
    id: str
    kind: str
    command: tuple[str, ...]
    asset_classes: tuple[str, ...]
    dimensions: tuple[str, ...]
    execution_mode: str
    evidence_class: str
    trust_bearing: bool
    tool_adapter: str
    writes_files: bool
    network_policy: str
    version_source: str
    policy: str = "required"
    profile: str = "product"
    toolchain: str = "quality-adapter"
    depends_on: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "command": list(self.command),
            "policy": self.policy,
            "profile": self.profile,
            "toolchain": self.toolchain,
            "asset_classes": list(self.asset_classes),
            "dimensions": list(self.dimensions),
            "execution_mode": self.execution_mode,
            "evidence_class": self.evidence_class,
            "trust_bearing": self.trust_bearing,
            "tool_adapter": self.tool_adapter,
            "writes_files": self.writes_files,
            "network_policy": self.network_policy,
            "version_source": self.version_source,
            "depends_on": list(self.depends_on),
        }


@dataclass(frozen=True)
class QualityFinding:
    id: str
    severity: str
    asset_class: str
    dimension: str
    message: str
    path: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
