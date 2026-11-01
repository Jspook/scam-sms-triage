"""Generate SYNTHETIC SMS scam-report data for exercising the pipeline.

This data is invented. It exists only so the pipeline has something to process.
Do NOT train the Phase 2 model on it (the labels would be circular).
Deliberate dirty rows (nulls, duplicates, bad values) are injected so the
quality checks have something to catch.
"""
import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Invented templates. Domains are fictional or reserved-style placeholders.
SCAM_TEMPLATES = [
    ("คะแนนสะสมของคุณกำลังจะหมดอายุภายใน 3 วัน กดแลกที่ {url}", "brand_lookalike"),
    ("บัญชีของคุณถูกระงับ ยืนยันตัวตนที่ {url}", "account_suspend"),
    ("คุณได้รับสิทธิ์รับเงินคืน กรอกข้อมูลที่ {url}", "refund"),
    ("พัสดุของคุณค้างจัดส่ง ชำระค่าธรรมเนียมที่ {url}", "parcel"),
]
LEGIT_TEMPLATES = [
    "รหัส OTP ของคุณคือ {otp} ห้ามบอกผู้อื่น",
    "แพ็กเกจของคุณจะหมดอายุในวันที่ {day} ต่ออายุได้ในแอปทางการ",
    "ขอบคุณที่ใช้บริการ ยอดค้างชำระของคุณคือ {amt} บาท",
]
SPAM_TEMPLATES = [
    "โปรโมชั่นพิเศษ ลด 50% วันนี้เท่านั้น ที่ร้านค้าใกล้บ้านคุณ",
    "สมัครสินเชื่อด่วน อนุมัติไว โทร {phone}",
]
LOOKALIKE_DOMAINS = ["ais-points-th", "aisthailand-bonus", "ais-rewards-claim", "my-ais-verify"]
OTHER_SCAM_DOMAINS = ["th-parcel-pay", "gov-refund-th", "bank-secure-verify"]
TLDS = ["com", "xyz", "top", "info", "vip"]


def phone():
    return "08" + "".join(random.choice("0123456789") for _ in range(8))


def make_row(i, start):
    roll = random.random()
    ts = start + timedelta(seconds=random.randint(0, 30 * 24 * 3600))
    sender = phone()
    url = ""
    if roll < 0.35:  # scam
        text, kind = random.choice(SCAM_TEMPLATES)
        pool = LOOKALIKE_DOMAINS if kind == "brand_lookalike" else OTHER_SCAM_DOMAINS
        url = f"http://{random.choice(pool)}.{random.choice(TLDS)}/{random.randint(100, 999)}"
        text = text.format(url=url)
        true_label = "scam"
        report_count = max(1, int(random.expovariate(1 / 6)))
    elif roll < 0.60:  # spam
        text = random.choice(SPAM_TEMPLATES).format(phone=phone())
        true_label = "spam"
        report_count = max(1, int(random.expovariate(1 / 2)))
    else:  # legit message reported by mistake
        text = random.choice(LEGIT_TEMPLATES).format(
            otp=random.randint(100000, 999999), day=random.randint(1, 28), amt=random.randint(100, 999)
        )
        true_label = "legit"
        report_count = 1
    return {
        "report_id": f"R{i:07d}",
        "reported_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "sender": sender,
        "message_text": text,
        "url": url,
        "report_count": report_count,
        "channel": random.choice(["hotline", "app", "ussd"]),
        "synthetic_label": true_label,  # for pipeline testing ONLY
    }


def inject_dirt(rows):
    """Add deliberate data-quality problems."""
    n = len(rows)
    for r in random.sample(rows, k=max(1, n // 50)):  # ~2% null message_text
        r["message_text"] = ""
    for r in random.sample(rows, k=max(1, n // 100)):  # ~1% bad report_count
        r["report_count"] = random.choice([0, -3, 99999])
    dupes = [dict(r) for r in random.sample(rows, k=max(1, n // 50))]  # ~2% duplicates
    return rows + dupes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/raw/reports_synthetic.csv")
    args = ap.parse_args()

    random.seed(args.seed)
    start = datetime(2026, 1, 1)
    rows = [make_row(i, start) for i in range(1, args.rows + 1)]
    rows = inject_dirt(rows)
    random.shuffle(rows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
