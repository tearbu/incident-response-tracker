#!/usr/bin/env python3
"""
Incident Response Tracker
-------------------------
A small command-line incident tracker backed by SQLite (standard library
only). It records security incidents with severity (P1-P4), category,
opened / first-response / closed timestamps and a resolution note, then
produces the kind of summary an incident review actually asks for:

  * counts by severity and status
  * mean time to respond  (opened -> first response)
  * mean time to resolve  (opened -> closed)
  * open incidents older than 7 days ("aging" queue)

Commands:
    init                                   create the database
    add   --title T --severity P2 --category Phishing --opened 2026-11-01
          [--responded 2026-11-01]
    list                                   show all incidents
    close ID --closed 2026-11-03 --resolution "..."
    report                                 summary metrics

Dates are YYYY-MM-DD. The database file defaults to ./ir.db (--db PATH).
The "as of" date used by `report` is the latest date present in the data,
so seeded demo numbers are reproducible.
"""

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    severity     TEXT NOT NULL CHECK (severity IN ('P1','P2','P3','P4')),
    category     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Closed')),
    opened_at    TEXT NOT NULL,
    responded_at TEXT,
    closed_at    TEXT,
    resolution   TEXT
);
"""

AGING_DAYS = 7


def parse_date(value, field):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        sys.exit(f"error: {field} must be a date in YYYY-MM-DD form, got {value!r}")


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def cmd_init(args):
    connect(args.db).close()
    print(f"Database ready: {args.db}")
    return 0


def add_incident(conn, title, severity, category, opened,
                 responded=None, closed=None, resolution=None):
    """Insert one incident; used by both the CLI and data/seed.py."""
    status = "Closed" if closed else "Open"
    cur = conn.execute(
        "INSERT INTO incidents (title, severity, category, status, opened_at,"
        " responded_at, closed_at, resolution) VALUES (?,?,?,?,?,?,?,?)",
        (title, severity, category, status, opened,
         responded, closed, resolution))
    conn.commit()
    return cur.lastrowid


def cmd_add(args):
    opened = parse_date(args.opened, "--opened")
    responded = parse_date(args.responded, "--responded") if args.responded else None
    if responded and responded < opened:
        sys.exit("error: --responded cannot be before --opened")
    conn = connect(args.db)
    new_id = add_incident(conn, args.title, args.severity, args.category,
                          opened.isoformat(),
                          responded.isoformat() if responded else None)
    conn.close()
    print(f"Added incident #{new_id}: [{args.severity}] {args.title} "
          f"({args.category}, opened {opened.isoformat()})")
    return 0


def cmd_list(args):
    conn = connect(args.db)
    rows = conn.execute(
        "SELECT * FROM incidents ORDER BY opened_at, id").fetchall()
    conn.close()
    if not rows:
        print("No incidents recorded.")
        return 0
    print(f"{'ID':>3}  {'Sev':<3}  {'Status':<6}  {'Opened':<10}  "
          f"{'Category':<20}  Title")
    print("-" * 100)
    for r in rows:
        print(f"{r['id']:>3}  {r['severity']:<3}  {r['status']:<6}  "
              f"{r['opened_at']:<10}  {r['category']:<20}  {r['title']}")
    print(f"\n{len(rows)} incident(s).")
    return 0


def cmd_close(args):
    closed = parse_date(args.closed, "--closed")
    conn = connect(args.db)
    row = conn.execute("SELECT * FROM incidents WHERE id = ?",
                       (args.id,)).fetchone()
    if row is None:
        conn.close()
        sys.exit(f"error: no incident with id {args.id}")
    if row["status"] == "Closed":
        conn.close()
        sys.exit(f"error: incident #{args.id} is already closed")
    if closed < parse_date(row["opened_at"], "opened_at"):
        conn.close()
        sys.exit("error: --closed cannot be before the opened date")
    conn.execute(
        "UPDATE incidents SET status = 'Closed', closed_at = ?, resolution = ?"
        " WHERE id = ?",
        (closed.isoformat(), args.resolution, args.id))
    conn.commit()
    conn.close()
    print(f"Closed incident #{args.id} on {closed.isoformat()}: {args.resolution}")
    return 0


def cmd_report(args):
    conn = connect(args.db)
    rows = conn.execute("SELECT * FROM incidents").fetchall()
    conn.close()
    if not rows:
        print("No incidents recorded.")
        return 0

    all_dates = [d for r in rows
                 for d in (r["opened_at"], r["responded_at"], r["closed_at"]) if d]
    as_of = max(parse_date(d, "date") for d in all_dates)

    by_severity = {}
    by_status = {"Open": 0, "Closed": 0}
    respond_days, resolve_days = [], []
    aging = []
    for r in rows:
        by_severity[r["severity"]] = by_severity.get(r["severity"], 0) + 1
        by_status[r["status"]] += 1
        opened = parse_date(r["opened_at"], "opened_at")
        if r["responded_at"]:
            respond_days.append((parse_date(r["responded_at"], "r") - opened).days)
        if r["closed_at"]:
            resolve_days.append((parse_date(r["closed_at"], "c") - opened).days)
        if r["status"] == "Open" and (as_of - opened).days > AGING_DAYS:
            aging.append((r, (as_of - opened).days))

    print(f"Incident Response Report (as of {as_of.isoformat()})")
    print("=" * 48)
    print(f"Total incidents: {len(rows)}")
    print("\nBy severity:")
    for sev in ("P1", "P2", "P3", "P4"):
        if sev in by_severity:
            print(f"  {sev}: {by_severity[sev]}")
    print("\nBy status:")
    print(f"  Open:   {by_status['Open']}")
    print(f"  Closed: {by_status['Closed']}")
    if respond_days:
        print(f"\nMean time to respond: "
              f"{sum(respond_days) / len(respond_days):.1f} days (n={len(respond_days)})")
    if resolve_days:
        print(f"Mean time to resolve: "
              f"{sum(resolve_days) / len(resolve_days):.1f} days (n={len(resolve_days)})")
    print(f"\nOpen incidents older than {AGING_DAYS} days:")
    if not aging:
        print("  (none)")
    for r, age in sorted(aging, key=lambda x: -x[1]):
        print(f"  #{r['id']} [{r['severity']}] {r['title']} "
              f"(opened {r['opened_at']}, {age} days open)")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Incident response tracker (SQLite).")
    parser.add_argument("--db", default="ir.db", help="Database file (default: ir.db)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create the database.")

    p_add = sub.add_parser("add", help="Add an incident.")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--severity", required=True, choices=["P1", "P2", "P3", "P4"])
    p_add.add_argument("--category", required=True)
    p_add.add_argument("--opened", required=True, help="YYYY-MM-DD")
    p_add.add_argument("--responded", help="First-response date, YYYY-MM-DD")

    sub.add_parser("list", help="List all incidents.")

    p_close = sub.add_parser("close", help="Close an incident.")
    p_close.add_argument("id", type=int)
    p_close.add_argument("--closed", required=True, help="YYYY-MM-DD")
    p_close.add_argument("--resolution", required=True)

    sub.add_parser("report", help="Print summary metrics.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    handler = {"init": cmd_init, "add": cmd_add, "list": cmd_list,
               "close": cmd_close, "report": cmd_report}[args.command]
    if args.command != "init" and not Path(args.db).exists():
        print(f"note: creating new database {args.db}", file=sys.stderr)
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
