-- =====================================================================
-- DSA 2050 Water Supply Reliability Monitoring - SQL (SQLite)
-- Database: data/processed/water.db  (built by notebooks/01_acquisition_quality.ipynb)
--
-- Tables
--   bills_raw        dataset A as downloaded (all text)            one row per meter bill
--   bills_clean      dataset A after cleaning rules C1-C9 (typed)  one row per meter bill
--   developments     dataset B, standardised                       one row per development (PK tds)
--   complaints_raw   dataset C, 311 counts                          borough x month x descriptor
--   weather_daily    dataset D                                      one row per day
--
-- Keys
--   developments.tds        PRIMARY KEY (unique development ID)
--   bills_*.tds             FOREIGN KEY -> developments.tds
--   bills_*.revenue_month   'YYYY-MM' -> weather_monthly.month, complaints_monthly.month
--   bills_*.borough         -> complaints_monthly.borough
--
-- Each block starts with "-- name: <name>". The notebooks run blocks by name
-- with water_utils.run(con, "<name>"). You can also paste any block into
-- DB Browser for SQLite or the sqlite3 shell.
-- =====================================================================


-- name: q01_row_counts
-- Q1. How many rows are in each table? (first row-count check)
SELECT 'bills_raw'      AS table_name, COUNT(*) AS n_rows FROM bills_raw
UNION ALL SELECT 'developments',   COUNT(*) FROM developments
UNION ALL SELECT 'complaints_raw', COUNT(*) FROM complaints_raw
UNION ALL SELECT 'weather_daily',  COUNT(*) FROM weather_daily;


-- name: q02_bills_by_borough
-- Q2. GROUP BY: size of the meter data per borough, and how often meters were NOT read.
SELECT  UPPER(TRIM(borough))                                   AS borough,
        COUNT(*)                                               AS bills,
        COUNT(DISTINCT tds)                                    AS developments,
        COUNT(DISTINCT meter_number)                           AS meters,
        ROUND(100.0 * SUM(CASE WHEN UPPER(estimated) = 'Y' THEN 1 ELSE 0 END) / COUNT(*), 1)
                                                               AS pct_estimated,
        ROUND(SUM(CAST(consumption_hcf AS REAL)), 0)           AS total_hcf
FROM    bills_raw
GROUP BY UPPER(TRIM(borough))
ORDER BY bills DESC;


-- name: q03_filter_largest_actual_2024
-- Q3. WHERE filter + ORDER BY: the 20 largest ACTUAL (not estimated) meter bills in 2024.
SELECT  development_name, borough, meter_number, revenue_month,
        CAST(days AS INTEGER)            AS days,
        CAST(consumption_hcf AS REAL)    AS consumption_hcf,
        ROUND(CAST(consumption_hcf AS REAL) / CAST(days AS REAL), 1) AS hcf_per_day
FROM    bills_raw
WHERE   UPPER(estimated) = 'N'
  AND   revenue_month BETWEEN '2024-01' AND '2024-12'
  AND   CAST(days AS REAL) > 0
ORDER BY CAST(consumption_hcf AS REAL) DESC
LIMIT 20;


-- name: q04_missingness
-- Q4. Missing values per important column (quality audit).
SELECT  COUNT(*)                                                                    AS total_rows,
        SUM(CASE WHEN tds IS NULL OR TRIM(tds) = ''                       THEN 1 ELSE 0 END) AS missing_tds,
        SUM(CASE WHEN revenue_month IS NULL OR TRIM(revenue_month) = ''   THEN 1 ELSE 0 END) AS missing_month,
        SUM(CASE WHEN consumption_hcf IS NULL OR TRIM(consumption_hcf) = '' THEN 1 ELSE 0 END) AS missing_consumption,
        SUM(CASE WHEN days IS NULL OR TRIM(days) = ''                     THEN 1 ELSE 0 END) AS missing_days,
        SUM(CASE WHEN meter_number IS NULL OR TRIM(meter_number) = ''     THEN 1 ELSE 0 END) AS missing_meter,
        SUM(CASE WHEN estimated IS NULL OR TRIM(estimated) = ''           THEN 1 ELSE 0 END) AS missing_estimated_flag
FROM    bills_raw;


-- name: q05_duplicates
-- Q5. GROUP BY ... HAVING: the same meter billed more than once for the same month.
--     (Some are true duplicates; some are two billing periods in one month.)
SELECT  tds, meter_number, revenue_month, COUNT(*) AS n_rows,
        GROUP_CONCAT(estimated) AS estimated_flags
FROM    bills_raw
GROUP BY tds, meter_number, revenue_month
HAVING  COUNT(*) > 1
ORDER BY n_rows DESC
LIMIT 50;


-- name: q06_type_and_range_checks
-- Q6. Impossible or suspicious values (types, ranges, outliers to investigate).
SELECT  SUM(CASE WHEN CAST(consumption_hcf AS REAL) < 0  THEN 1 ELSE 0 END) AS negative_consumption,
        SUM(CASE WHEN CAST(consumption_hcf AS REAL) = 0  THEN 1 ELSE 0 END) AS zero_consumption,
        SUM(CASE WHEN CAST(days AS REAL) <= 0            THEN 1 ELSE 0 END) AS non_positive_days,
        SUM(CASE WHEN CAST(days AS REAL) > 62            THEN 1 ELSE 0 END) AS days_over_62,
        SUM(CASE WHEN meter_number IS NULL OR TRIM(meter_number) = ''
                   OR UPPER(meter_number) LIKE '%UN-METER%' THEN 1 ELSE 0 END)   AS no_meter,
        SUM(CASE WHEN UPPER(meter_number) LIKE '%SEWER%' OR UPPER(meter_number) LIKE '%FIRE%'
                   OR UPPER(rate_class) IN ('MWW SWR','FIRE','FRONTAGEWW') THEN 1 ELSE 0 END) AS sewer_or_fire_lines,
        SUM(CASE WHEN UPPER(TRIM(borough)) NOT IN
                 ('BRONX','BROOKLYN','MANHATTAN','QUEENS','STATEN ISLAND') THEN 1 ELSE 0 END) AS non_borough_value,
        MIN(revenue_month) AS first_month, MAX(revenue_month) AS last_month
FROM    bills_raw;


-- name: q07_join_validation
-- Q7. JOIN + ROW-COUNT VALIDATION. A LEFT JOIN keeps every bill. If the
--     developments table had duplicate TDS values the row count would GROW
--     ("fan-out"); unmatched bills show up with a NULL development.
SELECT  (SELECT COUNT(*) FROM bills_clean)                        AS rows_before_join,
        COUNT(*)                                                  AS rows_after_left_join,
        SUM(CASE WHEN d.tds IS NOT NULL THEN 1 ELSE 0 END)        AS matched_rows,
        SUM(CASE WHEN d.tds IS NULL     THEN 1 ELSE 0 END)        AS unmatched_rows,
        ROUND(100.0 * SUM(CASE WHEN d.tds IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_unmatched,
        COUNT(DISTINCT b.tds)                                     AS distinct_tds_in_bills,
        COUNT(DISTINCT CASE WHEN d.tds IS NULL THEN b.tds END)    AS distinct_tds_unmatched
FROM    bills_clean AS b
LEFT JOIN developments AS d
       ON d.tds = b.tds;


-- name: q08_unmatched_developments
-- Q8. Which developments in the bills have no match in the Data Book? (explain each in the decisions log:
--     usually developments converted to PACT/RAD or demolished before the current Data Book edition)
SELECT  b.tds, MIN(b.development_name) AS development_name, MIN(b.borough) AS borough,
        COUNT(*) AS bills, MIN(b.revenue_month) AS first_month, MAX(b.revenue_month) AS last_month
FROM    bills_clean AS b
LEFT JOIN developments AS d ON d.tds = b.tds
WHERE   d.tds IS NULL
GROUP BY b.tds
ORDER BY bills DESC;


-- name: q09_recurring_measurement_gaps
-- Q9. JOIN + GROUP BY + HAVING: developments whose meters are most often NOT read
--     (recurring measurement gaps, a reliability problem of the metering itself).
SELECT  b.tds, d.development, b.borough, d.apartments,
        COUNT(*)                                         AS bills,
        SUM(b.is_estimated)                              AS estimated_bills,
        ROUND(100.0 * SUM(b.is_estimated) / COUNT(*), 1) AS pct_estimated
FROM    bills_clean AS b
JOIN    developments AS d ON d.tds = b.tds
GROUP BY b.tds, d.development, b.borough, d.apartments
HAVING  COUNT(*) >= 24
ORDER BY pct_estimated DESC
LIMIT 25;


-- name: q10_complaints_by_borough_year
-- Q10. 311 water-system complaints per borough per year, split by type.
SELECT  UPPER(TRIM(borough))   AS borough,
        SUBSTR(month, 1, 4)    AS year,
        SUM(n)                 AS complaints,
        SUM(CASE WHEN UPPER(descriptor) LIKE '%NO WATER%'     THEN n ELSE 0 END) AS no_water,
        SUM(CASE WHEN UPPER(descriptor) LIKE '%LOW%PRESSURE%' THEN n ELSE 0 END) AS low_pressure,
        SUM(CASE WHEN UPPER(descriptor) LIKE '%MAIN BREAK%'   THEN n ELSE 0 END) AS main_break,
        SUM(CASE WHEN UPPER(descriptor) LIKE 'LEAK%'          THEN n ELSE 0 END) AS leak
FROM    complaints_raw
GROUP BY UPPER(TRIM(borough)), SUBSTR(month, 1, 4)
ORDER BY borough, year;


-- name: q11_descriptor_list
-- Q11. Discovery query: which 311 descriptors exist? Run this BEFORE trusting the LIKE patterns above.
SELECT descriptor, SUM(n) AS complaints
FROM   complaints_raw
GROUP BY descriptor
ORDER BY complaints DESC;


-- name: v01_monthly_views
-- V1. Views that turn daily weather and raw 311 counts into monthly tables.
DROP VIEW IF EXISTS weather_monthly;
CREATE VIEW weather_monthly AS
SELECT  SUBSTR(date, 1, 7)                                          AS month,
        ROUND(AVG(temperature_2m_mean), 2)                          AS temp_mean,
        MAX(temperature_2m_max)                                     AS temp_max,
        MIN(temperature_2m_min)                                     AS temp_min,
        ROUND(SUM(precipitation_sum), 1)                            AS precip_mm,
        ROUND(SUM(snowfall_sum), 1)                                 AS snow_cm,
        SUM(CASE WHEN temperature_2m_min < -5 THEN 1 ELSE 0 END)    AS freeze_days,
        SUM(CASE WHEN temperature_2m_max > 30 THEN 1 ELSE 0 END)    AS hot_days
FROM    weather_daily
GROUP BY SUBSTR(date, 1, 7);

DROP VIEW IF EXISTS complaints_monthly;
-- 311 complaint groups (descriptor list checked with q11):
--   supply disruption = no water, low pressure, possible main break  -> used for corroboration
--   leak = street/building leak (WA2);  hydrant = hydrant problems (mostly summer openings, NOT supply failures)
CREATE VIEW complaints_monthly AS
SELECT  UPPER(TRIM(borough)) AS borough,
        SUBSTR(month, 1, 7)  AS month,
        SUM(n)               AS complaints_total,
        SUM(CASE WHEN UPPER(descriptor) LIKE '%NO WATER%'
                   OR UPPER(descriptor) LIKE '%LOW WATER PRESSURE%'
                   OR UPPER(descriptor) LIKE '%LOW PRESSURE%'
                   OR UPPER(descriptor) LIKE '%MAIN BREAK%' THEN n ELSE 0 END)          AS c_supply,
        SUM(CASE WHEN UPPER(descriptor) LIKE '%NO WATER%' THEN n ELSE 0 END)         AS c_no_water,
        SUM(CASE WHEN UPPER(descriptor) LIKE '%LOW%PRESSURE%' THEN n ELSE 0 END)     AS c_low_pressure,
        SUM(CASE WHEN UPPER(descriptor) LIKE '%MAIN BREAK%' THEN n ELSE 0 END)       AS c_main_break,
        SUM(CASE WHEN UPPER(descriptor) LIKE 'LEAK%' THEN n ELSE 0 END)              AS c_leak,
        SUM(CASE WHEN UPPER(descriptor) LIKE '%HYDRANT%' OR UPPER(descriptor) LIKE 'HYD %' THEN n ELSE 0 END) AS c_hydrant
FROM    complaints_raw
WHERE   UPPER(TRIM(borough)) IN ('BRONX','BROOKLYN','MANHATTAN','QUEENS','STATEN ISLAND')
GROUP BY UPPER(TRIM(borough)), SUBSTR(month, 1, 7);


-- name: q12_development_month_panel
-- Q12. The analysis table. Two GROUP BY levels and three LEFT JOINs:
--   step 1 (meter_month): one row per meter per month (sums split billing periods)
--   step 2 (dev_month)  : one row per development per month (sums meters)
--   step 3              : add development size, monthly weather and borough 311 counts
WITH meter_month AS (
    SELECT  tds, revenue_month, meter_number, borough,
            SUM(consumption_hcf)                  AS hcf,
            SUM(days)                             AS days,
            MAX(is_estimated)                     AS est,
            SUM(water_sewer_charges)              AS charges
    FROM    bills_clean
    GROUP BY tds, revenue_month, meter_number, borough
),
dev_month AS (
    SELECT  tds, revenue_month,
            MIN(borough)                          AS borough,
            COUNT(*)                              AS n_meters,
            SUM(est)                              AS n_est_meters,
            SUM(CASE WHEN hcf = 0 THEN 1 ELSE 0 END) AS n_zero_meters,
            SUM(hcf)                              AS hcf,
            SUM(hcf * 1.0 / days)                 AS hcf_per_day,
            SUM(charges)                          AS charges
    FROM    meter_month
    GROUP BY tds, revenue_month
)
SELECT  m.*,
        d.development, d.apartments, d.population, d.res_buildings,
        w.temp_mean, w.temp_max, w.temp_min, w.precip_mm, w.snow_cm, w.freeze_days, w.hot_days,
        c.complaints_total, c.c_supply, c.c_no_water, c.c_low_pressure, c.c_main_break, c.c_leak, c.c_hydrant
FROM    dev_month AS m
LEFT JOIN developments       AS d ON d.tds = m.tds
LEFT JOIN weather_monthly    AS w ON w.month = m.revenue_month
LEFT JOIN complaints_monthly AS c ON c.borough = m.borough AND c.month = m.revenue_month
ORDER BY m.tds, m.revenue_month;


-- name: q13_panel_join_check
-- Q13. Row-count check for the panel: the joins must not add or lose rows.
WITH dev_month AS (
    SELECT tds, revenue_month, MIN(borough) AS borough FROM bills_clean GROUP BY tds, revenue_month
)
SELECT  (SELECT COUNT(*) FROM dev_month)                                   AS dev_months,
        COUNT(*)                                                           AS after_joins,
        SUM(CASE WHEN w.month   IS NULL THEN 1 ELSE 0 END)                 AS no_weather_match,
        SUM(CASE WHEN c.borough IS NULL THEN 1 ELSE 0 END)                 AS no_311_match,
        SUM(CASE WHEN d.tds     IS NULL THEN 1 ELSE 0 END)                 AS no_devbook_match
FROM    dev_month AS m
LEFT JOIN developments       AS d ON d.tds = m.tds
LEFT JOIN weather_monthly    AS w ON w.month = m.revenue_month
LEFT JOIN complaints_monthly AS c ON c.borough = m.borough AND c.month = m.revenue_month;
