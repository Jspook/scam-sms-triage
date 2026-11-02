import duckdb as dd
con = dd.connect('data/processed/triage.duckdb')
total = con.execute('select count(*) from raw.reports').fetchone()[0]
empty = con.execute("select count(*) from raw.reports where message_text is null or trim(message_text) = '' ").fetchone()[0]
count_row_clean = con.execute('select count(*) from clean.reports').fetchone()[0]
count_report_id = con.execute('select count(distinct report_id) from raw.reports').fetchone()[0]

test = con.execute(
    "SELECT * FROM raw.reports "
    "WHERE CAST(report_count AS INTEGER) NOT BETWEEN 1 AND 1000"
).fetchall()

print(f"empty message_text: {empty}")
print(f'count rows from clean.reports: {count_row_clean}')
print(f'count report_id: {count_report_id}')

print(len(test))
print(f"total rows in raw.reports: {total}")
con.close()
