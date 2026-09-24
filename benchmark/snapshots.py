from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .io_csv import read_rows
from .models import EvidenceRow

DATA_DIR = Path("data")
SNAPSHOTS_DIR = DATA_DIR / "snapshots"


@dataclass
class Snapshot:
    id: str  # YYYY-MM-DD, optionally with -N suffix
    dir: Path

    @property
    def evidence_path(self) -> Path:
        return self.dir / "evidence.csv"

    @property
    def meta_path(self) -> Path:
        return self.dir / "meta.json"

    def load_rows(self) -> list[EvidenceRow]:
        return read_rows(self.evidence_path)

    def load_meta(self) -> dict:
        if self.meta_path.exists():
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        return {}


def list_snapshots(root: Path = SNAPSHOTS_DIR) -> list[Snapshot]:
    if not root.exists():
        return []
    snaps = [
        Snapshot(id=p.name, dir=p)
        for p in sorted(root.iterdir())
        if p.is_dir() and (p / "evidence.csv").exists()
    ]
    return sorted(snaps, key=lambda s: s.id)


def latest_two(root: Path = SNAPSHOTS_DIR) -> tuple[Snapshot | None, Snapshot | None]:
    snaps = list_snapshots(root)
    if not snaps:
        return None, None
    if len(snaps) == 1:
        return snaps[-1], None
    return snaps[-1], snaps[-2]


def new_snapshot_id(root: Path = SNAPSHOTS_DIR, on: date | None = None) -> str:
    on = on or date.today()
    base = on.isoformat()
    existing = {s.id for s in list_snapshots(root)}
    if base not in existing:
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    return f"{base}-{n}"


def write_meta(snapshot: Snapshot, meta: dict) -> None:
    snapshot.meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
