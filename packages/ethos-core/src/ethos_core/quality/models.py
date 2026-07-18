from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass

from ethos_core.contracts.gates import GateDescriptor


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


QualityGateDescriptor = GateDescriptor


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
