"""เทสต์ของ Phase 3: น้ำหนัก report_count, คะแนนจัดลำดับ และตาราง mart.triage"""
import subprocess
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from triage import build_triage, count_weight, hostname_of, priority_score, score_reports, train_model


class FakeModel:
    """โมเดลปลอมที่รู้คำตอบล่วงหน้า: hostname ที่มี 'scam' ได้ prob 0.9 นอกนั้น 0.1
    ใช้เพื่อเทสต์การจัดลำดับโดยไม่ต้องพึ่งข้อมูล URL จริง"""

    def predict_proba(self, hosts):
        # คืนตารางแบบเดียวกับ scikit-learn: [prob ปกติ, prob scam] ต่อแถว
        return np.array([[0.1, 0.9] if "scam" in h else [0.9, 0.1] for h in hosts])


def test_count_weight_grows_by_one_per_digit():
    assert count_weight(1) == 1
    assert count_weight(10) == pytest.approx(2)
    assert count_weight(1000) == pytest.approx(4)


def test_count_weight_rejects_zero():
    with pytest.raises(ValueError):
        count_weight(0)


def test_likely_phishing_beats_heavily_reported_spam():
    # เหตุผลที่ใช้ log: สแปมที่คนแจ้งเยอะต้องไม่แซงฟิชชิ่งที่โมเดลมั่นใจ
    phishing = priority_score(0.95, 3)
    spam = priority_score(0.10, 50)
    assert phishing > spam


def test_same_prob_more_reports_ranks_higher():
    assert priority_score(0.8, 20) > priority_score(0.8, 2)


def test_hostname_of():
    assert hostname_of("http://ais-points-th.xyz/123") == "ais-points-th.xyz"
    assert hostname_of(None) is None
    assert hostname_of("") is None
    assert hostname_of(float("nan")) is None   # pandas ใช้ NaN แทนค่าว่าง


def test_report_without_url_gets_zero_score():
    reports = pd.DataFrame({"url": [None, "http://scam-site.top/1"], "report_count": [100, 1]})
    scored = score_reports(reports, FakeModel())
    assert list(scored["scam_prob"]) == [0.0, 0.9]
    assert scored["priority_score"][0] == 0.0


def _clean_db(tmp_path):
    con = duckdb.connect(str(tmp_path / "t.duckdb"))
    con.execute("CREATE SCHEMA clean")
    con.execute("""
        CREATE TABLE clean.reports AS SELECT * FROM (VALUES
            ('r1', TIMESTAMP '2026-01-01 10:00:00', '0811111111', 'spam',  NULL,                     50),
            ('r2', TIMESTAMP '2026-01-01 11:00:00', '0822222222', 'phish', 'http://scam-a.xyz/1',     3),
            ('r3', TIMESTAMP '2026-01-01 12:00:00', '0833333333', 'ok',    'http://shop.example.com', 5),
            ('r4', TIMESTAMP '2026-01-01 09:00:00', '0844444444', 'phish', 'http://scam-b.top/2',     3)
        ) t(report_id, reported_at, sender, message_text, url, report_count)
    """)
    return con


def test_build_triage_ranks_by_priority_score(tmp_path):
    con = _clean_db(tmp_path)
    n = build_triage(con, FakeModel())
    rows = con.execute("SELECT report_id, review_rank FROM mart.triage ORDER BY review_rank").fetchall()
    con.close()
    assert n == 4                      # ไม่มีแถวหาย
    # r4 กับ r2 คะแนนเท่ากัน (prob 0.9, แจ้ง 3 ครั้ง) r4 แจ้งก่อนจึงได้อันดับ 1
    # r1 แจ้ง 50 ครั้งแต่ไม่มี url จึงอยู่ท้าย
    assert rows == [("r4", 1), ("r2", 2), ("r3", 3), ("r1", 4)]


def test_train_model_learns_from_url_dataset():
    url_df = pd.DataFrame({
        "hostname": ["ais-points-th.xyz", "my-ais-verify.top", "bank-secure-verify.vip",
                     "google.com", "wikipedia.org", "github.com"],
        "label": [1, 1, 1, 0, 0, 0],
    })
    model = train_model(url_df)
    probs = model.predict_proba(["ais-rewards-verify.xyz", "google.org"])[:, 1]
    assert probs[0] > probs[1]


def test_triage_script_end_to_end(tmp_path):
    """รันทั้งเส้น: สร้างข้อมูล → โหลด → SQL → triage.py แล้วตาราง mart.triage ต้องครบทุกแถว"""
    def run(*args):
        subprocess.run([sys.executable, *args], cwd=tmp_path, check=True, capture_output=True, text=True)

    (tmp_path / "data/raw").mkdir(parents=True)
    pd.DataFrame({
        "hostname": ["ais-points-th.xyz", "gov-refund-th.top", "google.com", "wikipedia.org"],
        "label": [1, 1, 0, 0],
    }).to_csv(tmp_path / "urls.csv", index=False)
    run(str(ROOT / "src/generate_reports.py"), "--rows", "300", "--seed", "1", "--out", "data/raw/r.csv")
    run(str(ROOT / "src/load_duckdb.py"), "--db", "t.duckdb", "--src", "data/raw/r.csv")
    run(str(ROOT / "src/run_sql.py"), "--db", "t.duckdb", "--sql-dir", str(ROOT / "sql"))
    run(str(ROOT / "src/triage.py"), "--db", "t.duckdb", "--urls", "urls.csv")

    con = duckdb.connect(str(tmp_path / "t.duckdb"), read_only=True)
    clean_n = con.execute("SELECT count(*) FROM clean.reports").fetchone()[0]
    triage_n, min_rank, has_prob = con.execute(
        "SELECT count(*), min(review_rank), count(scam_prob) FROM mart.triage").fetchone()
    con.close()
    assert triage_n == clean_n
    assert min_rank == 1
    assert has_prob == triage_n        # ทุกแถวมี scam_prob (ไม่มี url = 0)
