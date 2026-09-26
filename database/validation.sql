-- =============================================================================
-- database/validation.sql
-- JourneyIQ — Stage 2 Data Quality Checks
--
-- Run this in psql after loading data:
--   psql -U postgres -d journeyiq -f database/validation.sql
--
-- Each query is labelled with what it checks and what a PASS looks like.
-- =============================================================================


-- =============================================================================
-- SECTION 1: Basic row counts
-- PASS: matches the numbers reported by generate_data.py
-- =============================================================================

\echo '============================================================'
\echo 'CHECK 1: Row counts per table'
\echo 'Expected: ~500 customers, ~18 campaigns, ~3000+ events, ~50+ conversions'
\echo '============================================================'

SELECT
    'customers'   AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL
SELECT
    'campaigns',                  COUNT(*) FROM campaigns
UNION ALL
SELECT
    'events',                     COUNT(*) FROM events
UNION ALL
SELECT
    'conversions',                COUNT(*) FROM conversions
ORDER BY table_name;


-- =============================================================================
-- CHECK 2: Channel distribution in events
-- PASS: all 10 channels present, Google Search / Instagram at top
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'CHECK 2: Event count by channel'
\echo 'Expected: all 10 channels present'
\echo '============================================================'

SELECT
    channel,
    COUNT(*)                                    AS event_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM events
GROUP BY channel
ORDER BY event_count DESC;


-- =============================================================================
-- CHECK 3: Event type distribution (funnel shape)
-- PASS: impression/click/page_view > product_view > add_to_cart > checkout
-- This is the classic drop-off funnel — each step should have fewer rows.
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'CHECK 3: Event count by type (funnel shape)'
\echo 'Expected: impression > click > page_view > product_view > add_to_cart > checkout'
\echo '============================================================'

SELECT
    event_type,
    COUNT(*)                                    AS event_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM events
GROUP BY event_type
ORDER BY event_count DESC;


-- =============================================================================
-- CHECK 4: Revenue summary
-- PASS: total revenue > 0, reasonable min/max, positive mean
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'CHECK 4: Revenue statistics'
\echo 'Expected: min ~$10, median ~$80, max ~$500, total depends on conversion count'
\echo '============================================================'

SELECT
    COUNT(*)                    AS conversion_count,
    ROUND(MIN(revenue), 2)      AS min_revenue,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY revenue)::numeric, 2)
                                AS median_revenue,
    ROUND(AVG(revenue)::numeric, 2)      AS avg_revenue,
    ROUND(MAX(revenue), 2)      AS max_revenue,
    ROUND(SUM(revenue)::numeric, 2)      AS total_revenue
FROM conversions;


-- =============================================================================
-- CHECK 5: Conversion rate
-- PASS: ~30-40% of customers who checked out converted
-- Formula: converters / customers_who_checked_out
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'CHECK 5: Conversion rate'
\echo 'Expected: ~30-40% of checkout customers converted'
\echo '============================================================'

WITH checkout_customers AS (
    SELECT DISTINCT customer_id
    FROM events
    WHERE event_type = 'checkout'
),
converters AS (
    SELECT DISTINCT customer_id
    FROM conversions
)
SELECT
    COUNT(DISTINCT cc.customer_id)           AS customers_who_checked_out,
    COUNT(DISTINCT c.customer_id)            AS customers_who_converted,
    ROUND(
        COUNT(DISTINCT c.customer_id) * 100.0
        / NULLIF(COUNT(DISTINCT cc.customer_id), 0),
    1)                                       AS conversion_rate_pct
FROM checkout_customers cc
LEFT JOIN converters c USING (customer_id);


-- =============================================================================
-- CHECK 6: Orphan events
-- PASS: 0 rows (every event links to a real customer)
-- An "orphan event" is an event whose customer_id doesn't exist in customers.
-- This would violate the FK constraint — but let's verify explicitly.
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'CHECK 6: Orphan events (events with no matching customer)'
\echo 'Expected: 0 rows'
\echo '============================================================'

SELECT COUNT(*) AS orphan_event_count
FROM events e
WHERE NOT EXISTS (
    SELECT 1 FROM customers c WHERE c.customer_id = e.customer_id
);


-- =============================================================================
-- CHECK 7: Orphan conversions
-- PASS: 0 rows (every conversion links to a real customer)
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'CHECK 7: Orphan conversions (conversions with no matching customer)'
\echo 'Expected: 0 rows'
\echo '============================================================'

SELECT COUNT(*) AS orphan_conversion_count
FROM conversions cv
WHERE NOT EXISTS (
    SELECT 1 FROM customers c WHERE c.customer_id = cv.customer_id
);


-- =============================================================================
-- CHECK 8: Invalid timestamps — events before customer first_seen
-- PASS: 0 rows (no event can happen before the customer was first observed)
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'CHECK 8: Events before customer first_seen'
\echo 'Expected: 0 rows'
\echo '============================================================'

SELECT COUNT(*) AS events_before_first_seen
FROM events e
JOIN customers c USING (customer_id)
WHERE e.timestamp < c.first_seen;


-- =============================================================================
-- CHECK 9: Conversions before checkout
-- PASS: 0 rows (a purchase cannot happen before the customer checked out)
-- This is the most important business logic check.
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'CHECK 9: Conversions before last checkout event'
\echo 'Expected: 0 rows'
\echo '============================================================'

WITH last_checkout AS (
    SELECT
        customer_id,
        MAX(timestamp) AS last_checkout_ts
    FROM events
    WHERE event_type = 'checkout'
    GROUP BY customer_id
)
SELECT COUNT(*) AS conversions_before_checkout
FROM conversions cv
JOIN last_checkout lc USING (customer_id)
WHERE cv.timestamp <= lc.last_checkout_ts;


-- =============================================================================
-- CHECK 10: Duplicate order IDs
-- PASS: 0 rows (each order_id must be unique — enforced by DB constraint,
-- but we verify explicitly)
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'CHECK 10: Duplicate order_ids'
\echo 'Expected: 0 rows'
\echo '============================================================'

SELECT order_id, COUNT(*) AS occurrences
FROM conversions
GROUP BY order_id
HAVING COUNT(*) > 1;


-- =============================================================================
-- CHECK 11: Campaign coverage
-- PASS: all campaigns have at least some events attributed to them
-- If a campaign has 0 events, it may be out of the event date range.
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'CHECK 11: Events per campaign (including campaigns with 0 events)'
\echo 'Expected: most campaigns have events; some may have 0 if inactive in window'
\echo '============================================================'

SELECT
    c.name,
    c.channel,
    c.start_date,
    c.end_date,
    COUNT(e.id) AS event_count
FROM campaigns c
LEFT JOIN events e ON e.campaign_id = c.campaign_id
GROUP BY c.campaign_id, c.name, c.channel, c.start_date, c.end_date
ORDER BY event_count DESC;


-- =============================================================================
-- CHECK 12: Events outside their campaign's active date range
-- PASS: 0 rows (enforced by the generator, verified here)
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'CHECK 12: Events attributed to campaigns outside their date range'
\echo 'Expected: 0 rows'
\echo '============================================================'

SELECT COUNT(*) AS events_outside_campaign_window
FROM events e
JOIN campaigns c ON e.campaign_id = c.campaign_id
WHERE e.timestamp::date < c.start_date
   OR e.timestamp::date > c.end_date;


-- =============================================================================
-- SUMMARY DASHBOARD
-- A quick single-view summary of key metrics
-- =============================================================================

\echo ''
\echo '============================================================'
\echo 'SUMMARY DASHBOARD'
\echo '============================================================'

SELECT
    (SELECT COUNT(*) FROM customers)                            AS total_customers,
    (SELECT COUNT(*) FROM campaigns)                           AS total_campaigns,
    (SELECT COUNT(*) FROM events)                              AS total_events,
    (SELECT COUNT(*) FROM conversions)                         AS total_conversions,
    (SELECT ROUND(SUM(revenue)::numeric, 2) FROM conversions)  AS total_revenue,
    (SELECT COUNT(DISTINCT customer_id) FROM events
     WHERE event_type = 'checkout')                            AS customers_reached_checkout,
    (SELECT COUNT(DISTINCT customer_id) FROM conversions)      AS customers_converted,
    (SELECT ROUND(
        COUNT(DISTINCT cv.customer_id) * 100.0 /
        NULLIF(COUNT(DISTINCT e.customer_id), 0)
    , 1)
     FROM conversions cv, (
         SELECT DISTINCT customer_id FROM events WHERE event_type = 'checkout'
     ) e)                                                      AS overall_conversion_rate_pct;
