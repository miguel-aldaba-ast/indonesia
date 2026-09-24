"""Competitive positioning for one focus brand against the rest of the sample.

This is the "so what for us" layer on top of the raw matrix: category-level
scores, capability-level leads/gaps versus the strongest competitor, and
advanced-depth deltas. Built for presenting a benchmark back to the brand
being discussed, not just publishing a neutral comparison table.
"""

from __future__ import annotations

from collections import defaultdict

from .taxonomy import CATEGORY_ORDER


def _category_sort_key(category: str):
    if category in CATEGORY_ORDER:
        return (0, CATEGORY_ORDER.index(category))
    return (1, category)


def build_positioning(matrix: dict, focus_brand: str) -> dict | None:
    brands = matrix["brands"]
    if focus_brand not in brands:
        return None
    competitors = [b for b in brands if b != focus_brand]

    category_scores: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    leads, gaps = [], []
    focus_advanced_edge, competitor_advanced_edge = [], []

    confirmed_count = defaultdict(int)
    all_scores = defaultdict(list)

    for (category, capability) in matrix["cap_keys"]:
        cells = matrix["cells"][(category, capability)]

        for b in brands:
            r = cells.get(b)
            if r is None:
                continue
            if r.is_confirmed():
                confirmed_count[b] += 1
            s = r.score_numeric()
            if s is not None:
                category_scores[category][b].append(s)
                all_scores[b].append(s)

        focus_row = cells.get(focus_brand)
        focus_score = focus_row.score_numeric() if focus_row else None

        comp_scores = []
        for b in competitors:
            r = cells.get(b)
            s = r.score_numeric() if r else None
            if s is not None:
                comp_scores.append((b, s))
        best_competitor = max(comp_scores, key=lambda t: t[1]) if comp_scores else None

        if focus_score is not None and (best_competitor is None or focus_score > best_competitor[1]):
            delta = focus_score - (best_competitor[1] if best_competitor else -1)
            leads.append({
                "category": category, "capability": capability,
                "focus_score": focus_score,
                "best_competitor": best_competitor[0] if best_competitor else None,
                "best_competitor_score": best_competitor[1] if best_competitor else None,
                "delta": delta,
            })

        if best_competitor is not None and (focus_score is None or best_competitor[1] > focus_score):
            delta = best_competitor[1] - (focus_score if focus_score is not None else -1)
            gaps.append({
                "category": category, "capability": capability,
                "focus_score": focus_score,
                "best_competitor": best_competitor[0], "best_competitor_score": best_competitor[1],
                "delta": delta,
            })

        focus_adv = bool(focus_row and focus_row.is_advanced())
        comp_adv = [b for b in competitors if cells.get(b) and cells[b].is_advanced()]
        if focus_adv and not comp_adv:
            focus_advanced_edge.append({"category": category, "capability": capability})
        if comp_adv and not focus_adv:
            competitor_advanced_edge.append({"category": category, "capability": capability, "brands": comp_adv})

    category_avg = {}
    for category in sorted(category_scores.keys(), key=_category_sort_key):
        brand_avgs = {}
        for b, scores in category_scores[category].items():
            brand_avgs[b] = sum(scores) / len(scores)
        category_avg[category] = brand_avgs

    leads.sort(key=lambda x: (-x["delta"], x["category"]))
    gaps.sort(key=lambda x: (-x["delta"], x["category"]))

    overall_avg = {b: (sum(s) / len(s) if s else None) for b, s in all_scores.items()}
    coverage_rank = sorted(brands, key=lambda b: -confirmed_count.get(b, 0))
    avg_rank = sorted([b for b in brands if overall_avg.get(b) is not None],
                       key=lambda b: -overall_avg[b])

    return {
        "focus_brand": focus_brand,
        "competitors": competitors,
        "category_avg": category_avg,
        "leads": leads,
        "gaps": gaps,
        "focus_advanced_edge": focus_advanced_edge,
        "competitor_advanced_edge": competitor_advanced_edge,
        "confirmed_count": dict(confirmed_count),
        "overall_avg": overall_avg,
        "coverage_rank": coverage_rank,
        "avg_score_rank": avg_rank,
    }
