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


def test_clean_rules(tmp_path):
    con = duckdb.connect(str(tmp_path / "t.duckdb"))
    con.execute("CREATE SCHEMA raw")
    con.execute(
        "CREATE TABLE raw.reports ("
        "report_id VARCHAR, reported_at VARCHAR, sender VARCHAR, message_text VARCHAR, "
        "url VARCHAR, report_count VARCHAR, channel VARCHAR, synthetic_label VARCHAR)"
    )
    con.execute("""
        INSERT INTO raw.reports VALUES
        ('r1', '2024-01-01 10:00:00', '0811111111', 'normal',    'http://a.com/1', '5', 'sms', 'x'),
        ('r1', '2024-01-02 10:00:00', '0811111111', 'duplicate', 'http://a.com/1', '5', 'sms', 'x'),
        ('r2', '2024-01-01 11:00:00', '0822222222', '   ',       'http://b.com/2', '5', 'sms', 'x'),
        ('r3', '2024-01-01 12:00:00', '0833333333', 'zero count', 'http://c.com/3', '0', 'sms', 'x')
    """)
    con.execute((ROOT / "sql/01_clean.sql").read_text(encoding="utf-8"))

    rows = con.execute("SELECT report_id, message_text FROM clean.reports").fetchall()
    con.close()
    assert rows == [("r1", "normal")]


