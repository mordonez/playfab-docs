from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class SourceType(str, Enum):
    OFFICIAL_GUIDE = "official-guide"
    REST_API = "rest-api"


class ContentStatus(str, Enum):
    CURRENT = "current"
    PREVIEW = "preview"
    MAINTENANCE = "maintenance"
    LEGACY = "legacy"


@dataclass(frozen=True)
class SourceFamily:
    source_type: SourceType
    manifest_url: str
    base_url: str
    product_area: str = ""


@dataclass(frozen=True)
class DiscoveredDocument:
    url: str
    source_type: SourceType
    toc_path: tuple[str, ...]
    product_area: str = "_root"
    api_surface: str = "_root"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["source_type"] = self.source_type.value
        data["toc_path"] = list(self.toc_path)
        return data


@dataclass
class ExtractedDocument:
    discovered: DiscoveredDocument
    title: str
    markdown: str
    fetched_at: str
    updated_at: str = ""
    published_at: str = ""
    content_status: ContentStatus = ContentStatus.CURRENT
    service: str = ""
    api_version: str = ""
    external_references: list[str] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)


@dataclass
class ExtractionFailure:
    discovered: DiscoveredDocument
    reason: str
    hard: bool = True


@dataclass
class BuildPaths:
    root: Path
    raw: Path
    reports: Path

    @classmethod
    def under(cls, root: Path) -> BuildPaths:
        return cls(root=root, raw=root / "raw", reports=root / "reports")
