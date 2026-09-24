"""Snapshot-to-snapshot diff — the "dynamic" part: run the benchmark again next
month and see exactly what changed instead of re-reading the whole matrix."""

from __future__ import annotations

from .models import EvidenceRow


def diff_rows(old: list[EvidenceRow], new: list[EvidenceRow]) -> dict:
    old_by_key = {r.key(): r for r in old}
    new_by_key = {r.key(): r for r in new}

    old_keys, new_keys = set(old_by_key), set(new_by_key)
    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    common = old_keys & new_keys

    status_changed = []
    score_changed = []
    url_changed = []
    for k in sorted(common):
        o, n = old_by_key[k], new_by_key[k]
        if o.status != n.status:
            status_changed.append((k, o.status, n.status))
        if o.maturity_score != n.maturity_score:
            score_changed.append((k, o.maturity_score, n.maturity_score))
        if o.url != n.url and o.url and n.url:
            url_changed.append((k, o.url, n.url))

    old_brands = {r.brand for r in old}
    new_brands = {r.brand for r in new}

    return {
        "added": [(k, new_by_key[k]) for k in added],
        "removed": [(k, old_by_key[k]) for k in removed],
        "status_changed": status_changed,
        "score_changed": score_changed,
        "url_changed": url_changed,
        "brands_added": sorted(new_brands - old_brands),
        "brands_removed": sorted(old_brands - new_brands),
    }


def to_markdown(old_id: str, new_id: str, d: dict) -> str:
    lines = [f"# Changes: {old_id} → {new_id}\n"]

    if d["brands_added"]:
        lines.append(f"**Brands added:** {', '.join(d['brands_added'])}\n")
    if d["brands_removed"]:
        lines.append(f"**Brands removed:** {', '.join(d['brands_removed'])}\n")

    def fmt_key(k):
        brand, category, capability = k
        return f"{brand} — {capability} ({category})"

    if d["status_changed"]:
        lines.append(f"\n## Status changes ({len(d['status_changed'])})\n")
        for k, o, n in d["status_changed"]:
            lines.append(f"- {fmt_key(k)}: `{o}` → `{n}`")

    if d["score_changed"]:
        lines.append(f"\n## Maturity score changes ({len(d['score_changed'])})\n")
        for k, o, n in d["score_changed"]:
            lines.append(f"- {fmt_key(k)}: `{o}` → `{n}`")

    if d["added"]:
        lines.append(f"\n## New capability rows ({len(d['added'])})\n")
        lines.append("New for this snapshot — either a brand shipped something new, or it's newly in scope.\n")
        for k, row in d["added"]:
            lines.append(f"- {fmt_key(k)} — {row.status} ({row.maturity_score})")

    if d["removed"]:
        lines.append(f"\n## Rows no longer present ({len(d['removed'])})\n")
        lines.append("Present last time, absent now — check whether this was dropped from scope "
                      "or genuinely removed from the site before concluding a brand removed a feature.\n")
        for k, row in d["removed"]:
            lines.append(f"- {fmt_key(k)} — was {row.status} ({row.maturity_score})")

    if d["url_changed"]:
        lines.append(f"\n## Evidence URL changed ({len(d['url_changed'])})\n")
        for k, o, n in d["url_changed"]:
            lines.append(f"- {fmt_key(k)}: {o} → {n}")

    if not any([d["status_changed"], d["score_changed"], d["added"], d["removed"], d["url_changed"],
                d["brands_added"], d["brands_removed"]]):
        lines.append("\nNo changes detected between these two snapshots.\n")

    return "\n".join(lines) + "\n"
