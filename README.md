# scam-sms-triage

โปรเจกต์ไปป์ไลน์ข้อมูล (data pipeline) ขนาดเล็ก พร้อมโมเดลพื้นฐาน เพื่อจัดลำดับรายงาน SMS หลอกลวง ให้รายงานที่น่าจะเป็นของจริงถูกตรวจก่อน

> **สถานะ:** จบ Phase 2 (Data Science) แล้ว: มี URL features, กฎพื้นฐาน และโมเดล TF-IDF + Logistic Regression พร้อมผลวัดบน test set ต่อไปคือ Phase 3 (Triage output) ดูแผนทั้งหมดที่ [docs/ROADMAP.md](docs/ROADMAP.md)

## ศัพท์ที่ควรรู้ก่อนอ่าน

| คำ | ความหมายแบบง่าย |
|---|---|
| Pipeline (ไปป์ไลน์) | ลำดับขั้นตอนที่ข้อมูลไหลผ่าน แต่ละขั้นรับของจากขั้นก่อนแล้วส่งต่อ |
| DuckDB | ฐานข้อมูลขนาดเล็กที่อยู่ในไฟล์เดียว ใช้ภาษา SQL สอบถามข้อมูลได้ |
| SQL | ภาษาสำหรับสั่งให้ฐานข้อมูลกรอง นับ หรือรวมข้อมูล |
| raw / clean / mart | ชั้นข้อมูล 3 ระดับ: ดิบ (เก็บตามที่ได้มา), สะอาด (แก้ชนิดข้อมูล ตัดของเสีย), พร้อมใช้ (จัดอันดับแล้ว) |
| Dedupe | ลบแถวที่ซ้ำกันให้เหลือแถวเดียว |
| NULL | "ไม่มีค่า" ไม่เหมือนกับข้อความว่าง `''` |
| Data quality check | โปรแกรมตรวจว่าข้อมูลผิดปกติหรือไม่ เช่น มีแถวซ้ำ ค่าว่าง หรือค่านอกช่วง |
| Synthetic data | ข้อมูลที่สร้างขึ้นเอง ไม่ใช่ข้อมูลจริง |
| Test (เทสต์) | โค้ดที่ตรวจโค้ดอื่นอัตโนมัติ ว่าให้ผลตามที่คาดหรือไม่ |
| Feature (ฟีเจอร์) | ตัวเลขที่ดึงออกมาจากข้อมูลดิบให้โมเดลใช้ เช่น ความยาวของ hostname |
| Label | คำตอบที่ถูกของแต่ละแถว: 1 = scam, 0 = ปกติ |
| Hostname | ส่วนชื่อเว็บใน URL เช่น `a.example.com` (ไม่รวม `https://` และ path) |
| Data leakage | โมเดลไปจับเบาะแสที่ติดมากับวิธีเก็บข้อมูล ไม่ใช่ลักษณะจริงของ scam ทำให้คะแนนสูงหลอก |
| Edit distance | จำนวนตัวอักษรที่ต้องเพิ่ม/ลบ/เปลี่ยนน้อยที่สุด เพื่อเปลี่ยนคำหนึ่งเป็นอีกคำ เช่น `shopee` → `sh0pee` = 1 |
| Train / test split | แบ่งข้อมูลเป็นส่วนให้โมเดลเรียน (train) กับส่วนเก็บไว้สอบตอนท้าย (test) |
| Precision | ในที่เราทายว่า scam ถูกจริงกี่ % |
| Recall | ใน scam ทั้งหมด เราจับได้กี่ % |
| Confusion matrix | ตาราง 2×2 นับทายถูก/ผิด: TN, FP (ปกติแต่ทายว่า scam), FN (scam ที่หลุด), TP |
| TF-IDF | วิธีแปลงข้อความเป็นตัวเลข นับชิ้นข้อความที่โผล่บ่อย และลดน้ำหนักชิ้นที่โผล่แทบทุกแถว |
| Logistic Regression | โมเดลง่าย ๆ ที่ให้น้ำหนักแต่ละชิ้น แล้วรวมเป็นความน่าจะเป็นว่าเป็น scam |

## ปัญหาที่โปรเจกต์นี้แก้

ผู้ให้บริการมือถือได้รับรายงาน SMS น่าสงสัยจากลูกค้าอย่างต่อเนื่อง (เช่น สายด่วนที่ลูกค้าแจ้งเบอร์และข้อความหลอกลวง) ทุกรายงานต้องมีคนตรวจ และปริมาณสูง SMS ฟิชชิ่ง (phishing: หลอกให้กดลิงก์เพื่อขโมยข้อมูล) ที่ปลอมเป็นแบรนด์ของผู้ให้บริการ เช่น โดเมนคล้าย `ais-points-xxx.com` มักเร่งด่วนกว่าสแปมธรรมดา

โปรเจกต์นี้ตอบคำถามเดียว: **เมื่อมีรายงาน SMS เข้ามาเป็นกอง ควรตรวจรายงานไหนก่อน?**

## ขอบเขต

| ทำในโปรเจกต์นี้ | ไม่ทำ |
|---|---|
| Pipeline แบบชุด (batch): ไฟล์รายงานดิบ → DuckDB → clean → mart | Streaming (Kafka), ตัวจัดตารางงาน (Airflow) |
| ตรวจคุณภาพข้อมูล (ค่าว่าง แถวซ้ำ ค่านอกช่วง) | บล็อกแบบเรียลไทม์ หรือสิ่งที่แตะเครือข่ายจริง |
| ฟีเจอร์จาก URL + ข้อความ → ตัวจำแนกพื้นฐาน | Deep learning, LLM |
| คะแนนความสำคัญ → ตารางจัดอันดับ | การนำขึ้นใช้งานจริง |

## ข้อมูล: อะไรจริง อะไรสังเคราะห์

| ส่วน | ที่มา | เหตุผล |
|---|---|---|
| สตรีมรายงาน (`data/raw/reports_*.csv`) | **สังเคราะห์** สร้างโดย `src/generate_reports.py` | ไม่มีข้อมูลรายงานของผู้ให้บริการที่เปิดเผยสาธารณะ ใช้ทดสอบ pipeline เท่านั้น |
| ข้อมูล URL สำหรับสอนโมเดล (Phase 2) | **ของจริง เปิดสาธารณะ**: OpenPhish (scam) + Tranco (ปกติ) ดูหัวข้อ Phase 2 ด้านล่าง | ห้ามสอนโมเดลด้วยข้อมูลที่เขียนเอง |
| ข้อความ SMS ภาษาไทย (Phase 2) | ยังไม่กำหนด: ใช้ชุดข้อมูลสาธารณะถ้ามี ถ้าไม่มีจะติดป้ายมือจำนวนน้อยและระบุชัดเจน | จะบันทึกการตัดสินใจสุดท้ายที่นี่ |

โปรเจกต์นี้ไม่ใช้ข้อมูลภายในของบริษัทใดเลย และผลบนข้อมูลสังเคราะห์ไม่บอกอะไรเกี่ยวกับประสิทธิภาพในโลกจริง

### หน้าตาข้อมูล (ตาราง `raw.reports`)

ทุกคอลัมน์เก็บเป็นข้อความ (`VARCHAR`) เพราะเราไม่อยากให้ฐานข้อมูลเดาชนิดเอง การแปลงชนิดทำใน `sql/01_clean.sql`

| คอลัมน์ | ความหมาย |
|---|---|
| `report_id` | รหัสรายงาน เช่น R0002000 (ควรไม่ซ้ำ) |
| `reported_at` | วันเวลาที่ลูกค้าแจ้ง |
| `sender` | เบอร์ที่ส่ง SMS นั้นมา |
| `message_text` | ข้อความ SMS |
| `url` | ลิงก์ในข้อความ (ว่างถ้าไม่มี) |
| `report_count` | จำนวนครั้งที่มีคนแจ้งข้อความนี้ |
| `channel` | ช่องทางที่แจ้ง: hotline, app, ussd |
| `synthetic_label` | เฉลยว่า scam / spam / legit ใช้ทดสอบ pipeline เท่านั้น ห้ามใช้สอนโมเดล |

## สถาปัตยกรรม

```
generate_reports.py ──► data/raw/reports_synthetic.csv   (5,000 reports + 100 duplicated rows)
                              │
                       load_duckdb.py
                              ▼
        ┌──────────────── DuckDB (triage.duckdb) ──────────────────┐
        │                                                           │
        │  raw.reports        5,100 rows   all columns as text,     │
        │  (as-is)                         nothing removed          │
        │      │                                                    │
        │      │  sql/01_clean.sql                                  │
        │      │    • cast types (timestamp, integer)               │
        │      │    • dedupe on report_id (-100 rows)               │
        │      │    • drop blank/NULL message_text                  │
        │      │    • drop report_count outside 1..1000             │
        │      │      (-150 report_ids in total)                    │
        │      ▼                                                    │
        │  clean.reports      4,850 rows                            │
        │      │                                                    │
        │      │  sql/02_mart.sql                                   │
        │      │    • priority_score = report_count (placeholder)   │
        │      │    • review_rank = rank() by count desc, time      │
        │      ▼                                                    │
        │  mart.triage        4,850 rows ranked for review          │
        └───────────────────────────────────────────────────────────┘
                              │
                       quality_checks.py
                         • raw: report problems only (INFO)
                         • clean: 6 checks must be 0, else exit code 1
                         • tested in tests/test_pipeline.py
```

### ตัวเลขที่ตรวจสอบแล้ว (seed 42, 5,000 รายงาน)

- raw มี **5,100 แถว** = 5,000 รายงานจริง + 100 แถวซ้ำที่ใส่ไว้ตั้งใจ
- แถวที่ข้อความว่าง/NULL: 106 แถว, แถวที่ `report_count` นอกช่วง 1–1000: 51 แถว
- clean เหลือ **4,850 แถว** (ตัดไป 100 แถวซ้ำ และอีก 150 `report_id` ที่เสีย)
- ตัวเลข 106 + 51 = 157 มากกว่า 150 เพราะบางแถวเสียมีสำเนาซ้ำ จึงนับเป็นหลายแถวใน raw แต่เป็น `report_id` เดียว (ต้องนับ "หน่วย" เดียวกันจึงเทียบกันได้)

## เริ่มใช้งานเร็ว (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python src/generate_reports.py --rows 5000 --seed 42
python src/load_duckdb.py
python src/run_sql.py
python src/quality_checks.py
python -m pytest -q
```

Phase 2 (ต้องโหลดข้อมูล URL ก่อน ดูหัวข้อ Phase 2 ด้านล่าง):

```powershell
pip install scikit-learn
python src/build_url_dataset.py
python src/feature_summary.py
python src/evaluate.py
```

## ความคืบหน้า: ทำไปแล้ว และจะทำต่อ

**ทำแล้ว (Phase 0 และ Phase 1: Data Engineering)**

- สร้าง pipeline ครบเส้น: สร้างข้อมูลสังเคราะห์ → โหลดเข้า DuckDB → clean → mart
- เข้าใจและพิสูจน์ด้วยตัวเลขว่าแต่ละชั้นตัดอะไรออก (raw 5,100 → clean 4,850)
- เพิ่มเช็กคุณภาพข้อมูลชั้น clean 3 อัน (URL ต้องขึ้นต้น `http`, เวลาต้องไม่อยู่ในอนาคต, เบอร์ต้องขึ้นต้น `08`) รวมเป็น 6 เช็กที่ต้องเป็น 0
- `quality_checks.py` ออกด้วยรหัส 1 เมื่อเช็กชั้น clean ล้มเหลว
- เขียนเทสต์ 3 ตัว: pipeline ทั้งเส้น, เช็กคุณภาพจับ URL เสียได้จริง (ใส่แถวเสียตั้งใจแล้วต้องล้ม), และกฎการ clean ทีละกฎด้วยข้อมูลที่รู้คำตอบล่วงหน้า
- ปรับสถาปัตยกรรมใน README ให้มีตัวเลขจริงกำกับ

**ทำแล้ว (Phase 2: Data Science)**

- โหลด URL scam จริงจาก OpenPhish และเว็บปกติจาก Tranco แล้วตัดเหลือแค่ hostname ทั้งสองฝั่ง เพื่อกัน data leakage (`src/build_url_dataset.py`)
- เขียน URL features 6 ตัว พร้อมเทสต์ (`src/url_features.py`, `tests/test_url_features.py`): ความยาว, จำนวนตัวเลข, จำนวน `-`, มีคำแบรนด์ไหม, เป็นโดเมนทางการไหม, edit distance ถึงคำแบรนด์ (เขียนฟังก์ชัน Levenshtein เอง)
- ส่องข้อมูล (EDA) เทียบค่าเฉลี่ย feature ระหว่าง scam กับปกติ (`src/feature_summary.py`)
- ทำกฎพื้นฐาน (baseline) และโมเดล TF-IDF + Logistic Regression แล้ววัดผลบน test set เดียวกัน (`src/evaluate.py`)
- ดูตัวอย่างที่โมเดลทายผิด (error analysis) เพื่อหาสิ่งที่ควรปรับต่อ

## Phase 2 — แหล่งข้อมูล URL

| ข้อมูล | แหล่ง | label | วันที่โหลด |
|---|---|---|---|
| URL หลอกลวง | OpenPhish free feed (https://openphish.com/feed.txt) | 1 | 2026-11-18 |
| เว็บปกติ | Tranco top 1M (https://tranco-list.eu) สุ่ม 3,000 จาก top 100k | 0 | 2026-11-18 |

ไฟล์ใน `data/raw/` ไม่ขึ้น GitHub ให้โหลดเองด้วยคำสั่งนี้ใน PowerShell แล้วรัน `python src/build_url_dataset.py`

```powershell
Invoke-WebRequest https://openphish.com/feed.txt -OutFile data/raw/openphish_feed.txt
Invoke-WebRequest https://tranco-list.eu/top-1m.csv.zip -OutFile data/raw/tranco.zip
Expand-Archive data/raw/tranco.zip -DestinationPath data/raw/tranco
```

ผลลัพธ์รอบนี้: phish=289, legit=3000 (OpenPhish มี 300 URL แต่บางอันใช้ hostname เดียวกัน พอตัด path ทิ้งจึงเหลือ 289)

ทำไมต้องตัดเหลือ hostname: URL ของ OpenPhish มี `https://` และ path เสมอ แต่ Tranco มีแค่ชื่อโดเมน ถ้าไม่ตัด โมเดลจะเรียนแค่ว่า "มี `https://` = scam" ได้คะแนนสูงหลอก ๆ แลกกับการเสียเบาะแสใน path (เช่น `/login.php`)

### ส่องข้อมูล: ค่าเฉลี่ยของแต่ละ feature

| feature | ปกติ (0) | scam (1) |
|---|---|---|
| length | 12.56 | 31.61 |
| digits | 0.15 | 4.14 |
| hyphens | 0.10 | 1.96 |
| has_brand | 0.00 | 0.03 |
| is_official | 0.00 | 0.00 |
| brand_distance | 2.88 | 2.55 |

ความยาว ตัวเลข และขีด ต่างกันชัด แต่ feature เรื่องแบรนด์แทบไม่ช่วย เพราะลิสต์แบรนด์เน้นแบรนด์ไทย 7 แบรนด์ ส่วน OpenPhish เป็นฟีดทั่วโลก

## ผลลัพธ์ (Phase 2)

Test set: 823 hostname (scam 72) แบ่งแบบ stratified 25%, seed 42 รันด้วย `python src/evaluate.py`

| โมเดล | Precision | Recall | TP | FP | FN |
|---|---|---|---|---|---|
| Baseline (มีคำแบรนด์ + ไม่ใช่โดเมนทางการ) | 1.000 | 0.042 | 3 | 0 | 69 |
| TF-IDF (ตัวอักษรติดกัน 3–5 ตัว) + Logistic Regression | 0.955 | 0.875 | 63 | 3 | 9 |

กฎพื้นฐานระวังมาก ทายว่า scam แค่ 3 ครั้ง ถูกทั้งหมดแต่หลุดเกือบทั้งหมด โมเดลกล้าทายมากขึ้น (66 ครั้ง) ยอมเสีย precision 4.5% แลกกับ recall เพิ่มจาก 4% เป็น 88%

ใช้ `class_weight="balanced"` เพราะข้อมูลไม่สมดุล (scam 1 : ปกติ 10) และ `fit` เฉพาะส่วน train เท่านั้น

### ตัวที่โมเดลทายผิด

- **เว็บปกติที่โดนกล่าวหา (FP):** `infoblox.com`, `www.gov.mo`, `livedrawsdy.page` มีชิ้นตัวอักษรที่เจอบ่อยใน scam ชุดนี้ เช่น `info` และ `gov`
- **scam ที่หลุด (FN):** ส่วนใหญ่ปลอมแบรนด์ที่ไม่อยู่ในลิสต์ของเรา เช่น `promos.rnovistar.com` (ใช้ `rn` แทน `m` ปลอมเป็น movistar), `rbx-account-check.netlify.app` (Roblox), `opensea.enter-elysium.net`, `irs-gov-report.netlify.app` และบางอันสั้นเรียบจนดูเหมือนเว็บปกติ เช่น `rbx.tg`

## ข้อจำกัด

- ข้อมูลใน pipeline (รายงาน SMS) เป็นข้อมูลสังเคราะห์ ส่วนโมเดล Phase 2 สอนด้วย URL จริง แต่ยังไม่ได้เอามาใช้กับรายงาน SMS
- **ผลน่าจะสูงเกินจริง:** scam มักมี subdomain ยาวบนโฮสต์ฟรี (`blogspot.com`, `pages.dev`, `netlify.app`) ส่วน Tranco เป็นโดเมนหลักสั้น ๆ โมเดลอาจเรียน "ความยาว/โฮสต์ฟรี" มากกว่าลักษณะ scam จริง
- ข้อมูลน้อย: scam แค่ 289 hostname จากฟีดวันเดียว (2026-11-18) และ test มี scam แค่ 72 อัน ตัวเลขจึงแกว่งได้มากถ้าเปลี่ยน seed
- ตัด path ทิ้ง จึงไม่ได้ใช้เบาะแสอย่าง `/login.php`
- ลิสต์แบรนด์มีแค่ 7 แบรนด์ เน้นไทย ขณะที่ฟีดเป็นของทั่วโลก
- เว็บใน Tranco ไม่ได้รับประกันว่าปลอดภัย 100% แค่เป็นเว็บที่คนเข้าเยอะ
- ไม่ได้อ้างว่าพร้อมใช้งานจริง

## ทำอะไรต่อ

- เพิ่มแบรนด์ทั่วโลกที่เจอในตัวที่หลุด (Microsoft, Roblox, OpenSea, Movistar, IRS) และแปลง homoglyph (`rn`→`m`, `0`→`o`, `1`→`l`) ก่อนคำนวณ edit distance
- หาเว็บปกติที่อยู่บนโฮสต์ฟรีเหมือนกัน (เช่น blog จริงบน `blogspot.com`) มาใส่ฝั่งปกติ เพื่อลดรอยรั่ว
- โหลดฟีดหลายวันแล้วทดสอบกับวันที่ใหม่กว่าวันที่ train (ใกล้การใช้งานจริงกว่าแบ่งแบบสุ่ม)
- Phase 3: เอาความน่าจะเป็นจากโมเดลมาคูณกับน้ำหนักของ `report_count` เป็นคะแนนจัดลำดับ

## แผนงาน

ดู [docs/ROADMAP.md](docs/ROADMAP.md)
