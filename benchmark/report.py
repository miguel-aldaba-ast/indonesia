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

SCORE_LABELS = {
    None: "?",
    0: "0",
    1: "1",
    2: "2",
    3: "3",
    4: "4",
}


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
    if row.status == "Not found":
        return "0" if row.maturity_score == "0" else "0?"
    label = row.maturity_score or "?"
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
    lines.append("\nScore key: 0=not found, 1=informational, 2=interactive/calculated, "
                  "3=integrated into next step, 4=completed/tracked, ?=unverified, "
                  "★=independently evidenced advanced depth, –=not evaluated.\n")

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
        return "na", "–"
    n = row.score_numeric()
    if n is None:
        return "unknown", row.maturity_score or "?"
    return f"score-{n}", str(n)


def _e(s) -> str:
    return html.escape(str(s)) if s is not None else ""


def _positioning_html(pos: dict) -> str:
    focus = pos["focus_brand"]
    all_brands = [focus] + pos["competitors"]

    cov_rank = pos["coverage_rank"].index(focus) + 1
    counts_by_brand = pos["confirmed_count"]
    counts_str = ", ".join(f"{_e(b)}: {counts_by_brand.get(b, 0)}" for b in pos["coverage_rank"])
    avg_rank_str = ""
    if focus in pos["avg_score_rank"]:
        r = pos["avg_score_rank"].index(focus) + 1
        avg_rank_str = (f"<li>Average maturity score (evaluated capabilities only): "
                         f"{_fmt_score(pos['overall_avg'].get(focus))} — rank {r} of {len(pos['avg_score_rank'])}</li>")

    cat_rows = []
    for category, brand_avgs in pos["category_avg"].items():
        cells = "".join(f"<td>{_fmt_score(brand_avgs.get(b))}</td>" for b in all_brands)
        cat_rows.append(f"<tr><td>{_e(category)}</td>{cells}</tr>")
    cat_header = "".join(f"<th>{_e(b)}</th>" for b in all_brands)

    def lead_li(it):
        vs = (f"{_e(it['best_competitor'])} at {it['best_competitor_score']}"
              if it["best_competitor"] else "no competitor evidence")
        return (f"<li><b>{_e(it['capability'])}</b> <span class='muted'>({_e(it['category'])})</span>: "
                f"{_e(focus)} scores {it['focus_score']} vs {vs}</li>")

    def gap_li(it):
        fs = it["focus_score"] if it["focus_score"] is not None else "not confirmed"
        return (f"<li><b>{_e(it['capability'])}</b> <span class='muted'>({_e(it['category'])})</span>: "
                f"{_e(it['best_competitor'])} scores {it['best_competitor_score']}, {_e(focus)} is at {fs}</li>")

    leads_html = "".join(lead_li(it) for it in pos["leads"][:8]) or "<li class='muted'>None found</li>"
    gaps_html = "".join(gap_li(it) for it in pos["gaps"][:8]) or "<li class='muted'>None found</li>"

    depth_gap_html = ""
    if pos["competitor_advanced_edge"]:
        items = "".join(
            f"<li><b>{_e(it['capability'])}</b> ({_e(it['category'])}): {_e(', '.join(it['brands']))}</li>"
            for it in pos["competitor_advanced_edge"])
        depth_gap_html = f"<h3>Depth gaps (competitor evidenced as ★ advanced, {_e(focus)} is not)</h3><ul>{items}</ul>"

    return f"""
<section class="positioning">
  <h2>Competitive positioning: {_e(focus)}</h2>
  <p class="muted">Benchmarked against: {_e(', '.join(pos['competitors']))}.</p>
  <ul>
    <li>Confirmed capabilities: {counts_by_brand.get(focus, 0)} — rank {cov_rank} of
        {len(pos['coverage_rank'])} brands by count ({counts_str})</li>
    {avg_rank_str}
  </ul>
  <h3>Average maturity score by category</h3>
  <table class="posTable"><thead><tr><th>Category</th>{cat_header}</tr></thead>
    <tbody>{''.join(cat_rows)}</tbody></table>
  <div class="posCols">
    <div><h3>Where {_e(focus)} leads ({len(pos['leads'])})</h3><ul>{leads_html}</ul></div>
    <div><h3>Priority gaps vs competitors ({len(pos['gaps'])})</h3><ul>{gaps_html}</ul></div>
  </div>
  {depth_gap_html}
</section>
"""


def to_html(snapshot_id: str, rows: list[EvidenceRow], matrix: dict, novelty: list[dict],
            previous_id: str | None = None, positioning: dict | None = None) -> str:
    brands = matrix["brands"]

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
                "status": r.status if r else "Not evaluated",
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
    })

    title = f"Indonesia Automotive Digital Benchmark — {html.escape(snapshot_id)}"
    positioning_html = _positioning_html(positioning) if positioning else ""
    return (_HTML_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__DATA__", data_json)
            .replace("__POSITIONING__", positioning_html))


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --bg: #ffffff; --fg: #1a1d21; --muted: #6b7280; --border: #e5e7eb;
    --s0: #f3f4f6; --s1: #dbeafe; --s2: #93c5fd; --s3: #3b82f6; --s4: #1d4ed8;
    --unknown: #fde68a; --na: #f9fafb;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#15171a; --fg:#e5e7eb; --muted:#9ca3af; --border:#2b2f36;
      --s0:#23262b; --s1:#1e3a5f; --s2:#2f5c9c; --s3:#3b82f6; --s4:#60a5fa;
      --unknown:#6b5b1e; --na:#1c1e22; }
  }
  * { box-sizing: border-box; }
  body { background: var(--bg); color: var(--fg); font: 14px/1.5 -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; padding: 24px 16px 64px; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  .meta { color: var(--muted); margin-bottom: 20px; font-size: 13px; }
  .controls { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
  select, input[type=text] { background: var(--bg); color: var(--fg); border: 1px solid var(--border); border-radius: 6px; padding: 6px 10px; font-size: 13px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { border: 1px solid var(--border); padding: 6px 8px; text-align: left; vertical-align: top; }
  th { cursor: pointer; position: sticky; top: 0; background: var(--bg); user-select: none; }
  th.sorted::after { content: " \\2195"; color: var(--muted); }
  td.score { text-align: center; font-weight: 600; width: 44px; }
  .score-0 { background: var(--s0); }
  .score-1 { background: var(--s1); }
  .score-2 { background: var(--s2); }
  .score-3 { background: var(--s3); color: #fff; }
  .score-4 { background: var(--s4); color: #fff; }
  .unknown { background: var(--unknown); }
  .na { background: var(--na); color: var(--muted); }
  .star { color: #b45309; }
  .desc { color: var(--muted); max-width: 360px; }
  a { color: inherit; }
  .legend { display:flex; gap:14px; flex-wrap:wrap; margin: 10px 0 18px; font-size: 12px; color: var(--muted); align-items:center; }
  .swatch { display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:4px; vertical-align:-1px; }
  .muted { color: var(--muted); }
  .positioning { border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; margin-bottom: 24px; }
  .positioning h2 { margin-top: 0; font-size: 17px; }
  .positioning h3 { font-size: 13px; text-transform: uppercase; letter-spacing: .02em; color: var(--muted); margin: 16px 0 6px; }
  .positioning ul { margin: 4px 0; padding-left: 20px; }
  .positioning li { margin: 3px 0; }
  .posTable { width: auto; min-width: 50%; }
  .posCols { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  @media (max-width: 700px) { .posCols { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<h1>__TITLE__</h1>
<div class="meta" id="meta"></div>
__POSITIONING__
<div class="legend">
  <span><span class="swatch score-0"></span>0 not found</span>
  <span><span class="swatch score-1"></span>1 informational</span>
  <span><span class="swatch score-2"></span>2 interactive/calculated</span>
  <span><span class="swatch score-3"></span>3 integrated into next step</span>
  <span><span class="swatch score-4"></span>4 completed/tracked</span>
  <span><span class="swatch unknown"></span>? unverified</span>
  <span><span class="swatch na"></span>– not evaluated</span>
  <span class="star">★ advanced</span>
</div>
<div class="controls">
  <input type="text" id="q" placeholder="Filter capability or brand...">
  <select id="brandFilter"><option value="">All brands</option></select>
  <select id="categoryFilter"><option value="">All categories</option></select>
  <select id="statusFilter">
    <option value="">All statuses</option>
    <option>Confirmed</option><option>Partial</option>
    <option>Not found</option><option>Unknown</option><option>Not evaluated</option>
  </select>
</div>
<table id="tbl">
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

<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  var data = JSON.parse(document.getElementById('data').textContent);
  var rows = data.rows;
  document.getElementById('meta').textContent =
    'Snapshot ' + data.snapshot + (data.previous ? ' (previous: ' + data.previous + ')' : '') +
    ' — ' + data.brands.length + ' brands, ' + rows.length + ' evidence cells';

  var brandSel = document.getElementById('brandFilter');
  var catSel = document.getElementById('categoryFilter');
  Array.from(new Set(rows.map(function(r){return r.brand;}))).sort().forEach(function(b){
    var o = document.createElement('option'); o.textContent = b; brandSel.appendChild(o);
  });
  Array.from(new Set(rows.map(function(r){return r.category;}))).forEach(function(c){
    var o = document.createElement('option'); o.textContent = c; catSel.appendChild(o);
  });

  var sortKey = 'category', sortDir = 1;
  var tbody = document.querySelector('#tbl tbody');
  var q = document.getElementById('q');
  var statusSel = document.getElementById('statusFilter');

  function esc(s) {
    var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML;
  }

  function render() {
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
        '<td class="score ' + r.score_class + '">' + esc(r.score_label) + star + '</td>' +
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
      document.querySelectorAll('th').forEach(function(t){t.classList.remove('sorted');});
      th.classList.add('sorted');
      render();
    });
  });
  [q, brandSel, catSel, statusSel].forEach(function (el) {
    el.addEventListener('input', render);
  });

  render();
})();
</script>
</body>
</html>
"""
