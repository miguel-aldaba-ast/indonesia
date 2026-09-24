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

## Current status

Four real, interactively-verified snapshots trace how coverage grew:
`2026-09-24` (4 brands, pilot) → `2026-09-24-2` (8 brands) → `2026-09-24-3`
(all 14 brands, first pass) → `2026-09-24-4` — the current one — same 14
brands with a second gap-filling research pass: Toyota, Honda, Mitsubishi,
BYD, Daihatsu, Suzuki, Hyundai, Wuling, Jaecoo, Isuzu, Geely, Chery, MG,
VinFast. This is a provisional brand list built from public research, not
the internal DCI report — swap in the exact DCI names whenever you have
them (see `data/snapshots/2026-09-24-4/evidence.csv`, just relabel the
`brand` column, no schema change needed).

119 evidence rows across **19 distinct capabilities** and **13 of 14**
taxonomy categories (`reports/<date>/report.md` names the 1 still untouched:
OMNICHANNEL) — a wide, still-growing pass, not the full ~150-capability
taxonomy. Standout real findings: Toyota's ecosystem turned out to be the
deepest of the sample once its footer sitemap was actually explored —
T-Intouch (8+ named connected-car features plus an on-page VIN checker),
G-Fleet (real-time fleet telematics, matching Isuzu Link), and KINTO (a
fully online, no-down-payment car subscription — the only vehicle
subscription found in the sample, and the reason EMERGING EXPERIENCES is no
longer empty); VinFast still has the deepest single configurator-to-
reservation flow and the only fully calculated cost-of-ownership tool;
MG's i-SMART app is the only EV app found that folds a charging-station
map into the app itself rather than a separate page; several brands'
"finance calculators" turned out to be lead-capture gates rather than actual
calculators once clicked through. Rows marked `Partial`/`?` are cases where
a tool was found but couldn't be fully verified in that session, a site
actively blocked automated browsing (Cloudflare on one Daihatsu subdomain),
or a previously-indexed page now 404s (Suzuki's `/compare`) — each one says
why in its `limitations` field. Extend coverage by running another research
pass — more capabilities, OMNICHANNEL, or the exact DCI brand list — and
ingesting it as a new snapshot; nothing about the pipeline changes.

**A note on location-based tools:** dealer/charging-station locators that
offer a "use my location" button were deliberately not exercised that way
in this session — the browsing session itself is physically outside
Indonesia, so a geolocation prompt would return an irrelevant nearby
location (e.g. Madrid) instead of anywhere in Indonesia. Locators were
tested via explicit city/province search fields instead, or left as
"entry point confirmed, not searched" where no such field existed.

No single brand is a default "reference" anywhere in the pipeline: the
`--focus-brand` CLI flag only adds an extra narrative section to the written
`report.md` when you ask for it, and the `dashboard.html` lets the viewer pick
*any* brand from a dropdown to see its positioning — every brand's leads/gaps
are precomputed, and none is selected by default.

## How a research pass flows through the system

1. **Research.** Someone (or something) with a real browser goes and looks at
   the brand websites and fills in the evidence CSV. Three ways to do this:
   - **Ask Claude Code, in this repo, to do it** — it can browse interactively
     (this is how the `2026-09-24` snapshot in this repo was produced).
   - **Run the `indonesia-auto-benchmark` skill in Codex CLI** — it auto-loads
     from `.codex-plugin/plugin.json` in this repo; ask it to output its
     evidence table using the columns in `data/evidence_template.csv`.
   - **Use the Custom GPT** in `chatgpt-gpt/` — for colleagues without
     Python/terminal access. See `chatgpt-gpt/README.md` to set it up in
     chatgpt.com. It only produces the CSV; a human still runs steps 3–4
     below locally.
2. **Save the CSV.** Save the finished table as a CSV file somewhere on disk
   (e.g. `oct_2026.csv`), using `data/evidence_template.csv` as the header
   reference. This file does not need to exist yet, and does not live in this
   repo until you ingest it in the next step — it's just wherever you saved
   your research output.
3. **Ingest it as a snapshot.**
   ```
   python3 -m benchmark ingest oct_2026.csv --date 2026-10-15
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
chatgpt-gpt/                 Custom GPT setup: instructions.md, csv-output-format.md, README.md
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
