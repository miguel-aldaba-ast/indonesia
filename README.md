# Indonesia Automotive Digital Benchmark

A local, git-tracked system for benchmarking what automotive brand websites in
Indonesia actually let customers **do** (configure, price, finance, book a
test drive, book service, etc.) — not how they look. It's built to sit on top
of the `indonesia-auto-benchmark` Codex/Claude skill in this folder:

```
indonesia-automotive-digital-benchmark (1)/skills/indonesia-auto-benchmark/
```

That skill defines the research method: a 14-category capability taxonomy, a
0–4 maturity scoring scale, a Confirmed/Partial/Not found/Unknown status
model, and an evidence-register schema. This tool is the part that's better
done in code than in a conversation: storing every research pass as a dated,
diffable snapshot, computing the brand × capability matrix and novelty labels
mechanically from the evidence (so scoring stays consistent instead of drifting
between runs), diffing snapshots so a re-run next month tells you exactly what
changed, and exporting a deduped URL list for pasting into your analytics/
tracking systems (this tool has no access to traffic or conversion data —
that hand-off is intentional).

## How a research pass flows through the system

1. **Research.** Run the `indonesia-auto-benchmark` skill (in Claude or
   Codex) against this month's brand list. Ask it to output its evidence
   table using the exact columns in `data/evidence_template.csv` — the skill
   already tracks all of these fields internally, so this is just an export
   format, not extra work for it.
2. **Fill / save the CSV.** Save that table as a CSV (e.g. `sept_2026.csv`),
   using `data/evidence_template.csv` as the header reference.
3. **Ingest it as a snapshot.**
   ```
   python3 -m benchmark ingest sept_2026.csv --date 2026-09-24
   ```
   This validates the data (blocking errors on malformed status/score values
   or duplicate brand+capability rows; non-blocking warnings for things like
   a Confirmed capability with no evidence URL) and stores it at
   `data/snapshots/2026-09-24/evidence.csv` — plain CSV, so `git diff` on it
   is actually readable.
4. **Generate the report.**
   ```
   python3 -m benchmark report --focus-brand Mitsubishi
   ```
   Writes, under `reports/2026-09-24/`:
   - `report.md` — capability matrix, coverage by brand, novelty
     classification (Table Stakes / Developing / Distinctive), and, with
     `--focus-brand`, a competitive-positioning section: rank, average
     maturity by category vs each named competitor, where the focus brand
     already leads, and priority gaps naming the specific competitor and
     score that's ahead.
   - `dashboard.html` — the same data as a filterable/sortable single-file
     page (open it directly in a browser, no server needed).
   - `urls.csv` — every evidence URL, deduped, tagged with brand/category/
     capability — paste this into your tracking/analytics tool to line up
     traffic and conversion against specific capabilities.
   - `diff_from_previous.md` — auto-generated whenever a previous snapshot
     exists: status/score changes, new capability rows, rows that dropped
     out, changed evidence URLs. This is the "what changed since last time"
     view.
5. **Commit.** `data/snapshots/*` and `reports/*` are meant to be committed —
   that history *is* the tracked-over-time benchmark.

Repeat steps 1–4 whenever you want a fresh read (monthly, quarterly, after a
brand relaunches a site, etc.). Nothing needs to be reconfigured.

## Commands

| Command | Purpose |
|---|---|
| `python3 -m benchmark init` | Scaffold `data/`/`reports/` and write the evidence CSV template (safe to re-run). |
| `python3 -m benchmark validate <csv>` | Check a raw evidence CSV without storing it. |
| `python3 -m benchmark ingest <csv> [--date YYYY-MM-DD] [--snapshot-id ID] [--force]` | Validate and store a research pass as a new snapshot. |
| `python3 -m benchmark report [--snapshot ID] [--focus-brand BRAND]` | Build report.md, dashboard.html, urls.csv (+ diff vs the previous snapshot, when generating the latest one). |
| `python3 -m benchmark diff [--old ID] [--new ID] [--out FILE]` | Diff any two snapshots explicitly. |
| `python3 -m benchmark export-urls [--snapshot ID] [--out FILE]` | Standalone URL export. |
| `python3 -m benchmark list` | List stored snapshots with row/brand counts. |

No third-party dependencies — standard library only, Python 3.10+.

## Evidence CSV columns

`brand, category, capability, status, maturity_score, advanced,
short_description, how_it_works, customer_value, url, page_title,
date_accessed, screenshot_status, screenshot_reference, limitations,
confidence`

- `status`: `Confirmed | Partial | Not found | Unknown`
- `maturity_score`: `0-4 | ? | N/A` — 0 not found, 1 informational, 2
  interactive/calculated, 3 integrated into a next step (finance, dealer,
  account, order), 4 completed/tracked. Use `?` rather than `0` when a
  capability wasn't actually inspected.
- `advanced`: `yes` when the capability shows independently evidenced
  functional depth, regardless of how common it is across brands (this
  drives the ★ marker and the "depth gap" section, kept separate from the
  Table Stakes/Developing/Distinctive prevalence label).
- `category` / `capability`: ideally values from
  `benchmark/taxonomy.py` (mirrors the skill's
  `references/capability-taxonomy.md`). New values are allowed — the tool
  only warns, it doesn't reject — since the skill is explicitly meant to
  surface genuinely new functionality.

## Repo layout

```
benchmark/                  CLI + report logic (stdlib only)
data/
  evidence_template.csv     CSV header/example row for a new research pass
  snapshots/<date>/
    evidence.csv            canonical evidence for that pass
    meta.json               ingest metadata (source file, row/brand counts)
reports/<date>/
  report.md
  dashboard.html
  urls.csv
  diff_from_previous.md     only when a prior snapshot exists
indonesia-automotive-digital-benchmark (1)/   the research skill (unmodified)
```

## Notes / known limits

- This tool does not browse the web or judge website quality itself — that
  judgment is the skill's job. The tool's job is storing, scoring
  consistently, comparing and diffing what the skill (or a human) found.
- Novelty labels (Table Stakes ≥75% confirmed, Developing 25–75%, Distinctive
  <25%) are computed from whatever brands are in *that* snapshot's sample —
  they'll shift as you add or drop brands, which is expected.
- Traffic, conversion and monetization data are out of scope by design; use
  `urls.csv` to cross-reference against your own analytics tooling.
