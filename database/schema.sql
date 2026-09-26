-- =============================================================================
-- JourneyIQ Database Schema
-- PostgreSQL 14+
-- Purpose: Store customer journeys and campaign attribution data
-- =============================================================================

-- Drop tables in reverse dependency order (safe for re-runs)
DROP TABLE IF EXISTS conversions   CASCADE;
DROP TABLE IF EXISTS events        CASCADE;
DROP TABLE IF EXISTS campaigns     CASCADE;
DROP TABLE IF EXISTS customers     CASCADE;

-- =============================================================================
-- ENUM TYPES
-- Using enums makes the schema self-documenting and prevents bad data.
-- =============================================================================

DO $$ BEGIN
    CREATE TYPE device_type AS ENUM ('mobile', 'desktop', 'tablet');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE channel_type AS ENUM (
        'Instagram', 'Facebook', 'Google Search', 'Google Display',
        'YouTube', 'Email', 'SMS', 'Organic Search', 'Direct', 'Referral'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE event_type_enum AS ENUM (
        'impression', 'click', 'page_view', 'product_view',
        'add_to_cart', 'checkout'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE segment_type AS ENUM (
        'new_visitor', 'returning', 'loyal', 'at_risk', 'churned'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =============================================================================
-- TABLE: customers
-- One row per unique customer. This is the anchor table for all other tables.
-- =============================================================================

CREATE TABLE customers (
    id               SERIAL          PRIMARY KEY,
    customer_id      VARCHAR(36)     NOT NULL UNIQUE,   -- UUID-style business key
    first_seen       TIMESTAMPTZ     NOT NULL,          -- when we first observed this customer
    country          VARCHAR(60)     NOT NULL,
    device           device_type     NOT NULL,
    customer_segment segment_type    NOT NULL DEFAULT 'new_visitor'
);

-- Index for fast lookups by business key (used heavily in JOIN operations)
CREATE INDEX idx_customers_customer_id ON customers(customer_id);
CREATE INDEX idx_customers_country     ON customers(country);
CREATE INDEX idx_customers_segment     ON customers(customer_segment);

-- =============================================================================
-- TABLE: campaigns
-- Marketing campaigns that drive traffic. Each campaign belongs to one channel.
-- =============================================================================

CREATE TABLE campaigns (
    id           SERIAL          PRIMARY KEY,
    campaign_id  VARCHAR(36)     NOT NULL UNIQUE,   -- UUID-style business key
    name         VARCHAR(255)    NOT NULL,
    channel      channel_type    NOT NULL,
    start_date   DATE            NOT NULL,
    end_date     DATE            NOT NULL,
    budget       NUMERIC(12, 2)  NOT NULL CHECK (budget >= 0),
    spend        NUMERIC(12, 2)  NOT NULL DEFAULT 0 CHECK (spend >= 0),

    -- A campaign cannot end before it starts
    CONSTRAINT campaigns_date_order CHECK (end_date >= start_date)
);

CREATE INDEX idx_campaigns_channel    ON campaigns(channel);
CREATE INDEX idx_campaigns_start_date ON campaigns(start_date);

-- =============================================================================
-- TABLE: events
-- Every touchpoint a customer has with any channel/campaign.
-- This is the largest table and the heart of journey analysis.
-- =============================================================================

CREATE TABLE events (
    id           BIGSERIAL       PRIMARY KEY,          -- BIGSERIAL: expect millions of rows
    customer_id  VARCHAR(36)     NOT NULL,
    timestamp    TIMESTAMPTZ     NOT NULL,
    session_id   VARCHAR(36)     NOT NULL,             -- groups events within one browsing session
    channel      channel_type    NOT NULL,
    campaign_id  VARCHAR(36),                          -- NULL = organic/direct (no campaign)
    event_type   event_type_enum NOT NULL,
    page         VARCHAR(255),                         -- URL slug or page name
    product_id   VARCHAR(36),                          -- NULL for non-product pages
    device       device_type     NOT NULL,

    -- Foreign keys for referential integrity
    CONSTRAINT fk_events_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    CONSTRAINT fk_events_campaign
        FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE SET NULL
);

-- Composite index for time-range queries per customer (most common analytics query)
CREATE INDEX idx_events_customer_time   ON events(customer_id, timestamp);
CREATE INDEX idx_events_timestamp       ON events(timestamp);
CREATE INDEX idx_events_channel         ON events(channel);
CREATE INDEX idx_events_campaign_id     ON events(campaign_id);
CREATE INDEX idx_events_event_type      ON events(event_type);
CREATE INDEX idx_events_session_id      ON events(session_id);

-- =============================================================================
-- TABLE: conversions
-- A conversion = a completed purchase. Linked back to a customer.
-- Attribution models (first-touch, last-touch, etc.) JOIN this with events.
-- NOTE: No purchases are seeded in Stage 1 — table exists for future stages.
-- =============================================================================

CREATE TABLE conversions (
    id           BIGSERIAL       PRIMARY KEY,
    customer_id  VARCHAR(36)     NOT NULL,
    timestamp    TIMESTAMPTZ     NOT NULL,
    order_id     VARCHAR(36)     NOT NULL UNIQUE,
    product_id   VARCHAR(36)     NOT NULL,
    revenue      NUMERIC(10, 2)  NOT NULL CHECK (revenue > 0),

    CONSTRAINT fk_conversions_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE INDEX idx_conversions_customer_id ON conversions(customer_id);
CREATE INDEX idx_conversions_timestamp   ON conversions(timestamp);
CREATE INDEX idx_conversions_order_id    ON conversions(order_id);

-- =============================================================================
-- COMMENTS (PostgreSQL native documentation)
-- =============================================================================

COMMENT ON TABLE customers    IS 'One row per unique customer across all channels';
COMMENT ON TABLE campaigns    IS 'Paid and organic marketing campaigns';
COMMENT ON TABLE events       IS 'Every customer touchpoint — impressions, clicks, views, etc.';
COMMENT ON TABLE conversions  IS 'Completed purchases; used for attribution in later stages';

COMMENT ON COLUMN events.campaign_id IS 'NULL for channels with no associated campaign (e.g. Direct, Organic Search)';
COMMENT ON COLUMN events.session_id  IS 'Groups events from the same browsing session; one customer can have many sessions';
