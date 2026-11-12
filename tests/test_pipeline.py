"""Smoke test: run the pipeline on a tiny synthetic file in a temp dir."""
import subprocess
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd):
    return subprocess.run([sys.executable, *args], cwd=cwd, check=True, capture_output=True, text=True)


def test_pipeline_end_to_end(tmp_path):
    (tmp_path / "data/raw").mkdir(parents=True)
    run(str(ROOT / "src/generate_reports.py"), "--rows", "300", "--seed", "1",
        "--out", "data/raw/reports_test.csv", cwd=tmp_path)
    run(str(ROOT / "src/load_duckdb.py"), "--db", "t.duckdb", "--src", "data/raw/reports_*.csv", cwd=tmp_path)
    run(str(ROOT / "src/run_sql.py"), "--db", "t.duckdb", "--sql-dir", str(ROOT / "sql"), cwd=tmp_path)

    con = duckdb.connect(str(tmp_path / "t.duckdb"), read_only=True)
    raw_n = con.execute("SELECT count(*) FROM raw.reports").fetchone()[0]
    clean_n = con.execute("SELECT count(*) FROM clean.reports").fetchone()[0]
    dupes = con.execute("SELECT count(*) - count(DISTINCT report_id) FROM clean.reports").fetchone()[0]
    assert clean_n < raw_n      # dirty rows were removed
    assert dupes == 0           # dedupe worked


def test_quality_check_catches_bad_url(tmp_path):
    (tmp_path / "data/raw").mkdir(parents=True)
    run(str(ROOT / "src/generate_reports.py"), "--rows", "300", "--seed", "1",
        "--out", "data/raw/reports_test.csv", cwd=tmp_path)
    run(str(ROOT / "src/load_duckdb.py"), "--db", "t.duckdb", "--src", "data/raw/reports_*.csv", cwd=tmp_path)
    run(str(ROOT / "src/run_sql.py"), "--db", "t.duckdb", "--sql-dir", str(ROOT / "sql"), cwd=tmp_path)

    # Open writable and inject one row whose url does not start with http.
    con = duckdb.connect(str(tmp_path / "t.duckdb"))
    con.execute(
        "INSERT INTO clean.reports "
        "(report_id, reported_at, sender, message_text, url, report_count, channel, synthetic_label) "
        "VALUES ('bad-url-1', TIMESTAMP '2024-01-01 00:00:00', '0800000000', 'test', 'www.bad.com', 1, 'sms', 'test')"
    )
    con.close()

    result = subprocess.run([sys.executable, str(ROOT / "src/quality_checks.py"), "--db", "t.duckdb"],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 1
    assert "url not starting with http" in result.stdout