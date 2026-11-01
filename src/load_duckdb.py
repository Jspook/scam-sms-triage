"""Load raw CSV files into DuckDB as raw.reports (no cleaning here)."""
import argparse
from pathlib import Path

import duckdb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/processed/triage.duckdb")
    ap.add_argument("--src", default="data/raw/reports_*.csv")
    args = ap.parse_args()

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(args.db)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        "CREATE OR REPLACE TABLE raw.reports AS "
        "SELECT * FROM read_csv_auto(?, all_varchar=true, header=true)",
        [args.src],
    )
    n = con.execute("SELECT count(*) FROM raw.reports").fetchone()[0]
    print(f"raw.reports: {n} rows")
    con.close()


if __name__ == "__main__":
    main()
