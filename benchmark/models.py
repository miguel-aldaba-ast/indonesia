"""Data model for one row of the evidence register.

Field set mirrors the skill's own schema (see SKILL.md "Evidence dataset"
and references/scoring-evidence.md "Evidence register") so output from an
`indonesia-auto-benchmark` research session can be pasted in with no
reshaping.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

STATUSES = {"Confirmed", "Partial", "Not found", "Unknown"}
CONFIDENCE_LEVELS = {"High", "Medium", "Low"}
VALID_SCORES = {"0", "1", "2", "3", "4", "?", "N/A"}

FIELDNAMES = [
    "brand",
    "category",
    "capability",
    "status",              # Confirmed | Partial | Not found | Unknown
    "maturity_score",      # 0-4 | ? | N/A
    "advanced",            # yes/no — independently evidenced functional depth
    "short_description",
    "how_it_works",
    "customer_value",
    "url",
    "page_title",
    "date_accessed",       # YYYY-MM-DD
    "screenshot_status",
    "screenshot_reference",
    "limitations",
    "confidence",          # High | Medium | Low
]


@dataclass
class EvidenceRow:
    brand: str
    category: str
    capability: str
    status: str
    maturity_score: str
    advanced: str = "no"
    short_description: str = ""
    how_it_works: str = ""
    customer_value: str = ""
    url: str = ""
    page_title: str = ""
    date_accessed: str = ""
    screenshot_status: str = ""
    screenshot_reference: str = ""
    limitations: str = ""
    confidence: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "EvidenceRow":
        known = {f.name for f in fields(cls)}
        clean = {k: (v or "").strip() for k, v in d.items() if k in known}
        return cls(**clean)

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def key(self) -> tuple[str, str, str]:
        return (self.brand, self.category, self.capability)

    def score_numeric(self) -> int | None:
        if self.maturity_score in ("?", "N/A", ""):
            return None
        try:
            return int(self.maturity_score)
        except ValueError:
            return None

    def is_confirmed(self) -> bool:
        return self.status == "Confirmed"

    def is_advanced(self) -> bool:
        return self.advanced.strip().lower() in ("yes", "true", "1", "y")
