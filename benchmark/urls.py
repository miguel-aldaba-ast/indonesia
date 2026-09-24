"""Export a deduped URL list for pasting into external tracking/analytics
systems. Python has no access to traffic data, so this is the hand-off point:
we can only tell you which pages embody which capability, not how much
traffic or conversion they get."""

from __future__ import annotations

import csv
from pathlib import Path

from .models import EvidenceRow

URL_FIELDNAMES = ["url", "brand", "category", "capability", "status", "page_title", "date_accessed"]


def export_urls(rows: list[EvidenceRow], path: Path) -> int:
    seen: dict[str, EvidenceRow] = {}
    combined: dict[str, list[EvidenceRow]] = {}
    for r in rows:
        if not r.url:
            continue
        combined.setdefault(r.url, []).append(r)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=URL_FIELDNAMES)
        writer.writeheader()
        for url, group in sorted(combined.items()):
            r = group[0]
            capabilities = "; ".join(sorted({g.capability for g in group}))
            writer.writerow({
                "url": url,
                "brand": r.brand,
                "category": r.category,
                "capability": capabilities,
                "status": r.status,
                "page_title": r.page_title,
                "date_accessed": r.date_accessed,
            })
    return len(combined)
