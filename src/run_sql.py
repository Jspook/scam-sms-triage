"""Run sql/*.sql in filename order against the DuckDB file."""
import argparse
from pathlib import Path

import duckdb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/processed/triage.duckdb")
    ap.add_argument("--sql-dir", default="sql")
    args = ap.parse_args()

    con = duckdb.connect(args.db)
    for f in sorted(Path(args.sql_dir).glob("*.sql")):
        print(f"running {f.name}")
        con.execute(f.read_text(encoding="utf-8"))
    for t in ["clean.reports", "mart.triage"]:
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"{t}: {n} rows")
    con.close()


if __name__ == "__main__":
    main()
