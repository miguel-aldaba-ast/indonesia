from __future__ import annotations

import argparse
import sys
from datetime import datetime, date
from pathlib import Path

from . import diffing, positioning as positioning_mod, report as report_mod, urls as urls_mod
from .io_csv import read_rows, write_rows, write_template
from .snapshots import DATA_DIR, SNAPSHOTS_DIR, Snapshot, list_snapshots, latest_two, new_snapshot_id, write_meta
from .validate import validate_rows

REPORTS_DIR = Path("reports")


def cmd_init(args: argparse.Namespace) -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    template_path = DATA_DIR / "evidence_template.csv"
    if not template_path.exists():
        write_template(template_path)
        print(f"Wrote {template_path}")
    else:
        print(f"{template_path} already exists, left untouched")
    print("Ready. Fill a copy of the template with this run's research, then:\n"
          "  python -m benchmark ingest <your_evidence.csv>\n"
          "  python -m benchmark report")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.csv)
    rows = read_rows(path)
    errors, warnings = validate_rows(rows)
    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    print(f"\n{len(rows)} rows, {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def cmd_ingest(args: argparse.Namespace) -> int:
    src = Path(args.csv)
    rows = read_rows(src)
    errors, warnings = validate_rows(rows)
    for w in warnings:
        print(f"WARNING: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"\n{len(errors)} blocking error(s) — fix the CSV and re-run ingest. Nothing was written.")
        return 1

    if args.date:
        on = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        on = date.today()
    snap_id = args.snapshot_id or new_snapshot_id(on=on)
    snap_dir = SNAPSHOTS_DIR / snap_id
    if snap_dir.exists() and not args.force:
        print(f"Snapshot {snap_id} already exists. Use --force to overwrite or --snapshot-id to pick a new id.")
        return 1

    snapshot = Snapshot(id=snap_id, dir=snap_dir)
    write_rows(snapshot.evidence_path, rows)
    write_meta(snapshot, {
        "snapshot_id": snap_id,
        "ingested_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": str(src),
        "row_count": len(rows),
        "brand_count": len({r.brand for r in rows}),
        "warning_count": len(warnings),
    })
    print(f"Ingested {len(rows)} rows into {snapshot.evidence_path} (snapshot '{snap_id}')")
    if warnings:
        print(f"{len(warnings)} non-blocking warning(s) — see above. Review before treating this as final.")
    return 0


def _load_snapshot(snapshot_id: str | None) -> Snapshot | None:
    snaps = list_snapshots()
    if not snaps:
        return None
    if snapshot_id is None:
        return snaps[-1]
    for s in snaps:
        if s.id == snapshot_id:
            return s
    return None


def cmd_report(args: argparse.Namespace) -> int:
    snapshot = _load_snapshot(args.snapshot)
    if snapshot is None:
        print("No snapshots found. Run `python -m benchmark ingest <csv>` first.")
        return 1

    rows = snapshot.load_rows()
    _, warnings = validate_rows(rows)
    matrix = report_mod.build_matrix(rows)
    novelty = report_mod.novelty_summary(matrix)

    latest, previous = latest_two()
    previous_id = previous.id if (previous and snapshot.id == latest.id) else None

    pos = None
    if args.focus_brand:
        pos = positioning_mod.build_positioning(matrix, args.focus_brand)
        if pos is None:
            print(f"WARNING: focus brand {args.focus_brand!r} not found in this snapshot's brands "
                  f"({', '.join(matrix['brands'])}) — skipping positioning section.")

    out_dir = REPORTS_DIR / snapshot.id
    out_dir.mkdir(parents=True, exist_ok=True)

    md = report_mod.to_markdown(snapshot.id, rows, matrix, novelty, warnings,
                                 previous_id=previous_id, positioning=pos)
    (out_dir / "report.md").write_text(md, encoding="utf-8")

    html_out = report_mod.to_html(snapshot.id, rows, matrix, novelty, previous_id=previous_id, positioning=pos)
    (out_dir / "dashboard.html").write_text(html_out, encoding="utf-8")

    n_urls = urls_mod.export_urls(rows, out_dir / "urls.csv")

    print(f"Wrote {out_dir / 'report.md'}")
    print(f"Wrote {out_dir / 'dashboard.html'}")
    print(f"Wrote {out_dir / 'urls.csv'} ({n_urls} unique URLs)")

    if previous_id:
        old_rows = previous.load_rows()
        d = diffing.diff_rows(old_rows, rows)
        diff_md = diffing.to_markdown(previous_id, snapshot.id, d)
        (out_dir / "diff_from_previous.md").write_text(diff_md, encoding="utf-8")
        print(f"Wrote {out_dir / 'diff_from_previous.md'} (vs '{previous_id}')")

    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    snaps = list_snapshots()
    by_id = {s.id: s for s in snaps}
    if args.old:
        old = by_id.get(args.old)
    else:
        _, old = latest_two()
    if args.new:
        new = by_id.get(args.new)
    else:
        new, _ = latest_two()

    if old is None or new is None:
        print("Need two snapshots to diff. Available: " + ", ".join(by_id) if by_id else "No snapshots found.")
        return 1

    d = diffing.diff_rows(old.load_rows(), new.load_rows())
    md = diffing.to_markdown(old.id, new.id, d)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(md)
    return 0


def cmd_export_urls(args: argparse.Namespace) -> int:
    snapshot = _load_snapshot(args.snapshot)
    if snapshot is None:
        print("No snapshots found.")
        return 1
    rows = snapshot.load_rows()
    out = Path(args.out) if args.out else REPORTS_DIR / snapshot.id / "urls.csv"
    n = urls_mod.export_urls(rows, out)
    print(f"Wrote {out} ({n} unique URLs) — paste these into your tracking system to match up traffic/conversion.")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    snaps = list_snapshots()
    if not snaps:
        print("No snapshots yet.")
        return 0
    for s in snaps:
        meta = s.load_meta()
        print(f"{s.id}  rows={meta.get('row_count', '?')}  brands={meta.get('brand_count', '?')}  "
              f"ingested={meta.get('ingested_at', '?')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m benchmark",
                                 description="Indonesia automotive digital-capability benchmark: "
                                             "versioned evidence snapshots, matrix/diff reports, URL export.")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("init", help="Scaffold data/reports folders and write the evidence CSV template.")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("validate", help="Validate a raw evidence CSV without ingesting it.")
    sp.add_argument("csv")
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("ingest", help="Validate and store a research pass as a new dated snapshot.")
    sp.add_argument("csv", help="Evidence CSV filled from a research session (see data/evidence_template.csv)")
    sp.add_argument("--date", help="Snapshot date YYYY-MM-DD (default: today)")
    sp.add_argument("--snapshot-id", help="Override the auto-generated snapshot id")
    sp.add_argument("--force", action="store_true", help="Overwrite an existing snapshot with this id")
    sp.set_defaults(func=cmd_ingest)

    sp = sub.add_parser("report", help="Generate report.md, dashboard.html, urls.csv (and a diff vs the "
                                        "previous snapshot when it's the latest one).")
    sp.add_argument("--snapshot", help="Snapshot id (default: latest)")
    sp.add_argument("--focus-brand", help="Add a competitive-positioning section for this brand "
                                          "(leads, gaps and depth deltas vs the rest of the sample)")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("diff", help="Diff two snapshots explicitly.")
    sp.add_argument("--old")
    sp.add_argument("--new")
    sp.add_argument("--out", help="Write to a file instead of stdout")
    sp.set_defaults(func=cmd_diff)

    sp = sub.add_parser("export-urls", help="Write a deduped URL list for a snapshot for pasting into "
                                             "your analytics/tracking system.")
    sp.add_argument("--snapshot", help="Snapshot id (default: latest)")
    sp.add_argument("--out", help="Output path (default: reports/<snapshot>/urls.csv)")
    sp.set_defaults(func=cmd_export_urls)

    sp = sub.add_parser("list", help="List stored snapshots.")
    sp.set_defaults(func=cmd_list)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
