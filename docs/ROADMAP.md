# Roadmap (8 weeks, ~1–1.5 h/day)

Rule: finish a phase, commit, and update the README before starting the next one.

## Phase 0 — Setup (week 1)
- [ ] `git init`, first commit, push to GitHub
- [ ] Run the quick start end to end (generate → load → SQL → checks → pytest)
- [ ] Read through every file in `src/` and `sql/` once; write a one-line comment on anything unclear

## Phase 1 — Data Engineering (weeks 2–3)
- [x] Understand each layer: `raw` (as-is), `clean` (typed + deduped), `mart` (aggregated)
- [x] Add 3 more quality checks of your own (e.g. future timestamps, URL scheme, report_count < 1)
- [x] Make `quality_checks.py` exit with code 1 when a check fails
- [x] Add 2 pytest tests for the cleaning logic
- [x] Write an architecture diagram in the README (replace the ASCII one if you like)

## Phase 2 — Data Science (weeks 4–6)
- [x] Download a public phishing URL feed into `data/raw/` (note the source and date in the README)
- [x] URL features: length, digit count, `-` count, brand keyword present, edit distance to official domains
- [x] Baseline: a rule-based flag (brand keyword + domain not official)
- [x] Model: TF-IDF + Logistic Regression (scikit-learn)
- [x] Evaluate on a held-out split: precision, recall, confusion matrix — report both baseline and model

## Phase 3 — Triage output (weeks 7–8)
- [x] Priority score = model probability × report_count weight (write down why)
- [x] `mart.triage` ranked table; one Streamlit page or notebook that shows the top 20
- [x] Final README: results table, limitations, what you would do next

## Stretch (after you apply)
- Airflow or dbt, PyThaiNLP tokenization, a live public feed
