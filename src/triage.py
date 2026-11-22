"""Phase 3: รวมความน่าจะเป็นจากโมเดลกับ report_count เป็นคะแนนจัดลำดับ แล้วสร้างตาราง mart.triage ใหม่

ลำดับการทำงาน:
  1. สอนโมเดล TF-IDF + LogReg (ตั้งค่าเดียวกับ Phase 2) ด้วย url_dataset.csv ทั้งไฟล์
  2. ดึง hostname จาก url ของแต่ละรายงานใน clean.reports แล้วให้โมเดลทาย scam_prob
  3. priority_score = scam_prob × count_weight(report_count)
  4. เขียนทับ mart.triage พร้อม review_rank (1 = ควรตรวจก่อน)

รัน: python src/run_sql.py แล้วตามด้วย python src/triage.py
"""
import argparse
import math
from pathlib import Path
from urllib.parse import urlparse

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "processed" / "triage.duckdb"
DEFAULT_URLS = ROOT / "data" / "processed" / "url_dataset.csv"
TOP_N = 20


def count_weight(report_count):
    """น้ำหนักจากจำนวนคนแจ้ง: 1 + log10(report_count)

    แจ้ง 1 ครั้ง = 1, 10 ครั้ง = 2, 100 ครั้ง = 3, 1000 ครั้ง = 4
    ทำไมใช้ log (ลอการิทึม: นับว่าเลขมีกี่หลัก) แทนการคูณตรง ๆ:
    - คนแจ้งเยอะควรได้ตรวจก่อน เพราะกระทบคนมาก แต่ครั้งที่ 101 บอกข้อมูลใหม่น้อยกว่าครั้งที่ 2
    - ถ้าคูณตรง ๆ สแปมที่คนแจ้ง 50 ครั้ง (prob 0.1 → 5.0) จะชนะฟิชชิ่งที่แจ้ง 3 ครั้ง (prob 0.95 → 2.85)
      ใช้ log แล้ว สแปมได้ 0.27 ฟิชชิ่งได้ 1.40 ให้โมเดลเป็นตัวตัดสินหลัก จำนวนแจ้งเป็นตัวเสริม
    - +1 เพื่อให้แจ้งครั้งเดียวได้น้ำหนัก 1 ไม่ใช่ 0 (log10(1) = 0)
    """
    if report_count < 1:
        raise ValueError("report_count must be >= 1 (clean layer guarantees this)")
    return 1 + math.log10(report_count)


def priority_score(scam_prob, report_count):
    """คะแนนจัดลำดับ = ความน่าจะเป็นว่าเป็น scam × น้ำหนักจาก report_count (ช่วง 0 ถึง 4)"""
    return scam_prob * count_weight(report_count)


def hostname_of(url):
    """ตัด url ให้เหลือ hostname แบบเดียวกับตอนสอนโมเดล (Phase 2) ถ้าไม่มี url คืน None"""
    if url is None or (isinstance(url, float) and math.isnan(url)) or not str(url).strip():
        return None
    return urlparse(str(url).strip()).hostname


def train_model(url_df):
    """สอนโมเดลด้วยข้อมูล URL ทั้งหมด (ไม่แบ่ง test แล้ว เพราะวัดผลไปแล้วใน Phase 2
    ตอนนี้คือการเอาไปใช้จริง จึงให้โมเดลเห็นข้อมูลมากที่สุด)"""
    from evaluate import make_model   # import ตรงนี้ เพื่อให้ไฟล์นี้ใช้ได้แม้ยังไม่ลง scikit-learn

    model = make_model()
    model.fit(url_df["hostname"], url_df["label"])
    return model


def score_reports(reports, model):
    """เพิ่มคอลัมน์ hostname, scam_prob, count_weight, priority_score ให้ตารางรายงาน

    รายงานที่ไม่มี url ได้ scam_prob = 0 เพราะโมเดลดูแค่ hostname
    (ข้อจำกัด: SMS หลอกให้โทรกลับโดยไม่มีลิงก์จะไปอยู่ท้ายคิว)
    """
    out = reports.copy()
    out["hostname"] = out["url"].map(hostname_of)
    has_host = out["hostname"].notna()
    out["scam_prob"] = 0.0
    if has_host.any():
        # predict_proba คืน [prob ปกติ, prob scam] เราเอาคอลัมน์ที่ 2 (scam)
        out.loc[has_host, "scam_prob"] = model.predict_proba(out.loc[has_host, "hostname"])[:, 1]
    out["count_weight"] = out["report_count"].map(count_weight)
    out["priority_score"] = out["scam_prob"] * out["count_weight"]
    return out


def build_triage(con, model):
    """อ่าน clean.reports → ให้คะแนน → เขียนทับ mart.triage แล้วคืนจำนวนแถว"""
    reports = con.execute(
        "SELECT report_id, reported_at, sender, message_text, url, report_count FROM clean.reports"
    ).df()
    scored = score_reports(reports, model)
    con.register("scored", scored)
    con.execute("CREATE SCHEMA IF NOT EXISTS mart")
    # คะแนนเท่ากัน: ตัดสินด้วยคนแจ้งมากกว่า แล้วแจ้งก่อนได้ตรวจก่อน
    con.execute("""
        CREATE OR REPLACE TABLE mart.triage AS
        SELECT
            report_id, reported_at, sender, message_text, url, report_count,
            hostname, scam_prob, count_weight, priority_score,
            rank() OVER (ORDER BY priority_score DESC, report_count DESC, reported_at) AS review_rank
        FROM scored
    """)
    con.unregister("scored")
    return con.execute("SELECT count(*) FROM mart.triage").fetchone()[0]


def top_n(con, n=TOP_N):
    return con.execute(f"""
        SELECT review_rank, report_id, hostname, report_count,
               round(scam_prob, 3) AS scam_prob, round(priority_score, 3) AS priority_score
        FROM mart.triage ORDER BY review_rank LIMIT {int(n)}
    """).df()


def scam_in_top_n(con, n=TOP_N):
    """ใช้ synthetic_label (เฉลยของข้อมูลสังเคราะห์) นับว่า top N มี scam กี่อัน
    เทียบระหว่างเรียงด้วย report_count อย่างเดียว (แบบเดิม) กับ priority_score (แบบใหม่)
    ใช้ตรวจผลเท่านั้น ไม่ได้ใช้สอนโมเดล"""
    sql = """
        SELECT count(*) FILTER (WHERE c.synthetic_label = 'scam') FROM (
            SELECT t.report_id FROM mart.triage t ORDER BY {order} LIMIT {n}
        ) top JOIN clean.reports c USING (report_id)
    """
    old = con.execute(sql.format(order="t.report_count DESC, t.reported_at", n=int(n))).fetchone()[0]
    new = con.execute(sql.format(order="t.review_rank", n=int(n))).fetchone()[0]
    return old, new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--urls", default=str(DEFAULT_URLS))
    args = ap.parse_args()

    model = train_model(pd.read_csv(args.urls))
    con = duckdb.connect(args.db)
    n = build_triage(con, model)
    print(f"mart.triage: {n} rows (scored by model)")
    print(f"\nTop {TOP_N} to review:")
    print(top_n(con).to_string(index=False))
    print("\nscam in top N (synthetic_label, check only): report_count only vs priority_score")
    for k in [20, 100, 500, 1000]:
        old, new = scam_in_top_n(con, k)
        print(f"  top {k:>4}: {old:>4} vs {new:>4}")
    con.close()


if __name__ == "__main__":
    main()
