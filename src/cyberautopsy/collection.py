"""Internet collection pipeline (vertical-slice scale).

Cyber Autopsy collects its source material from the public internet. This
module is the minimal, reproducible core of that pipeline:

  discovery  versioned query sets (what we searched for and when)
  retrieval  fetch a URL, record sha256 content hash + retrieval timestamp
  manifest   data/collection/collection_manifest.json records every URL
             considered, with an explicit include/exclude decision + reason

Stage directories
-----------------
  data/collection/raw/        raw retrieved content, named by content hash
  data/collection/processed/  normalised text (manual or scripted)
  data/                       benchmark-ready JSONL (sources, evidence, ...)

Nothing here fabricates content: retrieval failures, redirects, and paywalls
are recorded honestly via AccessStatus.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COLLECTION_DIR = REPO_ROOT / "data" / "collection"
RAW_DIR = COLLECTION_DIR / "raw"
PROCESSED_DIR = COLLECTION_DIR / "processed"
MANIFEST_PATH = COLLECTION_DIR / "collection_manifest.json"

PIPELINE_VERSION = "0.1.0"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def content_sha256(content: str | bytes) -> str:
    data = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()


@dataclass
class QuerySet:
    """A versioned set of discovery queries. Append-only: never rewrite a
    published version; add a new one."""

    version: str
    created_at: str
    queries: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class CollectionRecord:
    """One URL considered by the pipeline, included or not."""

    url: str
    discovered_via: str  # query text, referral URL, or "manual"
    retrieved_at: str | None = None
    content_hash: str | None = None
    access_status: str = "open"  # mirrors schemas.AccessStatus values
    archive_url: str | None = None
    included: bool = False
    decision_reason: str = ""
    source_id: str | None = None  # set when promoted to data/sources.jsonl
    parser_version: str = PIPELINE_VERSION


@dataclass
class CollectionManifest:
    pipeline_version: str = PIPELINE_VERSION
    query_sets: list[QuerySet] = field(default_factory=list)
    records: list[CollectionRecord] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path = MANIFEST_PATH) -> "CollectionManifest":
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            pipeline_version=raw.get("pipeline_version", PIPELINE_VERSION),
            query_sets=[QuerySet(**q) for q in raw.get("query_sets", [])],
            records=[CollectionRecord(**r) for r in raw.get("records", [])],
        )

    def save(self, path: Path = MANIFEST_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def record_for_url(self, url: str) -> CollectionRecord | None:
        return next((r for r in self.records if r.url == url), None)

    def add_record(self, record: CollectionRecord) -> None:
        existing = self.record_for_url(record.url)
        if existing is not None:
            self.records.remove(existing)
        self.records.append(record)


def store_raw(content: str | bytes, suffix: str = ".txt") -> tuple[str, Path]:
    """Store raw retrieved content under data/collection/raw/<hash><suffix>.

    Returns (content_hash, path). Idempotent: identical content is stored once.
    """
    digest = content_sha256(content)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{digest}{suffix}"
    if not path.exists():
        data = content.encode("utf-8") if isinstance(content, str) else content
        path.write_bytes(data)
    return digest, path
