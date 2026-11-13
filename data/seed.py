#!/usr/bin/env python3
"""
Seed the incident tracker with 8 fictional demo incidents.

Dates are fixed in Oct-Nov 2026 so `ir_tracker.py report` output is
reproducible. All incidents, people, and systems are fictional.

Usage:
    python3 data/seed.py [--db ir.db]

Re-running replaces any existing incidents in the database.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ir_tracker import add_incident, connect  # noqa: E402

SEED = [
    # title, severity, category, opened, responded, closed, resolution
    ("Phishing email reported by finance user", "P3", "Phishing",
     "2026-10-05", "2026-10-05", "2026-10-06",
     "Message purged from all mailboxes; sender domain blocked."),
    ("Malware detected on workstation WS-1042", "P2", "Malware",
     "2026-10-12", "2026-10-12", "2026-10-14",
     "Host reimaged and returned; no lateral movement found."),
    ("Impossible-travel login alert for executive account", "P2",
     "Unauthorized Access", "2026-10-20", "2026-10-20", "2026-10-21",
     "Confirmed corporate VPN exit node; alert rule tuned."),
    ("USB mass-storage device used against policy", "P4", "Policy Violation",
     "2026-10-22", "2026-10-23", "2026-10-27",
     "User coached; endpoint control verified as enforced."),
    ("Dormant vendor account attempted sign-in", "P3", "Unauthorized Access",
     "2026-10-28", "2026-10-29", None, None),
    ("Ransomware attempt blocked by EDR", "P1", "Malware",
     "2026-11-02", "2026-11-02", "2026-11-05",
     "EDR isolated the host; file shares scanned, no encryption found."),
    ("Sustained phishing campaign targeting HR inboxes", "P2", "Phishing",
     "2026-11-03", "2026-11-03", None, None),
    ("Unencrypted laptop left unattended in a public area", "P3",
     "Policy Violation", "2026-11-09", "2026-11-10", None, None),
]


def main():
    parser = argparse.ArgumentParser(description="Seed demo incidents.")
    parser.add_argument("--db", default="ir.db")
    args = parser.parse_args()

    conn = connect(args.db)
    conn.execute("DELETE FROM incidents")
    conn.commit()
    for row in SEED:
        new_id = add_incident(conn, *row)
        print(f"Seeded #{new_id}: [{row[1]}] {row[0]}")
    conn.close()
    print(f"\n{len(SEED)} demo incidents written to {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
