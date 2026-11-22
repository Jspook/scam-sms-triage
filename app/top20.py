"""หน้า Streamlit แสดง 20 รายงานที่ควรตรวจก่อน (อ่านจาก mart.triage)

Streamlit = ไลบรารีที่เปลี่ยนสคริปต์ Python เป็นหน้าเว็บง่าย ๆ
รัน: streamlit run app/top20.py   (ต้องรัน src/triage.py ก่อน)
"""
from pathlib import Path

import duckdb
import streamlit as st

DB = Path(__file__).resolve().parent.parent / "data" / "processed" / "triage.duckdb"

st.title("SMS scam triage: 20 รายงานที่ควรตรวจก่อน")
st.caption("priority_score = scam_prob × (1 + log10(report_count))  ·  ข้อมูลรายงานเป็นข้อมูลสังเคราะห์")

con = duckdb.connect(str(DB), read_only=True)
cols = {r[0] for r in con.execute("DESCRIBE mart.triage").fetchall()}
if "scam_prob" not in cols:
    st.warning("mart.triage ยังเป็นแบบเดิม (เรียงด้วย report_count) ให้รัน python src/triage.py ก่อน")
    st.stop()

n = st.slider("จำนวนแถว", 5, 100, 20)
top = con.execute("""
    SELECT review_rank, report_id, reported_at, hostname, report_count,
           round(scam_prob, 3) AS scam_prob, round(priority_score, 3) AS priority_score, message_text
    FROM mart.triage ORDER BY review_rank LIMIT ?
""", [n]).df()
con.close()

st.dataframe(top, hide_index=True, use_container_width=True)
