"""Build the capability matrix, novelty classification and Markdown/HTML report
for a single snapshot, following the scoring rules in the research skill's
references/scoring-evidence.md (novelty thresholds, maturity scale, N/A vs ?).
"""

from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path

from .models import EvidenceRow
from .taxonomy import CATEGORY_ORDER, TAXONOMY


def _category_sort_key(category: str):
    if category in CATEGORY_ORDER:
        return (0, CATEGORY_ORDER.index(category))
    return (1, category)


def _capability_sort_key(category: str, capability: str):
    known = TAXONOMY.get(category, [])
    if capability in known:
        return (0, known.index(capability))
    return (1, capability)


def build_matrix(rows: list[EvidenceRow]) -> dict:
    """Returns a structure grouping evidence by (category, capability) -> brand -> row."""
    brands = sorted({r.brand for r in rows})
    cells: dict[tuple[str, str], dict[str, EvidenceRow]] = defaultdict(dict)
    for r in rows:
        cells[(r.category, r.capability)][r.brand] = r

    cap_keys = sorted(cells.keys(), key=lambda ck: (_category_sort_key(ck[0]), _capability_sort_key(ck[0], ck[1])))
    return {"brands": brands, "cap_keys": cap_keys, "cells": cells}


def category_coverage(matrix: dict) -> list[dict]:
    """How much of the full taxonomy has at least one researched capability, per category."""
    present: dict[str, set] = defaultdict(set)
    for category, capability in matrix["cap_keys"]:
        present[category].add(capability)

    out = []
    for category in CATEGORY_ORDER:
        out.append({
            "category": category,
            "researched": len(present.get(category, ())),
            "in_taxonomy": len(TAXONOMY.get(category, [])),
        })
    for category in sorted(c for c in present if c not in TAXONOMY):
        out.append({"category": category, "researched": len(present[category]), "in_taxonomy": None})
    return out


def novelty_label(confirmed_count: int, sample_size: int) -> str:
    if sample_size == 0:
        return "Not confirmed"
    pct = confirmed_count / sample_size
    if pct >= 0.75:
        return "Table Stakes"
    if pct >= 0.25:
        return "Developing"
    return "Distinctive"


def novelty_summary(matrix: dict) -> list[dict]:
    brands = matrix["brands"]
    n = len(brands)
    out = []
    for (category, capability) in matrix["cap_keys"]:
        row_cells = matrix["cells"][(category, capability)]
        confirmed = [b for b in brands if row_cells.get(b) and row_cells[b].is_confirmed()]
        advanced = [b for b in brands if row_cells.get(b) and row_cells[b].is_advanced()]
        out.append({
            "category": category,
            "capability": capability,
            "confirmed_brands": confirmed,
            "confirmed_count": len(confirmed),
            "sample_size": n,
            "novelty": novelty_label(len(confirmed), n),
            "advanced_brands": advanced,
        })
    return out


def coverage_summary(rows: list[EvidenceRow]) -> dict:
    by_brand: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        by_brand[r.brand][r.status or "Unstated"] += 1
        by_brand[r.brand]["__total__"] += 1
    return dict(by_brand)


def _score_cell_md(row: EvidenceRow | None) -> str:
    if row is None:
        return "–"
    kind = row.score_kind()
    label = {"numeric": row.maturity_score, "unknown": "?", "na": "N/A", "blank": "?"}[kind]
    if row.is_advanced():
        label += "★"
    return label


def _fmt_score(v) -> str:
    return "n/a" if v is None else f"{v:.1f}"


def _positioning_markdown(pos: dict) -> str:
    focus = pos["focus_brand"]
    lines = [f"\n## Competitive positioning: {focus}\n"]
    lines.append(f"Benchmarked against: {', '.join(pos['competitors'])}.\n")

    lines.append("\n### Standing in this sample\n")
    cov_rank = pos["coverage_rank"].index(focus) + 1
    counts_by_brand = pos["confirmed_count"]
    counts_str = ", ".join(f"{b}: {counts_by_brand.get(b, 0)}" for b in pos["coverage_rank"])
    lines.append(f"- Confirmed capabilities: {counts_by_brand.get(focus, 0)} "
                 f"— rank {cov_rank} of {len(pos['coverage_rank'])} brands by count ({counts_str})")
    if focus in pos["avg_score_rank"]:
        avg_rank = pos["avg_score_rank"].index(focus) + 1
        lines.append(f"- Average maturity score (evaluated capabilities only): "
                     f"{_fmt_score(pos['overall_avg'].get(focus))} — rank {avg_rank} of {len(pos['avg_score_rank'])}")

    lines.append("\n### Average maturity score by category\n")
    all_brands = [focus] + pos["competitors"]
    lines.append("| Category | " + " | ".join(all_brands) + " |")
    lines.append("|---|" + "---|" * len(all_brands))
    for category, brand_avgs in pos["category_avg"].items():
        cells = [_fmt_score(brand_avgs.get(b)) for b in all_brands]
        lines.append(f"| {category} | " + " | ".join(cells) + " |")

    def fmt_lead(item):
        vs = (f"{item['best_competitor']} at {item['best_competitor_score']}"
              if item["best_competitor"] else "no competitor evidence")
        return (f"- **{item['capability']}** ({item['category']}): {focus} scores {item['focus_score']} "
                f"vs {vs}")

    def fmt_gap(item):
        fs = item["focus_score"] if item["focus_score"] is not None else "not confirmed"
        return (f"- **{item['capability']}** ({item['category']}): {item['best_competitor']} scores "
                f"{item['best_competitor_score']}, {focus} is at {fs}")

    top_leads = pos["leads"][:8]
    if top_leads:
        lines.append(f"\n### Where {focus} already leads ({len(pos['leads'])} total)\n")
        for it in top_leads:
            lines.append(fmt_lead(it))

    top_gaps = pos["gaps"][:8]
    if top_gaps:
        lines.append(f"\n### Priority gaps vs competitors ({len(pos['gaps'])} total)\n")
        for it in top_gaps:
            lines.append(fmt_gap(it))

    if pos["competitor_advanced_edge"]:
        lines.append(f"\n### Depth gaps (competitor evidenced as ★ advanced, {focus} is not)\n")
        for it in pos["competitor_advanced_edge"]:
            lines.append(f"- **{it['capability']}** ({it['category']}): {', '.join(it['brands'])}")

    if pos["focus_advanced_edge"]:
        lines.append(f"\n### {focus}'s independently evidenced advanced-depth capabilities\n")
        for it in pos["focus_advanced_edge"]:
            lines.append(f"- **{it['capability']}** ({it['category']})")

    if len(pos["leads"]) > 8 or len(pos["gaps"]) > 8:
        lines.append(f"\nFull lead/gap lists: {len(pos['leads'])} leads, {len(pos['gaps'])} gaps — "
                      "see the evidence CSV for the complete set; only the largest score deltas are shown above.\n")

    return "\n".join(lines) + "\n"


def to_markdown(snapshot_id: str, rows: list[EvidenceRow], matrix: dict, novelty: list[dict],
                 warnings: list[str], previous_id: str | None = None, positioning: dict | None = None) -> str:
    brands = matrix["brands"]
    lines: list[str] = []
    lines.append(f"# Indonesia Automotive Digital Benchmark — {snapshot_id}\n")
    lines.append(f"Brands covered: {', '.join(brands) if brands else '(none)'}\n")
    lines.append(f"Evidence rows: {len(rows)}\n")
    if previous_id:
        lines.append(f"Compared against previous snapshot: `{previous_id}` (see diff_from_previous.md)\n")

    coverage = category_coverage(matrix)
    researched = [c for c in coverage if c["researched"] > 0]
    not_started = [c["category"] for c in coverage if c["researched"] == 0 and c["in_taxonomy"] is not None]
    lines.append(f"\nFramework coverage: {len(researched)} of {len(CATEGORY_ORDER)} taxonomy categories have at "
                 "least one researched capability so far.")
    if not_started:
        lines.append(f"Not yet researched: {', '.join(not_started)}.\n")

    lines.append("\nScore key:\n")
    lines.append("- `0` not found — searched, confirmed absent")
    lines.append("- `1` informational / outbound contact only")
    lines.append("- `2` interactive tool with an observed result")
    lines.append("- `3` result carried into a next step (dealer, finance, account, order)")
    lines.append("- `4` completed and tracked outcome")
    lines.append("- `?` unknown — could not be verified")
    lines.append("- `N/A` not applicable to this brand (e.g. no EV in lineup)")
    lines.append("- `–` not yet researched for this brand")
    lines.append("- `★` independently evidenced advanced functional depth\n")

    if positioning:
        lines.append(_positioning_markdown(positioning))

    # Coverage
    lines.append("\n## Coverage by brand\n")
    cov = coverage_summary(rows)
    lines.append("| Brand | Confirmed | Partial | Not found | Unknown | Total rows |")
    lines.append("|---|---|---|---|---|---|")
    for b in brands:
        c = cov.get(b, {})
        lines.append(f"| {b} | {c.get('Confirmed', 0)} | {c.get('Partial', 0)} | "
                      f"{c.get('Not found', 0)} | {c.get('Unknown', 0)} | {c.get('__total__', 0)} |")

    # Matrix grouped by category
    lines.append("\n## Capability matrix\n")
    current_category = None
    for (category, capability) in matrix["cap_keys"]:
        if category != current_category:
            lines.append(f"\n### {category}\n")
            lines.append("| Capability | " + " | ".join(brands) + " |")
            lines.append("|---|" + "---|" * len(brands))
            current_category = category
        row_cells = matrix["cells"][(category, capability)]
        cells_md = [_score_cell_md(row_cells.get(b)) for b in brands]
        lines.append(f"| {capability} | " + " | ".join(cells_md) + " |")

    # Novelty
    lines.append("\n## Novelty classification\n")
    lines.append(f"Sample size: {len(brands)} brand(s). "
                  "Table Stakes = confirmed in ≥75% of the sample, "
                  "Developing = 25–75%, Distinctive = <25%. "
                  "Advanced (★) marks independently evidenced functional depth and can accompany any label.\n")
    by_label: dict[str, list[dict]] = defaultdict(list)
    for n in novelty:
        by_label[n["novelty"]].append(n)
    for label in ("Table Stakes", "Developing", "Distinctive", "Not confirmed"):
        items = by_label.get(label, [])
        if not items:
            continue
        lines.append(f"\n### {label} ({len(items)})\n")
        for it in items:
            who = f" — {', '.join(it['confirmed_brands'])}" if it["confirmed_brands"] else ""
            adv = f" [advanced: {', '.join(it['advanced_brands'])}]" if it["advanced_brands"] else ""
            lines.append(f"- **{it['capability']}** ({it['category']}): "
                          f"{it['confirmed_count']}/{it['sample_size']}{who}{adv}")

    if warnings:
        lines.append(f"\n## Data quality notes ({len(warnings)})\n")
        lines.append("Non-blocking issues flagged during ingest — review before treating findings as final.\n")
        for w in warnings:
            lines.append(f"- {w}")

    lines.append("\n## Sources\n")
    lines.append("Full evidence register: `data/snapshots/"
                  f"{snapshot_id}/evidence.csv`. Deduped URL list for tracking-tool import: "
                  f"`reports/{snapshot_id}/urls.csv`.\n")

    return "\n".join(lines) + "\n"


def _score_class(row: EvidenceRow | None) -> tuple[str, str]:
    if row is None:
        return "cell-blank", "–"
    kind = row.score_kind()
    if kind == "numeric":
        n = row.score_numeric()
        return f"score-{n}", str(n)
    if kind == "unknown":
        return "cell-unknown", "?"
    if kind == "na":
        return "cell-na", "N/A"
    return "cell-blank", "–"


def _e(s) -> str:
    return html.escape(str(s)) if s is not None else ""


def to_html(snapshot_id: str, rows: list[EvidenceRow], matrix: dict, novelty: list[dict],
            previous_id: str | None = None, all_positioning: dict | None = None) -> str:
    brands = matrix["brands"]
    coverage = category_coverage(matrix)

    table_rows = []
    for (category, capability) in matrix["cap_keys"]:
        row_cells = matrix["cells"][(category, capability)]
        for b in brands:
            r = row_cells.get(b)
            cls, label = _score_class(r)
            table_rows.append({
                "category": category,
                "capability": capability,
                "brand": b,
                "status": r.status if r else "Not researched",
                "score_class": cls,
                "score_label": label,
                "advanced": bool(r and r.is_advanced()),
                "description": r.short_description if r else "",
                "value": r.customer_value if r else "",
                "url": r.url if r else "",
                "confidence": r.confidence if r else "",
                "score": r.score_numeric() if r else None,
                "score_kind": r.score_kind() if r else "blank",
                "how": r.how_it_works if r else "",
                "limitations": r.limitations if r else "",
                "date": r.date_accessed if r else "",
                "page_title": r.page_title if r else "",
                "method": r.method if r else "",
            })

    data_json = json.dumps({
        "snapshot": snapshot_id,
        "previous": previous_id,
        "brands": brands,
        "rows": table_rows,
        "novelty": novelty,
        "categoryCoverage": coverage,
    })

    title = f"Indonesia Automotive Digital Benchmark — {html.escape(snapshot_id)}"
    return (_HTML_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__DATA__", data_json))


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --bg: #faf9f7; --panel: #ffffff; --fg: #262421; --muted: #85807a; --border: #eae6e0;
    --border-soft: #f1eee9; --accent: #3d6b63; --accent-soft: #e4efec;
    --s0: #f0ede8; --s0-fg: #857e74;
    --s1: #d9ece5; --s1-fg: #2f5348;
    --s2: #a9d6c6; --s2-fg: #1f4237;
    --s3: #5fa895; --s3-fg: #ffffff;
    --s4: #2f6f63; --s4-fg: #ffffff;
    --unknown: #f3dfae; --unknown-fg: #6b5321;
    --na: #ece8f2; --na-fg: #726b85;
    --blank: transparent; --blank-fg: #c7c2ba;
    --hl: #c62828;
    --shadow: 0 1px 2px rgba(40,35,25,.04), 0 6px 20px rgba(40,35,25,.05);
    --radius: 14px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #17181a; --panel: #1e2022; --fg: #eae7e1; --muted: #9a958c; --border: #2b2d2f;
      --border-soft: #232527; --accent: #7cbcae; --accent-soft: #1d2e2a;
      --s0: #232527; --s0-fg: #8a857c;
      --s1: #1e332c; --s1-fg: #9fd7c4;
      --s2: #24493c; --s2-fg: #bfe9d8;
      --s3: #3d8a76; --s3-fg: #ffffff;
      --s4: #58b39d; --s4-fg: #0c1a16;
      --unknown: #4a3d1e; --unknown-fg: #e8cf8e;
      --na: #2a2733; --na-fg: #b6adc9;
      --blank: transparent; --blank-fg: #45423d;
      --hl: #ef5350;
      --shadow: 0 1px 2px rgba(0,0,0,.2), 0 8px 24px rgba(0,0,0,.28);
    }
  }
  * { box-sizing: border-box; }
  body {
    background: var(--bg); color: var(--fg); margin: 0; padding: 28px 20px 80px;
    font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif;
    max-width: 1180px; margin-left: auto; margin-right: auto;
  }
  h1 { font-size: 22px; font-weight: 650; margin: 0 0 2px; letter-spacing: -.01em; }
  h2 { font-size: 16px; font-weight: 650; margin: 0 0 12px; letter-spacing: -.005em; }
  h3 { font-size: 12px; font-weight: 650; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); margin: 18px 0 8px; }
  .meta { color: var(--muted); margin-bottom: 22px; font-size: 13px; }
  .muted { color: var(--muted); }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }

  .card {
    background: var(--panel); border: 1px solid var(--border-soft); border-radius: var(--radius);
    box-shadow: var(--shadow); padding: 20px 22px; margin-bottom: 20px;
  }

  .stats { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 22px; }
  .stat {
    flex: 1 1 140px; background: var(--panel); border: 1px solid var(--border-soft); border-radius: var(--radius);
    box-shadow: var(--shadow); padding: 14px 16px;
  }
  .stat .n { font-size: 22px; font-weight: 650; letter-spacing: -.01em; }
  .stat .l { font-size: 12px; color: var(--muted); margin-top: 2px; }

  .catstrip { display: flex; flex-wrap: wrap; gap: 8px; }
  .catpill {
    font-size: 12px; padding: 5px 11px; border-radius: 999px; border: 1px solid var(--border-soft);
    background: var(--s0); color: var(--s0-fg); white-space: nowrap;
  }
  .catpill.has-data { background: var(--accent-soft); color: var(--accent); border-color: transparent; font-weight: 600; }

  .legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--muted); align-items: center; }
  .swatch { display: inline-block; width: 13px; height: 13px; border-radius: 4px; margin-right: 5px; vertical-align: -2px; border: 1px solid var(--border-soft); }
  .star { color: #b8863f; }

  select, input[type=text] {
    background: var(--panel); color: var(--fg); border: 1px solid var(--border); border-radius: 9px;
    padding: 8px 12px; font-size: 13px; font-family: inherit;
  }
  select:focus, input:focus { outline: none; border-color: var(--accent); }

  .controls { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }

  .heatwrap { overflow-x: auto; }
  table.heat { border-collapse: separate; border-spacing: 0 6px; width: 100%; font-size: 13px; }
  table.heat th { text-align: left; font-weight: 600; color: var(--muted); font-size: 12px; padding: 0 10px 6px; }
  table.heat td.cap { padding: 10px 12px; background: var(--panel); border: 1px solid var(--border-soft);
    border-radius: 10px 0 0 10px; border-right: none; font-weight: 500; white-space: nowrap; }
  table.heat td.score {
    text-align: center; font-weight: 650; width: 64px; border: 1px solid var(--border-soft); border-left: none; border-right: none;
    background: var(--panel);
  }
  table.heat td.score:last-child { border-radius: 0 10px 10px 0; border-right: 1px solid var(--border-soft); }
  .cellchip { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 26px; border-radius: 7px; font-size: 12.5px; }
  .score-0 .cellchip { background: var(--s0); color: var(--s0-fg); }
  .score-1 .cellchip { background: var(--s1); color: var(--s1-fg); }
  .score-2 .cellchip { background: var(--s2); color: var(--s2-fg); }
  .score-3 .cellchip { background: var(--s3); color: var(--s3-fg); }
  .score-4 .cellchip { background: var(--s4); color: var(--s4-fg); }
  .cell-unknown .cellchip { background: var(--unknown); color: var(--unknown-fg); }
  .cell-na .cellchip { background: var(--na); color: var(--na-fg); font-size: 10px; }
  .cell-blank .cellchip { background: var(--blank); color: var(--blank-fg); border: 1px dashed var(--border); }
  .cellchip.score-0 { background: var(--s0); color: var(--s0-fg); }
  .cellchip.score-1 { background: var(--s1); color: var(--s1-fg); }
  .cellchip.score-2 { background: var(--s2); color: var(--s2-fg); }
  .cellchip.score-3 { background: var(--s3); color: var(--s3-fg); }
  .cellchip.score-4 { background: var(--s4); color: var(--s4-fg); }
  .cellchip.cell-unknown { background: var(--unknown); color: var(--unknown-fg); }
  .cellchip.cell-na { background: var(--na); color: var(--na-fg); font-size: 10px; }
  .cellchip.cell-blank { background: var(--blank); color: var(--blank-fg); border: 1px dashed var(--border); }
  table.heat th.hl-col-header { color: var(--hl); font-weight: 700; }
  table.heat td.score.hl-col { border-top: 1.5px solid var(--hl); border-bottom: 1.5px solid var(--hl); box-shadow: inset 1.5px 0 0 var(--hl), inset -1.5px 0 0 var(--hl); }

  details.catgroup { margin-bottom: 10px; }
  details.catgroup > summary {
    cursor: pointer; list-style: none; font-weight: 650; font-size: 13.5px; padding: 10px 4px;
    display: flex; align-items: center; gap: 8px; user-select: none;
  }
  details.catgroup > summary::-webkit-details-marker { display: none; }
  details.catgroup > summary::before { content: "\\25B8"; color: var(--muted); font-size: 11px; transition: transform .15s; }
  details.catgroup[open] > summary::before { transform: rotate(90deg); }
  details.catgroup > summary .count { color: var(--muted); font-weight: 400; font-size: 12px; }

  .posPanel { min-height: 60px; }
  .posEmpty { color: var(--muted); font-size: 13.5px; padding: 10px 2px; }
  .posGrid { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; margin-top: 6px; }
  @media (max-width: 720px) { .posGrid { grid-template-columns: 1fr; } }
  .posGrid ul { margin: 4px 0; padding-left: 18px; }
  .posGrid li { margin: 4px 0; }
  table.posTable { border-collapse: collapse; width: auto; min-width: 60%; font-size: 13px; margin-top: 4px; }
  table.posTable th, table.posTable td { padding: 5px 12px 5px 0; text-align: left; }
  table.posTable th { color: var(--muted); font-weight: 600; font-size: 12px; }

  table.evidence { border-collapse: collapse; width: 100%; font-size: 12.5px; }
  table.evidence th, table.evidence td { border-bottom: 1px solid var(--border-soft); padding: 7px 10px; text-align: left; vertical-align: top; }
  table.evidence th { cursor: pointer; position: sticky; top: 0; background: var(--panel); user-select: none; color: var(--muted); font-weight: 600; }
  table.evidence th.sorted::after { content: " \\2195"; }
  table.evidence td.desc { color: var(--muted); max-width: 340px; }

  .sectionTitle { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }

  .lede { color: var(--muted); font-size: 13.5px; margin: 0 0 16px; max-width: 78ch; }
  .ladder { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
  @media (max-width: 900px) { .ladder { grid-template-columns: 1fr; } }
  .rung { border: 1px solid var(--border-soft); border-radius: 12px; padding: 12px 13px; background: var(--panel); }
  .rung .top { display: flex; align-items: center; gap: 9px; margin-bottom: 6px; }
  .rung .name { font-weight: 650; font-size: 13.5px; }
  .rung .can { font-size: 13px; }
  .rung .ex { font-size: 12px; color: var(--muted); margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border); }
  .rung .ex b { color: var(--fg); font-weight: 600; }
  .rung .ex button { all: unset; cursor: pointer; color: var(--accent); }
  .rung .ex button:hover, .rung .ex button:focus-visible { text-decoration: underline; }
  .extras { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 10px; margin-top: 12px; }
  .extra { border: 1px solid var(--border-soft); border-radius: 12px; padding: 11px 13px; font-size: 13px; }
  .extra .top { display: flex; align-items: center; gap: 9px; margin-bottom: 4px; font-weight: 650; }
  .extra p { margin: 0; color: var(--muted); }
  .extra.wide { grid-column: 1 / -1; }
  .ovl { display: flex; flex-direction: column; font-size: 11.5px; color: var(--muted); gap: 3px; }
  .ovl.chk { flex-direction: row; align-items: center; gap: 6px; font-size: 13px; color: var(--fg); align-self: flex-end; padding-bottom: 8px; }
  .ovsum { background: var(--accent-soft); border-radius: 12px; padding: 12px 14px; font-size: 13.5px; margin-bottom: 14px; }
  table.ovtable { border-collapse: collapse; width: 100%; font-size: 13px; }
  table.ovtable th { text-align: left; color: var(--muted); font-size: 12px; font-weight: 600; padding: 4px 10px 8px; }
  table.ovtable td { padding: 8px 10px; border-top: 1px solid var(--border-soft); vertical-align: middle; }
  table.ovtable tbody tr { cursor: pointer; }
  table.ovtable tbody tr:hover, table.ovtable tbody tr:focus-visible { background: var(--s0); outline: none; }
  table.ovtable .cellchip { margin-right: 4px; }
  tr.ov-behind td:last-child { color: var(--hl); font-weight: 600; }
  tr.ov-ahead td:last-child { color: var(--accent); font-weight: 600; }
  button.capbtn { all: unset; cursor: pointer; font-weight: 500; }
  button.capbtn:hover, button.capbtn:focus-visible { color: var(--accent); text-decoration: underline; }
  .cmpicon { color: var(--muted); font-size: 12px; }
  .btn { background: var(--accent-soft); color: var(--accent); border: 1px solid transparent; border-radius: 9px; padding: 8px 12px; font: inherit; font-weight: 600; cursor: pointer; }
  .btn:hover, .btn:focus-visible { border-color: var(--accent); outline: none; }
  .cmpbar { margin-top: 18px; }
  .cmp { display: none; position: fixed; inset: 3vh 3vw; background: var(--bg); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow); z-index: 60; overflow: auto; padding: 20px 22px 30px; }
  .cmp.open { display: block; }
  .cmphead { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; margin-bottom: 14px; position: relative; padding-right: 34px; }
  .cmphead h2 { margin: 0 8px 4px 0; font-size: 18px; }
  .cmphead label { display: flex; flex-direction: column; font-size: 11.5px; color: var(--muted); gap: 3px; }
  .cmphead .close { position: absolute; top: -4px; right: 0; background: none; border: none; color: var(--muted); font-size: 24px; cursor: pointer; }
  .cmpsum { background: var(--accent-soft); border-radius: 12px; padding: 12px 14px; font-size: 13.5px; margin-bottom: 16px; }
  .cmpgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }
  @media (max-width: 820px) { .cmpgrid { grid-template-columns: 1fr; } .cmp { inset: 0; border-radius: 0; } }
  .cmpcol { background: var(--panel); border: 1px solid var(--border-soft); border-radius: 14px; padding: 16px 18px; }
  .cmpcol.lead { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
  .cmpcol h2 { font-size: 16px; }
  .cmpcol .verdict .cellchip { width: 40px; height: 34px; font-size: 16px; }
  .tip { font-size: 12.5px; color: var(--muted); margin-top: 12px; }

  td.score { cursor: pointer; }
  td.score:hover .cellchip, td.score:focus-visible .cellchip { outline: 2px solid var(--accent); outline-offset: 1px; }
  td.score:focus-visible { outline: none; }
  table.evidence tbody tr { cursor: pointer; }
  table.evidence tbody tr:hover { background: var(--s0); }

  .scrim { position: fixed; inset: 0; background: rgba(20,18,15,.35); opacity: 0; pointer-events: none; transition: opacity .15s; z-index: 40; }
  .scrim.open { opacity: 1; pointer-events: auto; }
  .drawer {
    position: fixed; top: 0; right: 0; height: 100%; width: min(460px, 100%); background: var(--panel);
    border-left: 1px solid var(--border); box-shadow: var(--shadow); z-index: 50; overflow-y: auto;
    padding: 22px 22px 40px; transform: translateX(105%); transition: transform .18s ease;
  }
  .drawer.open { transform: none; }
  .drawer .close { position: absolute; top: 12px; right: 14px; background: none; border: none; color: var(--muted); font-size: 22px; cursor: pointer; line-height: 1; }
  .drawer .crumb { font-size: 12px; color: var(--muted); margin-bottom: 2px; }
  .drawer h2 { margin: 0 0 12px; font-size: 18px; }
  .drawer .verdict { display: flex; gap: 12px; align-items: center; margin-bottom: 14px; }
  .drawer .verdict .cellchip { width: 44px; height: 38px; font-size: 18px; border-radius: 10px; }
  .drawer .verdict .vt { font-weight: 650; font-size: 14.5px; }
  .drawer .verdict .vs { font-size: 12.5px; color: var(--muted); }
  .drawer h3 { margin: 16px 0 5px; }
  .drawer p { margin: 0 0 6px; font-size: 13.5px; }
  .drawer .next { background: var(--accent-soft); border-radius: 10px; padding: 10px 12px; font-size: 13px; }
  .drawer .caveat { background: var(--unknown); color: var(--unknown-fg); border-radius: 10px; padding: 10px 12px; font-size: 13px; }
  .drawer dl { display: grid; grid-template-columns: auto 1fr; gap: 3px 12px; font-size: 12.5px; margin: 0; }
  .drawer dt { color: var(--muted); }
  .drawer dd { margin: 0; word-break: break-word; }
  .pill { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11.5px; font-weight: 600; background: var(--s0); color: var(--s0-fg); }
  .pill.High { background: var(--s3); color: var(--s3-fg); } .pill.Medium { background: var(--s2); color: var(--s2-fg); } .pill.Low { background: var(--unknown); color: var(--unknown-fg); }
</style>
</head>
<body>
<h1>__TITLE__</h1>
<div class="meta" id="meta"></div>

<div class="stats" id="stats"></div>

<div class="card" id="howto">
  <h2>How to read the scores</h2>
  <p class="lede">Each cell rates how far a brand's website takes a customer with one capability, judged from what we could actually see and use on the live site. The number is about <b>depth of the experience</b>, not whether the feature exists. Each level below shows a real example from this study, and any cell in the matrix can be clicked to see the exact evidence behind its number.</p>
  <div class="ladder" id="ladder"></div>
  <div class="extras" id="extras"></div>
</div>

<div class="card">
  <h2>Framework coverage</h2>
  <div class="catstrip" id="catstrip"></div>
</div>

<div class="card">
  <div class="sectionTitle">
    <h2>Brand vs brand</h2>
    <div class="controls" style="margin:0">
      <label class="ovl">Brand A <select id="ovA"></select></label>
      <label class="ovl">Brand B <select id="ovB"></select></label>
      <label class="ovl chk"><input type="checkbox" id="ovDiff" checked> Only differences</label>
    </div>
  </div>
  <div class="ovsum" id="ovSummary"></div>
  <div class="heatwrap"><table class="ovtable" id="ovTable"></table></div>
  <div class="tip">Click a row for the full side-by-side evidence. A level-for-level result needs a verified score on both sides.</div>
</div>

<div class="card">
  <div class="sectionTitle"><h2>Capability heatmap</h2></div>
  <div class="legend" style="margin-bottom:14px;">
    <span><span class="swatch" style="background:var(--s0)"></span>0 not found</span>
    <span><span class="swatch" style="background:var(--s1)"></span>1 informational</span>
    <span><span class="swatch" style="background:var(--s2)"></span>2 interactive</span>
    <span><span class="swatch" style="background:var(--s3)"></span>3 integrated</span>
    <span><span class="swatch" style="background:var(--s4)"></span>4 completed</span>
    <span><span class="swatch" style="background:var(--unknown)"></span>? unknown</span>
    <span><span class="swatch" style="background:var(--na)"></span>N/A not applicable</span>
    <span><span class="swatch" style="border-style:dashed"></span>– not yet researched</span>
    <span class="star">★ advanced</span>
    <span><span class="swatch" style="border: 1.5px solid var(--hl); background: transparent;"></span>Mitsubishi (client)</span>
  </div>
  <div class="tip">Click any cell (or press Enter on it) to see what was observed, why it got that number, what would raise it, and the source page.</div>
  <div id="heatgroups"></div>
</div>

<div class="card">
  <div class="sectionTitle"><h2>Evidence explorer</h2></div>
  <div class="controls">
    <input type="text" id="q" placeholder="Filter capability or brand…">
    <select id="brandFilter"><option value="">All brands</option></select>
    <select id="categoryFilter"><option value="">All categories</option></select>
    <select id="statusFilter">
      <option value="">All statuses</option>
      <option>Confirmed</option><option>Partial</option>
      <option>Not found</option><option>Unknown</option><option>Not researched</option>
    </select>
  </div>
  <div class="heatwrap">
  <table class="evidence" id="tbl">
    <thead><tr>
      <th data-k="category">Category</th>
      <th data-k="capability">Capability</th>
      <th data-k="brand">Brand</th>
      <th data-k="score_label">Score</th>
      <th data-k="status">Status</th>
      <th data-k="description">Description</th>
      <th>Evidence</th>
    </tr></thead>
    <tbody></tbody>
  </table>
  </div>
</div>

<div class="scrim" id="scrim"></div>
<section class="cmp" id="cmp" role="dialog" aria-modal="true" aria-labelledby="cmpTitle"><div id="cmpBody"></div></section>
<aside class="drawer" id="drawer" role="dialog" aria-modal="true" aria-labelledby="dTitle" aria-hidden="true">
  <button class="close" id="dClose" aria-label="Close">&times;</button>
  <div id="dBody"></div>
</aside>

<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  var data = JSON.parse(document.getElementById('data').textContent);
  var rows = data.rows;
  // Client brand: gets a red column highlight in the heatmap so it's easy to spot among many
  // brand columns. Purely visual -- does not affect the neutral positioning switcher above.
  var HIGHLIGHT_BRAND = 'Mitsubishi';

  function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; }
  function fmtScore(v) { return (v === null || v === undefined) ? 'n/a' : v.toFixed(1); }
  rows.forEach(function (r, i) { r._i = i; });

  // ---- Scoring rubric: plain-language meaning of every number ----
  var LEVELS = [
    { n: 0, name: 'Not found', can: 'Nothing for the customer to use. We looked for this on the brand\\'s site and confirmed it is not there.',
      next: 'To reach 1, the brand would need to at least publish information about it, or give the customer a way to ask about it.' },
    { n: 1, name: 'Informational', can: 'The customer can read about it or is pointed elsewhere (a phone number, WhatsApp, a partner site), but there is no tool to use on the site.',
      next: 'To reach 2, the site would need an interactive tool that gives the customer a result, such as a working form with real choices, a filter, or a calculated figure.' },
    { n: 2, name: 'Interactive', can: 'The customer can use a tool on the site and see a result, for example compare models, pick a colour and see the car change, or get a price.',
      next: 'To reach 3, what the customer chose must carry into a next step, such as a dealer, a finance request, an account or an order, so they do not start again.' },
    { n: 3, name: 'Connected to a next step', can: 'What the customer sets up is carried forward: a chosen car goes into a quote, a dealer, a finance request or an order.',
      next: 'To reach 4, the journey must be finishable online with an outcome the customer can track, such as a confirmed booking or an order status.' },
    { n: 4, name: 'Completed and tracked', can: 'The customer can finish the task end to end online and follow the outcome (confirmation, status, history).',
      next: 'This is the top of the scale.' }
  ];
  var CONF = {
    High: 'We used it or read it first-hand on the live site.',
    Medium: 'We saw it, but did not use it end to end, or part of the evidence comes from the brand\\'s own documentation.',
    Low: 'Indirect or partial evidence, such as a single glimpse or a page that did not fully load.'
  };

  // ---- "How to read the scores" card, with a real example per level ----
  function pickExample(n) {
    var pool = rows.filter(function (r) { return r.score === n && r.score_kind === 'numeric'; });
    var rank = { High: 0, Medium: 1, Low: 2 };
    pool.sort(function (a, b) { return (rank[a.confidence] || 3) - (rank[b.confidence] || 3) || (a.brand + a.capability < b.brand + b.capability ? -1 : 1); });
    return pool[0] || null;
  }
  document.getElementById('ladder').innerHTML = LEVELS.map(function (L) {
    var ex = pickExample(L.n);
    var exHtml = ex ? '<div class="ex">Example: <button type="button" data-i="' + ex._i + '"><b>' + esc(ex.brand) + '</b> &middot; ' + esc(ex.capability) + '</button></div>' : '<div class="ex">No brand reaches this level in the current sample.</div>';
    return '<div class="rung score-' + L.n + '"><div class="top"><span class="cellchip">' + L.n + '</span><span class="name">' + esc(L.name) + '</span></div>' +
      '<div class="can">' + esc(L.can) + '</div>' + exHtml + '</div>';
  }).join('');
  var advEx = rows.filter(function (r) { return r.advanced && r.confidence === 'High'; })[0] || rows.filter(function (r) { return r.advanced; })[0];
  document.getElementById('extras').innerHTML =
    '<div class="extra"><div class="top"><span class="star">&#9733;</span> Advanced</div><p>Marks unusually deep functionality that we independently evidenced. It sits on top of the number and can appear with any score' +
      (advEx ? ' (e.g. <button type="button" data-i="' + advEx._i + '" style="all:unset;cursor:pointer;color:var(--accent)">' + esc(advEx.brand) + ' &middot; ' + esc(advEx.capability) + '</button>)' : '') + '.</p></div>' +
    '<div class="extra score-x cell-unknown"><div class="top"><span class="cellchip">?</span> Unknown</div><p>We could not verify it (page blocked, offline, or would not load in our session). This is not the same as absent, and needs a re-check.</p></div>' +
    '<div class="extra cell-na"><div class="top"><span class="cellchip">N/A</span> Not applicable</div><p>The capability does not apply to this brand, for example an EV charging map for a brand with no EV.</p></div>' +
    '<div class="extra cell-blank"><div class="top"><span class="cellchip">&ndash;</span> Not yet researched</div><p>We have not looked at this yet. It is not a finding.</p></div>' +
    '<div class="extra wide"><div class="top">Confidence</div><p><b>High</b>: ' + esc(CONF.High) + ' <b>Medium</b>: ' + esc(CONF.Medium) + ' <b>Low</b>: ' + esc(CONF.Low) + '</p></div>';

  // ---- Detail drawer: why this cell has this number ----
  var drawer = document.getElementById('drawer'), scrim = document.getElementById('scrim'), dBody = document.getElementById('dBody');
  var lastTrigger = null;
  function para(label, text) { return text ? '<h3>' + label + '</h3><p>' + esc(text) + '</p>' : ''; }
  function detailHtml(r, headId) {
    var chip = '<span class="cellchip ' + r.score_class + '">' + esc(r.score_label) + '</span>';
    var star = r.advanced ? ' <span class="star" title="Advanced">&#9733;</span>' : '';
    var title, sub, means = '', next = '';
    if (r.score_kind === 'numeric') {
      var L = LEVELS[r.score];
      title = 'Score ' + r.score + ' &mdash; ' + esc(L.name); sub = esc(r.status);
      means = '<h3>What this score means</h3><p>' + esc(L.can) + '</p>';
      next = '<h3>Why not higher</h3><div class="next">' + esc(L.next) + '</div>';
    } else if (r.score_kind === 'unknown') {
      title = 'Could not be verified'; sub = 'Unknown';
      means = '<h3>What this means</h3><p>We could not confirm whether this exists, so it is not counted as present or absent.</p>';
    } else if (r.score_kind === 'na') {
      title = 'Not applicable'; sub = 'N/A';
      means = '<h3>What this means</h3><p>This capability does not apply to this brand, so it is left out of the comparison.</p>';
    } else {
      title = 'Not yet researched'; sub = 'No finding yet';
      means = '<h3>What this means</h3><p>We have not looked at this capability for this brand yet. It is not a finding either way.</p>';
    }
    var adv = '';
    if (r.advanced) adv = '<h3>Why it also carries a &#9733;</h3><p>' + esc(r.value || 'Independently evidenced functional depth beyond the score level.') + '</p>';
    else if (r.value) adv = para('Why it matters to a customer', r.value);
    var src = r.url ? '<a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.page_title || r.url) + '</a>' : '&ndash;';
    var meta = r.score_kind === 'blank' ? '' :
      '<h3>Evidence</h3><dl><dt>Source</dt><dd>' + src + '</dd><dt>Checked</dt><dd>' + esc(r.date || '&ndash;') + '</dd>' +
      '<dt>How we checked</dt><dd>' + esc(r.method || 'Not recorded') + '</dd><dt>Confidence</dt><dd>' + (r.confidence ? '<span class="pill ' + esc(r.confidence) + '">' + esc(r.confidence) + '</span> ' + esc(CONF[r.confidence] || '') : '&ndash;') + '</dd></dl>';
    return '<div class="crumb">' + esc(r.category) + '</div><h2' + (headId ? ' id="' + headId + '"' : '') + '>' + esc(r.capability) + ' &middot; ' + esc(r.brand) + '</h2>' +
      '<div class="verdict">' + chip + '<div><div class="vt">' + title + star + '</div><div class="vs">' + sub + '</div></div></div>' +
      means +
      (r.score_kind === 'blank' ? '' : para('What we observed', r.description) + para('How it works', r.how)) +
      next + adv +
      (r.limitations ? '<h3>Caveats on this rating</h3><div class="caveat">' + esc(r.limitations) + '</div>' : '') + meta;
  }
  function openDetail(i, trigger) {
    var r = rows[i]; if (!r) return;
    lastTrigger = trigger || document.activeElement;
    var label = (r.brand === HIGHLIGHT_BRAND) ? 'Compare with another brand side by side' : 'Compare with ' + HIGHLIGHT_BRAND + ' side by side';
    var bar = '<div class="cmpbar"><button type="button" class="btn" data-cmp="1" data-cat="' + esc(r.category) + '" data-cap="' + esc(r.capability) + '" data-brand="' + esc(r.brand) + '">' + label + '</button></div>';
    dBody.innerHTML = detailHtml(r, 'dTitle') + bar;
    drawer.classList.add('open'); scrim.classList.add('open'); drawer.setAttribute('aria-hidden', 'false');
    document.getElementById('dClose').focus();
  }

  // ---- Side-by-side comparison ----
  var cmpEl = document.getElementById('cmp'), cmpBody = document.getElementById('cmpBody');
  var capList = [];
  rows.forEach(function (r) { var k = r.category + '||' + r.capability; if (capList.indexOf(k) === -1) capList.push(k); });
  var cmpState = { cap: null, a: HIGHLIGHT_BRAND, b: null };
  function cellFor(capKey, brand) {
    var hit = null;
    rows.some(function (r) { if (r.category + '||' + r.capability === capKey && r.brand === brand) { hit = r; return true; } return false; });
    return hit;
  }
  function bestOther(capKey, a) {
    var best = null, bs = -1;
    data.brands.forEach(function (b) {
      if (b === a) return;
      var r = cellFor(capKey, b);
      if (r && r.score_kind === 'numeric' && r.score > bs) { best = b; bs = r.score; }
    });
    return best || data.brands.filter(function (b) { return b !== a; })[0];
  }
  function kindLabel(r) {
    if (r.score_kind === 'numeric') return 'score ' + r.score + ' (' + LEVELS[r.score].name + ')';
    if (r.score_kind === 'unknown') return 'could not be verified';
    if (r.score_kind === 'na') return 'not applicable';
    return 'not yet researched';
  }
  function compareSummary(ra, rb) {
    if (ra.score_kind === 'numeric' && rb.score_kind === 'numeric') {
      var d = rb.score - ra.score;
      if (d === 0) return ra.brand + ' and ' + rb.brand + ' are at the same level (' + ra.score + ', ' + LEVELS[ra.score].name + '). Compare the details below for differences in depth.';
      var hi = d > 0 ? rb : ra, lo = d > 0 ? ra : rb, n = Math.abs(d);
      return hi.brand + ' is ' + n + ' level' + (n > 1 ? 's' : '') + ' ahead of ' + lo.brand + ' (' + hi.score + ' vs ' + lo.score + '). What separates them: ' + LEVELS[lo.score].next;
    }
    return ra.brand + ': ' + kindLabel(ra) + '. ' + rb.brand + ': ' + kindLabel(rb) + '. A level-for-level comparison needs a verified score on both sides.';
  }
  function optionsFor(list, sel, skip) {
    return list.filter(function (b) { return b !== skip; }).map(function (b) { return '<option' + (b === sel ? ' selected' : '') + '>' + esc(b) + '</option>'; }).join('');
  }
  function renderCompare() {
    var ra = cellFor(cmpState.cap, cmpState.a), rb = cellFor(cmpState.cap, cmpState.b);
    var capOpts = capList.map(function (k) {
      var parts = k.split('||');
      return '<option value="' + esc(k) + '"' + (k === cmpState.cap ? ' selected' : '') + '>' + esc(parts[1]) + ' (' + esc(parts[0]) + ')</option>';
    }).join('');
    var lead = (ra.score_kind === 'numeric' && rb.score_kind === 'numeric') ? (ra.score > rb.score ? 'a' : rb.score > ra.score ? 'b' : '') : '';
    cmpBody.innerHTML =
      '<div class="cmphead"><h2 id="cmpTitle">Compare</h2>' +
        '<label>Capability <select id="cmpCap">' + capOpts + '</select></label>' +
        '<label>Brand A <select id="cmpA">' + optionsFor(data.brands, cmpState.a, cmpState.b) + '</select></label>' +
        '<button type="button" class="btn" id="cmpSwap" title="Swap sides">&#8646;</button>' +
        '<label>Brand B <select id="cmpB">' + optionsFor(data.brands, cmpState.b, cmpState.a) + '</select></label>' +
        '<button class="close" id="cmpClose" aria-label="Close comparison">&times;</button></div>' +
      '<div class="cmpsum">' + esc(compareSummary(ra, rb)) + '</div>' +
      '<div class="cmpgrid"><div class="cmpcol' + (lead === 'a' ? ' lead' : '') + '">' + detailHtml(ra) + '</div>' +
      '<div class="cmpcol' + (lead === 'b' ? ' lead' : '') + '">' + detailHtml(rb) + '</div></div>';
  }
  function openCompare(capKey, a, b, trigger) {
    lastTrigger = trigger || document.activeElement;
    cmpState.cap = capKey; cmpState.a = a;
    cmpState.b = (b && b !== a) ? b : bestOther(capKey, a);
    drawer.classList.remove('open'); drawer.setAttribute('aria-hidden', 'true');
    renderCompare();
    cmpEl.classList.add('open'); scrim.classList.add('open');
    document.getElementById('cmpClose').focus();
  }
  function closeCompare() { cmpEl.classList.remove('open'); scrim.classList.remove('open'); if (lastTrigger && lastTrigger.focus) lastTrigger.focus(); }
  cmpEl.addEventListener('change', function (e) {
    var id = e.target.id;
    if (id === 'cmpCap') { cmpState.cap = e.target.value; }
    else if (id === 'cmpA') { cmpState.a = e.target.value; }
    else if (id === 'cmpB') { cmpState.b = e.target.value; }
    else return;
    renderCompare();
  });
  cmpEl.addEventListener('click', function (e) {
    if (e.target.closest('#cmpClose')) { closeCompare(); return; }
    if (e.target.closest('#cmpSwap')) { var t = cmpState.a; cmpState.a = cmpState.b; cmpState.b = t; renderCompare(); }
  });
  dBody.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-cmp]'); if (!b) return;
    var brand = b.getAttribute('data-brand'), capKey = b.getAttribute('data-cat') + '||' + b.getAttribute('data-cap');
    if (brand === HIGHLIGHT_BRAND) openCompare(capKey, HIGHLIGHT_BRAND, null, b);
    else openCompare(capKey, HIGHLIGHT_BRAND, brand, b);
  });
  function closeDetail() {
    drawer.classList.remove('open'); scrim.classList.remove('open'); drawer.setAttribute('aria-hidden', 'true');
    if (lastTrigger && lastTrigger.focus) lastTrigger.focus();
  }
  document.getElementById('dClose').addEventListener('click', closeDetail);
  scrim.addEventListener('click', function () { if (cmpEl.classList.contains('open')) closeCompare(); else closeDetail(); });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (cmpEl.classList.contains('open')) closeCompare(); else if (drawer.classList.contains('open')) closeDetail();
  });
  document.getElementById('howto').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-i]'); if (b) openDetail(+b.getAttribute('data-i'), b);
  });

  document.getElementById('meta').textContent =
    'Snapshot ' + data.snapshot + (data.previous ? ' (previous: ' + data.previous + ')' : '') +
    ' — ' + data.brands.length + ' brands, ' + rows.length + ' evidence cells';

  // Stats
  var capSet = {}; rows.forEach(function (r) { capSet[r.category + '|' + r.capability] = 1; });
  var confirmed = rows.filter(function (r) { return r.status === 'Confirmed'; }).length;
  var researchedCats = data.categoryCoverage.filter(function (c) { return c.researched > 0; }).length;
  var stats = [
    { n: data.brands.length, l: 'brands' },
    { n: Object.keys(capSet).length, l: 'capabilities researched' },
    { n: researchedCats + ' / ' + data.categoryCoverage.length, l: 'taxonomy categories touched' },
    { n: confirmed, l: 'confirmed findings' }
  ];
  document.getElementById('stats').innerHTML = stats.map(function (s) {
    return '<div class="stat"><div class="n">' + esc(s.n) + '</div><div class="l">' + esc(s.l) + '</div></div>';
  }).join('');

  // Category coverage strip
  document.getElementById('catstrip').innerHTML = data.categoryCoverage.map(function (c) {
    var cls = c.researched > 0 ? 'catpill has-data' : 'catpill';
    var label = c.category + (c.researched > 0 ? ' (' + c.researched + (c.in_taxonomy ? '/' + c.in_taxonomy : '') + ')' : '');
    return '<span class="' + cls + '">' + esc(label) + '</span>';
  }).join('');

  // Brand vs brand overview (opens the side-by-side comparer)
  var ovA = document.getElementById('ovA'), ovB = document.getElementById('ovB'), ovDiff = document.getElementById('ovDiff');
  var ovCaps = [];
  rows.forEach(function (r) { var k = r.category + '||' + r.capability; if (ovCaps.indexOf(k) === -1) ovCaps.push(k); });
  var ovIdx = {};
  rows.forEach(function (r) { ovIdx[r.category + '||' + r.capability + '||' + r.brand] = r; });
  function ovFill(sel, value) {
    sel.innerHTML = data.brands.map(function (b) { return '<option' + (b === value ? ' selected' : '') + '>' + esc(b) + '</option>'; }).join('');
  }
  var numericCount = {};
  rows.forEach(function (r) { if (r.score_kind === 'numeric') numericCount[r.brand] = (numericCount[r.brand] || 0) + 1; });
  var defaultA = data.brands.indexOf(HIGHLIGHT_BRAND) !== -1 ? HIGHLIGHT_BRAND : data.brands[0];
  var defaultB = data.brands.filter(function (b) { return b !== defaultA; }).sort(function (x, y) { return (numericCount[y] || 0) - (numericCount[x] || 0); })[0];
  ovFill(ovA, defaultA); ovFill(ovB, defaultB);
  function chipHtml(r) { return '<span class="cellchip ' + r.score_class + '">' + esc(r.score_label) + '</span>' + (r.advanced ? '<span class="star">&#9733;</span>' : ''); }
  function renderOverview() {
    var A = ovA.value, B = ovB.value;
    if (A === B) { document.getElementById('ovSummary').textContent = 'Pick two different brands.'; document.getElementById('ovTable').innerHTML = ''; return; }
    var items = ovCaps.map(function (k) {
      var ra = ovIdx[k + '||' + A], rb = ovIdx[k + '||' + B];
      var res = 'nc';
      if (ra && rb && ra.score_kind === 'numeric' && rb.score_kind === 'numeric') res = ra.score > rb.score ? 'ahead' : ra.score < rb.score ? 'behind' : 'tie';
      return { k: k, ra: ra, rb: rb, res: res, gap: (res === 'nc' || res === 'tie') ? 0 : Math.abs(ra.score - rb.score) };
    });
    var n = { ahead: 0, behind: 0, tie: 0, nc: 0 }, sa = 0, sb = 0, cmp = 0;
    items.forEach(function (it) { n[it.res]++; if (it.res !== 'nc') { sa += it.ra.score; sb += it.rb.score; cmp++; } });
    document.getElementById('ovSummary').innerHTML =
      '<b>' + esc(A) + '</b> is ahead on <b>' + n.ahead + '</b>, behind on <b>' + n.behind + '</b> and level on <b>' + n.tie + '</b> of ' + cmp + ' comparable capabilities' +
      (cmp ? ' (average level ' + (sa / cmp).toFixed(1) + ' vs ' + esc(B) + ' ' + (sb / cmp).toFixed(1) + ')' : '') + '. ' +
      n.nc + ' capabilities cannot be compared yet because one side is unverified, not applicable or not researched.';
    var order = { behind: 0, ahead: 1, tie: 2, nc: 3 };
    items.sort(function (x, y) { return order[x.res] - order[y.res] || y.gap - x.gap; });
    var shown = items.filter(function (it) { return !ovDiff.checked || it.res === 'ahead' || it.res === 'behind'; });
    var label = { ahead: A + ' ahead', behind: B + ' ahead', tie: 'Level', nc: 'Not comparable' };
    document.getElementById('ovTable').innerHTML =
      '<thead><tr><th>Capability</th><th>' + esc(A) + '</th><th>' + esc(B) + '</th><th>Result</th></tr></thead><tbody>' +
      (shown.map(function (it) {
        var parts = it.k.split('||');
        var txt = label[it.res] + (it.gap ? ' by ' + it.gap : '');
        return '<tr tabindex="0" class="ov-' + it.res + '" data-k="' + esc(it.k) + '"><td>' + esc(parts[1]) + ' <span class="muted">' + esc(parts[0]) + '</span></td><td>' + chipHtml(it.ra) + '</td><td>' + chipHtml(it.rb) + '</td><td>' + esc(txt) + '</td></tr>';
      }).join('') || '<tr><td colspan="4" class="muted">No differences to show.</td></tr>') + '</tbody>';
  }
  [ovA, ovB, ovDiff].forEach(function (el) { el.addEventListener('change', renderOverview); });
  document.getElementById('ovTable').addEventListener('click', function (e) {
    var tr = e.target.closest('tr[data-k]'); if (tr) openCompare(tr.getAttribute('data-k'), ovA.value, ovB.value, tr);
  });
  document.getElementById('ovTable').addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') return;
    var tr = e.target.closest('tr[data-k]'); if (tr) openCompare(tr.getAttribute('data-k'), ovA.value, ovB.value, tr);
  });
  renderOverview();

  // Heatmap grouped by category, collapsible
  var byCategory = {};
  var catOrder = [];
  rows.forEach(function (r) {
    var key = r.category;
    if (!byCategory[key]) { byCategory[key] = {}; catOrder.push(key); }
    var capKey = r.capability;
    if (!byCategory[key][capKey]) byCategory[key][capKey] = {};
    byCategory[key][capKey][r.brand] = r;
  });

  var heatHtml = catOrder.map(function (cat) {
    var caps = Object.keys(byCategory[cat]);
    var bodyRows = caps.map(function (cap) {
      var cells = data.brands.map(function (b) {
        var r = byCategory[cat][cap][b];
        var cls = r ? r.score_class : 'cell-blank';
        var label = r ? r.score_label : '–';
        var star = (r && r.advanced) ? '<span class="star">★</span>' : '';
        var title = r ? (r.brand + ' — ' + r.status + (r.description ? ': ' + r.description : '')) : (b + ' — not yet researched');
        var hl = (b === HIGHLIGHT_BRAND) ? ' hl-col' : '';
        var idx = r ? r._i : -1;
        return '<td class="score ' + cls + hl + '" tabindex="0" role="button" data-i="' + idx + '" aria-label="' + esc(b + ', ' + cap + ', score ' + label + '. Open explanation') + '" title="' + esc(title) + '"><span class="cellchip">' + esc(label) + '</span>' + star + '</td>';
      }).join('');
      return '<tr><td class="cap"><button type="button" class="capbtn" data-cat="' + esc(cat) + '" data-cap="' + esc(cap) + '" title="Compare ' + esc(HIGHLIGHT_BRAND) + ' with another brand on this capability">' + esc(cap) + ' <span class="cmpicon">&#8646;</span></button></td>' + cells + '</tr>';
    }).join('');
    var header = '<tr><th></th>' + data.brands.map(function (b) {
      var hl = (b === HIGHLIGHT_BRAND) ? ' hl-col-header' : '';
      return '<th class="' + hl.trim() + '">' + esc(b) + '</th>';
    }).join('') + '</tr>';
    return '<details class="catgroup" open><summary>' + esc(cat) + ' <span class="count">(' + caps.length + ')</span></summary>' +
      '<div class="heatwrap"><table class="heat">' + header + bodyRows + '</table></div></details>';
  }).join('');
  document.getElementById('heatgroups').innerHTML = heatHtml || '<div class="posEmpty">No evidence yet.</div>';
  var heatEl = document.getElementById('heatgroups');
  heatEl.addEventListener('click', function (e) {
    var cb = e.target.closest('button.capbtn');
    if (cb) { openCompare(cb.getAttribute('data-cat') + '||' + cb.getAttribute('data-cap'), HIGHLIGHT_BRAND, null, cb); return; }
    var td = e.target.closest('td.score[data-i]'); if (td && +td.getAttribute('data-i') >= 0) openDetail(+td.getAttribute('data-i'), td);
  });
  heatEl.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var td = e.target.closest('td.score[data-i]'); if (td && +td.getAttribute('data-i') >= 0) { e.preventDefault(); openDetail(+td.getAttribute('data-i'), td); }
  });

  // Evidence explorer
  var brandSel = document.getElementById('brandFilter');
  var catSel = document.getElementById('categoryFilter');
  Array.from(new Set(rows.map(function (r) { return r.brand; }))).sort().forEach(function (b) {
    var o = document.createElement('option'); o.textContent = b; brandSel.appendChild(o);
  });
  Array.from(new Set(rows.map(function (r) { return r.category; }))).forEach(function (c) {
    var o = document.createElement('option'); o.textContent = c; catSel.appendChild(o);
  });

  var sortKey = 'category', sortDir = 1;
  var tbody = document.querySelector('#tbl tbody');
  var q = document.getElementById('q');
  var statusSel = document.getElementById('statusFilter');

  function renderTable() {
    var query = q.value.toLowerCase();
    var brand = brandSel.value, cat = catSel.value, status = statusSel.value;
    var filtered = rows.filter(function (r) {
      if (brand && r.brand !== brand) return false;
      if (cat && r.category !== cat) return false;
      if (status && r.status !== status) return false;
      if (query && (r.capability + ' ' + r.brand + ' ' + r.description).toLowerCase().indexOf(query) === -1) return false;
      return true;
    });
    filtered.sort(function (a, b) {
      var av = a[sortKey], bv = b[sortKey];
      return av < bv ? -sortDir : av > bv ? sortDir : 0;
    });
    tbody.innerHTML = filtered.map(function (r) {
      var evidence = r.url ? '<a href="' + esc(r.url) + '" target="_blank" rel="noopener">source</a>' : '';
      var star = r.advanced ? ' <span class="star">★</span>' : '';
      return '<tr tabindex="0" data-i="' + r._i + '">' +
        '<td>' + esc(r.category) + '</td>' +
        '<td>' + esc(r.capability) + '</td>' +
        '<td>' + esc(r.brand) + '</td>' +
        '<td><span class="cellchip ' + r.score_class + '" style="display:inline-flex">' + esc(r.score_label) + '</span>' + star + '</td>' +
        '<td>' + esc(r.status) + '</td>' +
        '<td class="desc">' + esc(r.description) + '</td>' +
        '<td>' + evidence + '</td>' +
        '</tr>';
    }).join('');
  }

  document.querySelectorAll('th[data-k]').forEach(function (th) {
    th.addEventListener('click', function () {
      var k = th.getAttribute('data-k');
      if (sortKey === k) sortDir *= -1; else { sortKey = k; sortDir = 1; }
      document.querySelectorAll('th').forEach(function (t) { t.classList.remove('sorted'); });
      th.classList.add('sorted');
      renderTable();
    });
  });
  [q, brandSel, catSel, statusSel].forEach(function (el) { el.addEventListener('input', renderTable); });
  tbody.addEventListener('click', function (e) {
    if (e.target.closest('a')) return;
    var tr = e.target.closest('tr[data-i]'); if (tr) openDetail(+tr.getAttribute('data-i'), tr);
  });
  tbody.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') return;
    var tr = e.target.closest('tr[data-i]'); if (tr) openDetail(+tr.getAttribute('data-i'), tr);
  });

  renderTable();
})();
</script>
</body>
</html>
"""
