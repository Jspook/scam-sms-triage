-- clean -> mart: placeholder triage table.
-- Phase 0 priority = report_count only (ใช้ได้แม้ยังไม่มีโมเดล).
-- Phase 3: python src/triage.py เขียนทับตารางนี้ด้วย scam_prob × (1 + log10(report_count)).
CREATE SCHEMA IF NOT EXISTS mart;

CREATE OR REPLACE TABLE mart.triage AS
SELECT
    report_id,
    reported_at,
    sender,
    message_text,
    url,
    report_count,
    CAST(report_count AS DOUBLE) AS priority_score,
    rank() OVER (ORDER BY report_count DESC, reported_at) AS review_rank
FROM clean.reports;
