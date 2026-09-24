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
            })

    data_json = json.dumps({
        "snapshot": snapshot_id,
        "previous": previous_id,
        "brands": brands,
        "rows": table_rows,
        "novelty": novelty,
        "categoryCoverage": coverage,
        "positioning": all_positioning or {},
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
</style>
</head>
<body>
<h1>__TITLE__</h1>
<div class="meta" id="meta"></div>

<div class="stats" id="stats"></div>

<div class="card">
  <h2>Framework coverage</h2>
  <div class="catstrip" id="catstrip"></div>
</div>

<div class="card">
  <div class="sectionTitle">
    <h2>Explore a brand's positioning</h2>
    <select id="posBrand"><option value="">Select a brand…</option></select>
  </div>
  <div class="posPanel" id="posPanel"><div class="posEmpty">Pick a brand above to see its rank, category scores, leads and gaps versus the rest of the sample. No brand is selected by default — this view is neutral.</div></div>
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

  // Brand positioning switcher
  var posSel = document.getElementById('posBrand');
  data.brands.forEach(function (b) {
    var o = document.createElement('option'); o.value = b; o.textContent = b; posSel.appendChild(o);
  });
  posSel.addEventListener('change', function () { renderPositioning(posSel.value); });

  function renderPositioning(brand) {
    var panel = document.getElementById('posPanel');
    var pos = data.positioning[brand];
    if (!brand || !pos) {
      panel.innerHTML = '<div class="posEmpty">Pick a brand above to see its rank, category scores, leads and gaps versus the rest of the sample. No brand is selected by default — this view is neutral.</div>';
      return;
    }
    var allBrands = [brand].concat(pos.competitors);
    var covRank = pos.coverage_rank.indexOf(brand) + 1;
    var countsStr = pos.coverage_rank.map(function (b) { return esc(b) + ': ' + (pos.confirmed_count[b] || 0); }).join(', ');
    var avgRankStr = '';
    var avgIdx = pos.avg_score_rank.indexOf(brand);
    if (avgIdx !== -1) {
      avgRankStr = '<li>Average maturity score (evaluated capabilities only): ' + fmtScore(pos.overall_avg[brand]) +
        ' — rank ' + (avgIdx + 1) + ' of ' + pos.avg_score_rank.length + '</li>';
    }

    var catHeader = allBrands.map(function (b) { return '<th>' + esc(b) + '</th>'; }).join('');
    var catRows = Object.keys(pos.category_avg).map(function (cat) {
      var cells = allBrands.map(function (b) { return '<td>' + fmtScore(pos.category_avg[cat][b]) + '</td>'; }).join('');
      return '<tr><td>' + esc(cat) + '</td>' + cells + '</tr>';
    }).join('');

    function leadLi(it) {
      var vs = it.best_competitor ? (esc(it.best_competitor) + ' at ' + it.best_competitor_score) : 'no competitor evidence';
      return '<li><b>' + esc(it.capability) + '</b> <span class="muted">(' + esc(it.category) + ')</span>: ' +
        esc(brand) + ' scores ' + it.focus_score + ' vs ' + vs + '</li>';
    }
    function gapLi(it) {
      var fs = (it.focus_score === null || it.focus_score === undefined) ? 'not confirmed' : it.focus_score;
      return '<li><b>' + esc(it.capability) + '</b> <span class="muted">(' + esc(it.category) + ')</span>: ' +
        esc(it.best_competitor) + ' scores ' + it.best_competitor_score + ', ' + esc(brand) + ' is at ' + fs + '</li>';
    }
    var leadsHtml = pos.leads.slice(0, 8).map(leadLi).join('') || '<li class="muted">None found</li>';
    var gapsHtml = pos.gaps.slice(0, 8).map(gapLi).join('') || '<li class="muted">None found</li>';

    var depthHtml = '';
    if (pos.competitor_advanced_edge.length) {
      depthHtml = '<h3>Depth gaps (competitor evidenced as ★ advanced, ' + esc(brand) + ' is not)</h3><ul>' +
        pos.competitor_advanced_edge.map(function (it) {
          return '<li><b>' + esc(it.capability) + '</b> (' + esc(it.category) + '): ' + esc(it.brands.join(', ')) + '</li>';
        }).join('') + '</ul>';
    }

    panel.innerHTML =
      '<p class="muted">Benchmarked against: ' + esc(pos.competitors.join(', ')) + '.</p>' +
      '<ul><li>Confirmed capabilities: ' + (pos.confirmed_count[brand] || 0) + ' — rank ' + covRank + ' of ' +
        pos.coverage_rank.length + ' brands by count (' + countsStr + ')</li>' + avgRankStr + '</ul>' +
      '<h3>Average maturity score by category</h3>' +
      '<table class="posTable"><thead><tr><th>Category</th>' + catHeader + '</tr></thead><tbody>' + catRows + '</tbody></table>' +
      '<div class="posGrid">' +
        '<div><h3>Where ' + esc(brand) + ' leads (' + pos.leads.length + ')</h3><ul>' + leadsHtml + '</ul></div>' +
        '<div><h3>Priority gaps vs competitors (' + pos.gaps.length + ')</h3><ul>' + gapsHtml + '</ul></div>' +
      '</div>' + depthHtml;
  }

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
        return '<td class="score ' + cls + hl + '" title="' + esc(title) + '"><span class="cellchip">' + esc(label) + '</span>' + star + '</td>';
      }).join('');
      return '<tr><td class="cap">' + esc(cap) + '</td>' + cells + '</tr>';
    }).join('');
    var header = '<tr><th></th>' + data.brands.map(function (b) {
      var hl = (b === HIGHLIGHT_BRAND) ? ' hl-col-header' : '';
      return '<th class="' + hl.trim() + '">' + esc(b) + '</th>';
    }).join('') + '</tr>';
    return '<details class="catgroup" open><summary>' + esc(cat) + ' <span class="count">(' + caps.length + ')</span></summary>' +
      '<div class="heatwrap"><table class="heat">' + header + bodyRows + '</table></div></details>';
  }).join('');
  document.getElementById('heatgroups').innerHTML = heatHtml || '<div class="posEmpty">No evidence yet.</div>';

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
      return '<tr>' +
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

  renderTable();
})();
</script>
</body>
</html>
"""
