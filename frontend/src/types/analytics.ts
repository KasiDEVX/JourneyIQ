// -*- coding: utf-8 -*-
/**
 * TypeScript definitions corresponding to JourneyIQ backend schemas.
 */

export interface OverviewAnalytics {
  customers: number;
  events: number;
  sessions: number;
  conversions: number;
  conversion_rate: number;
  total_revenue: number;
  average_order_value: number;
  average_journey_duration_minutes: number;
  average_touchpoints: number;
  unique_channels: number;
}

export interface ChannelAnalytics {
  channel: string;
  customers: number;
  events: number;
  sessions: number;
  conversions: number;
  conversion_rate: number;
  revenue: number;
  average_revenue: number;
}

export interface AttributionChannel {
  channel: string;
  credit: number;
  attributed_revenue: number;
}

export interface AttributionAnalytics {
  model: string;
  total_revenue: number;
  channels: AttributionChannel[];
}

export interface AttributionComparison {
  models: {
    first_touch: AttributionChannel[];
    last_touch: AttributionChannel[];
    linear: AttributionChannel[];
    time_decay: AttributionChannel[];
    position_based: AttributionChannel[];
    markov: AttributionChannel[];
    [key: string]: AttributionChannel[];
  };
  total_revenue?: number;
}

export interface JourneyPattern {
  path: string[];
  customers: number;
  conversions: number;
  conversion_rate: number;
  revenue: number;
  average_journey_duration_minutes: number;
  average_touchpoints: number;
}

export interface JourneyEvent {
  timestamp: string;
  session_id: string;
  channel: string;
  campaign_id: string | null;
  event_type: string;
  page: string | null;
  product_id: string | null;
}

export interface JourneySession {
  session_index: number;
  started_at: string;
  ended_at: string;
  duration_minutes: number;
  event_count: number;
  channels: string[];
}

export interface CustomerJourney {
  customer_id: string;
  first_seen: string;
  last_activity: string;
  journey_duration_minutes: number;
  event_count: number;
  session_count: number;
  touchpoint_count: number;
  unique_channel_count: number;
  channels: string[];
  converted: boolean;
  conversion_timestamp: string | null;
  conversion_revenue: number | null;
  conversion_order_id: string | null;
  sessions: JourneySession[];
  events: JourneyEvent[];
}

export interface JourneySummary {
  customer_id: string;
  converted: boolean;
  conversion_revenue: number | null;
  journey_duration_minutes: number;
  event_count: number;
  session_count: number;
  touchpoint_count: number;
  unique_channel_count: number;
  channels: string[];
}

export type AttributionModelType =
  | 'first_touch'
  | 'last_touch'
  | 'linear'
  | 'time_decay'
  | 'position_based'
  | 'markov';

// ── Stage 7: Journey Flow ────────────────────────────────────────────────────

export type ConversionFilter = 'all' | 'converted' | 'non_converted';

/** A node in the journey flow graph (channel or special state). */
export interface JourneyFlowNode {
  /** Unique node identifier. Special values: '__START__', '__CONVERSION__'. */
  id: string;
  /** Human-readable display label. */
  label: string;
  /** Node category: 'start' | 'channel' | 'conversion'. */
  type: 'start' | 'channel' | 'conversion';
}

/** A directed edge in the journey flow graph. */
export interface JourneyFlowLink {
  /** Source node ID. */
  source: string;
  /** Target node ID. */
  target: string;
  /** Number of journeys that traversed this transition. */
  value: number;
}

/** Complete journey flow graph response from the backend. */
export interface JourneyFlowResponse {
  nodes: JourneyFlowNode[];
  links: JourneyFlowLink[];
  /** Total journeys used to build the graph (after filtering and limit). */
  total_journeys: number;
  /** Number of unique aggregated (source → target) pairs. */
  total_transitions: number;
  converted_journeys: number;
  non_converted_journeys: number;
}
