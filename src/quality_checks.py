"""Data quality checks. Exits with code 1 if any check on RAW data finds problems,
and reports what the clean layer removed."""
import argparse
import sys
from pathlib import Path

import duckdb

# Resolve relative to the project root so it works from any working directory.
DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "processed" / "triage.duckdb"

# (name, SQL returning the number of offending rows)
CHECKS = [
    ("raw: null/blank message_text",
     "SELECT count(*) FROM raw.reports WHERE message_text IS NULL OR trim(message_text) = ''"),
    ("raw: duplicate report_id",
     "SELECT count(*) - count(DISTINCT report_id) FROM raw.reports"),
    ("raw: report_count outside 1..1000",
     "SELECT count(*) FROM raw.reports WHERE TRY_CAST(report_count AS INTEGER) NOT BETWEEN 1 AND 1000"),
    ("clean: duplicate report_id (must be 0)",
     "SELECT count(*) - count(DISTINCT report_id) FROM clean.reports"),
    ("clean: null message_text (must be 0)",
     "SELECT count(*) FROM clean.reports WHERE message_text IS NULL"),
    ("clean: report_count outside 1..1000 (must be 0)",
     "SELECT count(*) FROM clean.reports WHERE report_count NOT BETWEEN 1 AND 1000"),
    ("clean: url not starting with http (must be 0)",
     "SELECT count(*) FROM clean.reports WHERE url IS NOT NULL AND url NOT LIKE 'http%'"),
    ("clean: reported_at in the future (must be 0)",
     "SELECT count(*) FROM clean.reports WHERE reported_at > current_timestamp"),
    ("clean: sender not starting with 08 (must be 0)",
     "SELECT count(*) FROM clean.reports WHERE sender IS NULL OR sender NOT LIKE '08%'"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args()

    con = duckdb.connect(args.db, read_only=True)
    failed = False
    for name, sql in CHECKS:
        bad = con.execute(sql).fetchone()[0]
        must_be_zero = name.startswith("clean:")
        status = "OK  " if bad == 0 else ("FAIL" if must_be_zero else "INFO")
        print(f"[{status}] {name}: {bad}")
        if must_be_zero and bad > 0:
            failed = True
    con.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
