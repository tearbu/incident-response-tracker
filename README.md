# Incident Response Tracker

A command-line incident tracker written in Python against SQLite, with no dependencies beyond the standard library. It records security incidents with severity, category, and opened / first-response / closed timestamps, and reports the metrics an incident review actually asks for: counts by severity and status, mean time to respond, mean time to resolve, and the open incidents that have been sitting too long.

## Why this matters

Incident response lives or dies on tracking. During an incident, notes are in chat threads and people's heads. Afterwards, leadership asks three questions: how fast did we respond, how long did it take to close, and what is still open? A tracker like this is the smallest tool that answers all three honestly. It is deliberately boring technology (one file, one SQLite database), because the tool you can run anywhere, back up by copying one file, and read without a server is the tool that actually gets used.

## Repository layout

```
src/ir_tracker.py   # CLI: init / add / list / close / report
data/seed.py        # loads 8 fictional demo incidents (fixed Oct-Nov 2026 dates)
ir.db               # created at runtime; gitignored
```

## Commands

```bash
python3 src/ir_tracker.py init                      # create the database
python3 src/ir_tracker.py add --title "..." --severity P2 \
    --category Phishing --opened 2026-11-01 --responded 2026-11-01
python3 src/ir_tracker.py list
python3 src/ir_tracker.py close 3 --closed 2026-11-04 --resolution "..."
python3 src/ir_tracker.py report
```

Severities are P1 (critical) through P4 (low). Dates are `YYYY-MM-DD`. The database path defaults to `./ir.db` and can be changed with `--db`.

## Demo (actual run)

Seed the demo data and print the report:

```bash
python3 data/seed.py
python3 src/ir_tracker.py list
python3 src/ir_tracker.py report
```

`list` output:

```
 ID  Sev  Status  Opened      Category              Title
----------------------------------------------------------------------------------------------------
  1  P3   Closed  2026-10-05  Phishing              Phishing email reported by finance user
  2  P2   Closed  2026-10-12  Malware               Malware detected on workstation WS-1042
  3  P2   Closed  2026-10-20  Unauthorized Access   Impossible-travel login alert for executive account
  4  P4   Closed  2026-10-22  Policy Violation      USB mass-storage device used against policy
  5  P3   Open    2026-10-28  Unauthorized Access   Dormant vendor account attempted sign-in
  6  P1   Closed  2026-11-02  Malware               Ransomware attempt blocked by EDR
  7  P2   Open    2026-11-03  Phishing              Sustained phishing campaign targeting HR inboxes
  8  P3   Open    2026-11-09  Policy Violation      Unencrypted laptop left unattended in a public area

8 incident(s).
```

`report` output:

```
Incident Response Report (as of 2026-11-10)
================================================
Total incidents: 8

By severity:
  P1: 1
  P2: 3
  P3: 3
  P4: 1

By status:
  Open:   3
  Closed: 5

Mean time to respond: 0.4 days (n=8)
Mean time to resolve: 2.4 days (n=5)

Open incidents older than 7 days:
  #5 [P3] Dormant vendor account attempted sign-in (opened 2026-10-28, 13 days open)
```

The report's "as of" date is the latest date present in the data (not the wall clock), so the seeded demo prints identical numbers on any day.

## Limitations (honest ones)

- **Day-level granularity.** Timestamps are dates, not datetimes, so response times under a day all read as 0. Fine for trend reporting, too coarse for measuring a live incident bridge.
- **Single user, local file.** SQLite is not a shared ticketing system. No assignments, notifications, SLA timers, or audit trail of edits.
- **Categories are free text.** Nothing stops "phishing" and "Phishing" from becoming two categories; a real deployment would want a fixed list.
- Closing an incident requires a resolution note by design. That is a feature, but it means there is no quick "close as duplicate" path.

## License

MIT. See [LICENSE](LICENSE). Copyright (c) 2026 Araf Abubakar.
