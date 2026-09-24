from __future__ import annotations

from .models import EvidenceRow, STATUSES, VALID_SCORES, CONFIDENCE_LEVELS
from .taxonomy import is_known


def validate_rows(rows: list[EvidenceRow]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors block ingest; warnings do not."""
    errors: list[str] = []
    warnings: list[str] = []
    seen: dict[tuple[str, str, str], int] = {}

    for i, row in enumerate(rows, start=2):  # header is line 1
        where = f"line {i} ({row.brand!r}/{row.capability!r})"

        if not row.brand:
            errors.append(f"{where}: missing brand")
        if not row.category:
            errors.append(f"{where}: missing category")
        if not row.capability:
            errors.append(f"{where}: missing capability")

        if row.status not in STATUSES:
            errors.append(f"{where}: status {row.status!r} not one of {sorted(STATUSES)}")

        if row.maturity_score not in VALID_SCORES:
            errors.append(f"{where}: maturity_score {row.maturity_score!r} not one of {sorted(VALID_SCORES)}")

        if row.status == "Confirmed" and row.maturity_score in ("", "N/A"):
            warnings.append(f"{where}: status is Confirmed but maturity_score is empty/N/A")
        if row.status == "Not found" and row.maturity_score not in ("0", "?"):
            warnings.append(f"{where}: status is 'Not found' but maturity_score is {row.maturity_score!r} (expected 0 or ?)")

        if row.confidence and row.confidence not in CONFIDENCE_LEVELS:
            warnings.append(f"{where}: confidence {row.confidence!r} not one of {sorted(CONFIDENCE_LEVELS)}")

        if row.status in ("Confirmed", "Partial") and not row.url:
            warnings.append(f"{where}: {row.status} capability has no evidence URL")

        if row.category and row.capability and not is_known(row.category, row.capability):
            warnings.append(f"{where}: '{row.category} / {row.capability}' is not in the shared taxonomy "
                             f"(fine if this is a genuinely new capability found during research)")

        key = row.key()
        if key in seen:
            errors.append(f"{where}: duplicate row for brand/category/capability "
                           f"(also on line {seen[key]}) — merge into one row")
        else:
            seen[key] = i

    return errors, warnings
