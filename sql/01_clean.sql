-- raw -> clean: cast types, drop invalid rows, dedupe on report_id.
CREATE SCHEMA IF NOT EXISTS clean;

CREATE OR REPLACE TABLE clean.reports AS
WITH typed AS (
    SELECT
        report_id,
        CAST(reported_at AS TIMESTAMP)        AS reported_at,
        sender,
        NULLIF(trim(message_text), '')        AS message_text,
        NULLIF(trim(url), '')                 AS url,
        CAST(report_count AS INTEGER)         AS report_count,
        channel,
        synthetic_label
    FROM raw.reports
),
ranked AS (
    SELECT *, row_number() OVER (PARTITION BY report_id ORDER BY reported_at) AS rn
    FROM typed
)
SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1
  AND message_text IS NOT NULL
  AND report_count BETWEEN 1 AND 1000;
