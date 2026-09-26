// -*- coding: utf-8 -*-
/**
 * JourneyIQ API Client Layer.
 * Centralizes all network requests, endpoints, and error handling.
 */

import {
  OverviewAnalytics,
  ChannelAnalytics,
  AttributionAnalytics,
  AttributionComparison,
  JourneyPattern,
  CustomerJourney,
  JourneySummary,
  AttributionModelType,
  JourneyFlowResponse,
  ConversionFilter,
} from '@/types/analytics';

// Uses VITE_API_BASE_URL if defined, stripping trailing slashes.
// Defaults to empty string so Vite dev proxy handles /api calls seamlessly (or http://127.0.0.1:8000).
const RAW_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').trim();
const API_BASE_URL = RAW_API_BASE_URL.replace(/\/+$/, '');

class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 15000;

async function request<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      ...options,
      signal: options?.signal || controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let errorDetail = `Request failed with status ${res.status}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string'
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Non-JSON response
      }
      throw new ApiError(errorDetail, res.status);
    }

    return await res.json();
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) {
      throw err;
    }
    if (err.name === 'AbortError') {
      throw new ApiError(
        `Request to ${endpoint} timed out after ${timeoutMs / 1000}s. Please check your connection.`,
        408
      );
    }
    // Network / offline error
    throw new ApiError(
      err.message || 'Unable to connect to JourneyIQ backend. Ensure server is running.',
      0
    );
  }
}

// ── API Functions ─────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<{ status: string; service: string }> {
  return request('/api/health');
}

export async function getOverview(): Promise<OverviewAnalytics> {
  return request<OverviewAnalytics>('/api/analytics/overview');
}

export async function getChannels(): Promise<ChannelAnalytics[]> {
  return request<ChannelAnalytics[]>('/api/analytics/channels');
}

export async function getAttribution(
  model: AttributionModelType = 'linear'
): Promise<AttributionAnalytics> {
  return request<AttributionAnalytics>(`/api/analytics/attribution?model=${encodeURIComponent(model)}`);
}

export async function getAttributionComparison(): Promise<AttributionComparison> {
  return request<AttributionComparison>('/api/analytics/attribution/compare');
}

export async function getJourneyPatterns(limit: number = 20): Promise<JourneyPattern[]> {
  return request<JourneyPattern[]>(`/api/analytics/journeys?limit=${encodeURIComponent(limit)}`);
}

export interface CustomerProfile {
  customer_id: string;
  first_seen: string;
  converted: boolean;
  conversion_revenue: number | null;
  event_count: number;
}

export async function getCustomers(
  limit: number = 50,
  search?: string,
  converted?: boolean
): Promise<CustomerProfile[]> {
  const params = new URLSearchParams();
  params.set('limit', String(limit));
  if (search) params.set('search', search);
  if (converted !== undefined) params.set('converted', String(converted));
  return request<CustomerProfile[]>(`/api/customers?${params.toString()}`);
}

export async function getCustomerJourney(customerId: string): Promise<CustomerJourney> {
  return request<CustomerJourney>(`/api/customers/${encodeURIComponent(customerId)}/journey`);
}

export async function getCustomerJourneySummary(customerId: string): Promise<JourneySummary> {
  return request<JourneySummary>(`/api/customers/${encodeURIComponent(customerId)}/journey/summary`);
}

/**
 * Fetch the customer journey flow graph from the backend.
 * @param conversion - Filter: 'all' | 'converted' | 'non_converted'
 * @param limit      - Max journeys to include in graph construction (1–5000).
 *                     Does NOT limit the number of links returned.
 */
export async function getJourneyFlow(
  conversion: ConversionFilter = 'all',
  limit: number = 1000,
): Promise<JourneyFlowResponse> {
  const params = new URLSearchParams({
    conversion,
    limit: String(limit),
  });
  return request<JourneyFlowResponse>(`/api/analytics/journey-flow?${params.toString()}`);
}
