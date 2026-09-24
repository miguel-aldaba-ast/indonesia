from __future__ import annotations

import csv
from pathlib import Path

from .models import EvidenceRow, FIELDNAMES


def read_rows(path: Path) -> list[EvidenceRow]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in ("brand", "category", "capability", "status") if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"{path}: missing required column(s) {missing}. "
                f"Expected header: {','.join(FIELDNAMES)}"
            )
        return [EvidenceRow.from_dict(row) for row in reader if any((v or "").strip() for v in row.values())]


def write_rows(path: Path, rows: list[EvidenceRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (r.category, r.capability, r.brand)):
            writer.writerow(row.to_dict())


def write_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerow({
            "brand": "Toyota",
            "category": "CONFIGURE",
            "capability": "Model configurator",
            "status": "Confirmed",
            "maturity_score": "2",
            "advanced": "no",
            "short_description": "Customer selects variant, colour and accessories and sees a running price.",
            "how_it_works": "Configurator updates a summary panel and price as each option is picked; no dealer hand-off observed.",
            "customer_value": "Lets the customer build a specific car and see an indicative price before contacting a dealer.",
            "url": "https://www.toyota.astra.co.id/example-configurator",
            "page_title": "Configurator - Toyota Indonesia",
            "date_accessed": "2026-09-24",
            "screenshot_status": "captured",
            "screenshot_reference": "toyota_configurator_01.png",
            "limitations": "Could not confirm whether configuration can be sent to a dealer.",
            "confidence": "High",
        })
