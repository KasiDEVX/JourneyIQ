// src/pages/Journeys.tsx
//
// Customer Journey Paths & Pattern Intelligence.
// Provides immediate clarity with:
// 1. Executive Summary KPIs (Journeys, Conversion Rate, Top Path, Attributed Revenue)
// 2. Interactive Journey Flow Viewer (Stage 7)
// 3. High-Clarity Journey Pattern Explorer (Sortable, Scannable, Visual Progress Meters)

import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  ArrowRight,
  Sparkles,
  TrendingUp,
  IndianRupee,
  Users,
  Compass,
  Award,
  Layers,
  Clock,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { JourneyPattern } from '@/types/analytics';
import { getJourneyPatterns } from '@/services/api';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';
import { CustomerJourneyFlow } from '@/components/dashboard/CustomerJourneyFlow';
import { formatINR } from '@/utils/currency';

type SortOption = 'revenue' | 'conversion_rate' | 'customers' | 'touchpoints';

export const Journeys: React.FC = () => {
  const [patterns, setPatterns] = useState<JourneyPattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [touchpointFilter, setTouchpointFilter] = useState<'all' | '1' | '2' | '3+'>('all');
  const [sortBy, setSortBy] = useState<SortOption>('revenue');
  const [showAll, setShowAll] = useState(false);

  const fetchJourneys = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJourneyPatterns(50);
      setPatterns(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch journey patterns');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJourneys();
  }, []);

  // Compute Page-Level KPIs from pattern data for instant comprehension
  const kpis = useMemo(() => {
    if (patterns.length === 0) return null;

    const totalCustomers = patterns.reduce((sum, p) => sum + p.customers, 0);
    const totalConversions = patterns.reduce((sum, p) => sum + p.conversions, 0);
    const totalRevenue = patterns.reduce((sum, p) => sum + p.revenue, 0);
    const overallConvRate =
      totalCustomers > 0 ? ((totalConversions / totalCustomers) * 100).toFixed(1) : '0.0';

    // Best converting multi-touch path
    const multiTouchWithConv = patterns.filter(
      (p) => p.path.length > 1 && p.conversions > 0,
    );
    const bestConverting = [...multiTouchWithConv].sort(
      (a, b) => b.conversion_rate - a.conversion_rate,
    )[0];

    // Average duration across paths
    const avgDurationHours =
      patterns.reduce((sum, p) => sum + p.average_journey_duration_minutes, 0) /
      patterns.length /
      60;

    return {
      totalPatterns: patterns.length,
      totalCustomers,
      totalConversions,
      totalRevenue,
      overallConvRate,
      bestConverting,
      avgDurationHours: avgDurationHours.toFixed(1),
    };
  }, [patterns]);

  // Filter & Sort
  const filteredAndSortedPatterns = useMemo(() => {
    const filtered = patterns.filter((p) => {
      const matchesSearch =
        searchQuery === '' ||
        p.path.some((ch) => ch.toLowerCase().includes(searchQuery.toLowerCase()));

      const touchCount = p.path.length;
      let matchesTouch = true;
      if (touchpointFilter === '1') matchesTouch = touchCount === 1;
      if (touchpointFilter === '2') matchesTouch = touchCount === 2;
      if (touchpointFilter === '3+') matchesTouch = touchCount >= 3;

      return matchesSearch && matchesTouch;
    });

    return [...filtered].sort((a, b) => {
      if (sortBy === 'revenue') return b.revenue - a.revenue;
      if (sortBy === 'conversion_rate') return b.conversion_rate - a.conversion_rate;
      if (sortBy === 'customers') return b.customers - a.customers;
      if (sortBy === 'touchpoints') return b.path.length - a.path.length;
      return 0;
    });
  }, [patterns, searchQuery, touchpointFilter, sortBy]);

  const displayedPatterns = showAll
    ? filteredAndSortedPatterns
    : filteredAndSortedPatterns.slice(0, 10);

  const getChannelColor = (ch: string) => {
    const lower = ch.toLowerCase();
    if (lower.includes('google search') || lower.includes('organic search'))
      return 'bg-blue-50 text-blue-700 border-blue-200';
    if (lower.includes('instagram')) return 'bg-pink-50 text-pink-700 border-pink-200';
    if (lower.includes('facebook')) return 'bg-indigo-50 text-indigo-700 border-indigo-200';
    if (lower.includes('email')) return 'bg-amber-50 text-amber-800 border-amber-200';
    if (lower.includes('youtube')) return 'bg-red-50 text-red-700 border-red-200';
    if (lower.includes('sms')) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (lower.includes('google display')) return 'bg-sky-50 text-sky-700 border-sky-200';
    return 'bg-gray-100 text-graphite-800 border-gray-200';
  };

  return (
    <div className="space-y-7">
      {/* ── Page Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold font-display tracking-tight text-graphite-950">
              Customer Journey Intelligence
            </h1>
            <Badge variant="coral">Multi-Touch Pathways</Badge>
          </div>
          <p className="text-xs sm:text-sm text-gray-500">
            Observed sequential touchpoint trajectories, cross-channel handoffs, and conversion performance.
          </p>
        </div>
      </div>

      {/* ── Stage 7: Large Journey Network & Controls (Primary Visualization) ── */}
      <CustomerJourneyFlow />

      {/* ── Executive Summary KPI Cards ──────────────────────────────────────── */}
      {kpis && !loading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5" aria-label="Journey summary metrics">
          {/* KPI 1: Total Journeys */}
          <div className="card-soft p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between text-gray-400 mb-1">
              <span className="text-[11px] font-mono uppercase font-bold tracking-wider">
                Journeys Analyzed
              </span>
              <Users className="w-4 h-4 text-blue-500" aria-hidden="true" />
            </div>
            <div className="text-2xl font-bold font-display text-graphite-950">
              {kpis.totalCustomers.toLocaleString()}
            </div>
            <div className="text-[11px] text-gray-500 mt-1">
              across <span className="font-semibold text-graphite-700">{kpis.totalPatterns}</span> unique pathways
            </div>
          </div>

          {/* KPI 2: Overall Conversion Rate */}
          <div className="card-soft p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between text-gray-400 mb-1">
              <span className="text-[11px] font-mono uppercase font-bold tracking-wider">
                Conversion Rate
              </span>
              <Award className="w-4 h-4 text-emerald-500" aria-hidden="true" />
            </div>
            <div className="text-2xl font-bold font-display text-emerald-600">
              {kpis.overallConvRate}%
            </div>
            <div className="text-[11px] text-gray-500 mt-1">
              <span className="font-semibold text-graphite-700">{kpis.totalConversions}</span> converted customers
            </div>
          </div>

          {/* KPI 3: Total Path Revenue */}
          <div className="card-soft p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between text-gray-400 mb-1">
              <span className="text-[11px] font-mono uppercase font-bold tracking-wider">
                Total Path Revenue
              </span>
              <IndianRupee className="w-4 h-4 text-coral-500" aria-hidden="true" />
            </div>
            <div className="text-2xl font-bold font-display text-coral-600">
              {formatINR(kpis.totalRevenue)}
            </div>
            <div className="text-[11px] text-gray-500 mt-1">
              avg <span className="font-semibold text-graphite-700">{formatINR(kpis.totalRevenue / (kpis.totalConversions || 1))}</span> / conversion
            </div>
          </div>

          {/* KPI 4: Top Multi-Touch Path */}
          <div className="card-soft p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between text-gray-400 mb-1">
              <span className="text-[11px] font-mono uppercase font-bold tracking-wider">
                Top Multi-Touch Path
              </span>
              <Sparkles className="w-4 h-4 text-amber-500" aria-hidden="true" />
            </div>
            <div className="text-sm font-bold font-display text-graphite-900 truncate">
              {kpis.bestConverting ? kpis.bestConverting.path.join(' → ') : 'Direct Only'}
            </div>
            <div className="text-[11px] text-gray-500 mt-1 flex items-center justify-between">
              <span>Conv: <strong className="text-emerald-600">{((kpis.bestConverting?.conversion_rate ?? 0) * 100).toFixed(1)}%</strong></span>
              <span className="font-mono font-semibold text-graphite-700">{formatINR(kpis.bestConverting?.revenue ?? 0)}</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Journey Pattern Explorer ──────────────────────────────────────── */}
      <section aria-labelledby="patterns-heading" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2
              id="patterns-heading"
              className="text-lg font-bold font-display text-graphite-950 tracking-tight"
            >
              Top Journey Patterns
            </h2>
            <p className="text-xs text-gray-500">
              Ranked channel paths with step-by-step conversion rates and attributed revenue.
            </p>
          </div>
          <div className="text-xs text-gray-400 font-mono">
            Showing {displayedPatterns.length} of {filteredAndSortedPatterns.length} pathways
          </div>
        </div>

        {/* Filter & Sort Toolbar */}
        <div className="card-soft p-3 sm:p-4 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Search by channel */}
          <div className="relative w-full md:w-72">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              id="pattern-search"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search channel (e.g. Email, Instagram)..."
              aria-label="Filter journey patterns by channel name"
              className="w-full pl-9 pr-3 py-1.5 bg-ivory-50 rounded-xl border border-gray-200 text-xs text-graphite-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-coral-500/20 focus:border-coral-500 transition-all"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Touchpoint Filter Tabs */}
            <div
              className="flex items-center gap-1 p-0.5 bg-ivory-100 rounded-xl border border-gray-200 text-xs"
              role="group"
              aria-label="Filter by number of touchpoints"
            >
              <span className="text-[10px] font-bold text-gray-400 px-2 uppercase font-mono">
                Steps:
              </span>
              {(['all', '1', '2', '3+'] as const).map((opt) => (
                <button
                  key={opt}
                  onClick={() => setTouchpointFilter(opt)}
                  aria-pressed={touchpointFilter === opt}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                    touchpointFilter === opt
                      ? 'bg-white text-graphite-950 shadow-2xs font-bold border border-gray-200/80'
                      : 'text-gray-500 hover:text-graphite-900'
                  }`}
                >
                  {opt === 'all' ? 'All' : opt === '1' ? '1-Touch' : opt === '2' ? '2-Touch' : '3+ Touches'}
                </button>
              ))}
            </div>

            {/* Sort Selector */}
            <div className="flex items-center gap-1.5">
              <label htmlFor="pattern-sort" className="text-[11px] font-mono text-gray-400 uppercase">
                Sort:
              </label>
              <select
                id="pattern-sort"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                aria-label="Sort journey patterns"
                className="text-xs font-mono bg-ivory-50 border border-gray-200 rounded-xl px-2.5 py-1 text-graphite-800 focus:outline-none focus:ring-2 focus:ring-coral-500/20 cursor-pointer"
              >
                <option value="revenue">Highest Revenue</option>
                <option value="conversion_rate">Highest Conv. Rate</option>
                <option value="customers">Most Customers</option>
                <option value="touchpoints">Path Length</option>
              </select>
            </div>
          </div>
        </div>

        {/* Patterns List */}
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full rounded-2xl" />
            ))}
          </div>
        ) : error ? (
          <div className="card-soft p-12 text-center text-xs text-red-500 bg-red-50/50">
            {error}
          </div>
        ) : filteredAndSortedPatterns.length === 0 ? (
          <div className="card-soft p-12 text-center text-sm text-gray-400">
            No journeys match your filter criteria.
          </div>
        ) : (
          <div className="space-y-3">
            {displayedPatterns.map((pattern, idx) => {
              const convPct = (pattern.conversion_rate * 100).toFixed(1);
              const isTopRevenue = idx === 0 && sortBy === 'revenue' && pattern.revenue > 0;
              const isHighConv = pattern.conversion_rate >= 0.5 && pattern.conversions > 0;

              return (
                <div
                  key={idx}
                  className="card-soft p-4 sm:p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4 hover:border-gray-300 transition-all shadow-2xs"
                >
                  {/* Left: Sequence and Metadata */}
                  <div className="space-y-2.5 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-gray-400">
                      <span className="font-bold text-graphite-900 bg-gray-100 px-2 py-0.5 rounded-md">
                        #{idx + 1}
                      </span>
                      <span>{pattern.path.length} touchpoint{pattern.path.length !== 1 ? 's' : ''}</span>
                      <span className="w-1 h-1 rounded-full bg-gray-300" />
                      <span>Avg {(pattern.average_journey_duration_minutes / 60).toFixed(1)}h duration</span>

                      {/* Standout badges */}
                      {isTopRevenue && (
                        <span className="px-2 py-0.5 rounded-full bg-coral-50 text-coral-700 border border-coral-200 text-[10px] font-bold">
                          👑 Top Revenue
                        </span>
                      )}
                      {isHighConv && !isTopRevenue && (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold">
                          ⚡ High Converting
                        </span>
                      )}
                    </div>

                    {/* Step-by-Step Channel Pathway */}
                    <div className="flex items-center flex-wrap gap-2">
                      {pattern.path.length === 0 ? (
                        <span className="px-3 py-1 rounded-lg text-xs font-mono text-gray-500 bg-gray-100 border border-gray-200">
                          Direct Conversion
                        </span>
                      ) : (
                        pattern.path.map((ch, chIdx) => (
                          <React.Fragment key={chIdx}>
                            <span
                              className={`inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-semibold border ${getChannelColor(
                                ch,
                              )}`}
                            >
                              <span className="text-[10px] font-mono opacity-60">{chIdx + 1}.</span>
                              <span>{ch}</span>
                            </span>
                            {chIdx < pattern.path.length - 1 && (
                              <ArrowRight className="w-3.5 h-3.5 text-gray-400 shrink-0" aria-hidden="true" />
                            )}
                          </React.Fragment>
                        ))
                      )}

                      {/* Outcome icon */}
                      {pattern.conversions > 0 && (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>Converted</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Right: Metrics Cluster (Structured & Scannable) */}
                  <div className="flex items-center justify-between sm:justify-end gap-5 sm:gap-7 pt-3 lg:pt-0 border-t lg:border-t-0 border-gray-100 shrink-0 text-xs">
                    {/* Volume: X of Y converted */}
                    <div className="min-w-[70px]">
                      <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">
                        Audience
                      </div>
                      <div className="text-xs font-mono font-bold text-graphite-900 mt-0.5">
                        {pattern.conversions}{' '}
                        <span className="font-normal text-gray-400">/ {pattern.customers} users</span>
                      </div>
                    </div>

                    {/* Conversion Rate with visual bar */}
                    <div className="min-w-[100px]">
                      <div className="text-[10px] uppercase font-bold text-gray-400 font-mono flex items-center justify-between">
                        <span>Conv Rate</span>
                        <span className="font-mono font-bold text-graphite-800">{convPct}%</span>
                      </div>
                      <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden mt-1.5">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${
                            pattern.conversions > 0 ? 'bg-emerald-500' : 'bg-gray-300'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(pattern.conversions > 0 ? 6 : 0, Number(convPct)))}%` }}
                        />
                      </div>
                    </div>

                    {/* Attributed Revenue */}
                    <div className="min-w-[95px] text-right">
                      <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">
                        Revenue
                      </div>
                      <div className="text-base font-mono font-extrabold text-coral-600 mt-0.5">
                        {formatINR(pattern.revenue)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Show More / Show Less Toggle Button */}
            {filteredAndSortedPatterns.length > 10 && (
              <div className="text-center pt-2">
                <button
                  onClick={() => setShowAll((prev) => !prev)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium text-graphite-700 bg-white border border-gray-200 hover:bg-gray-50 shadow-2xs transition-colors"
                >
                  {showAll ? (
                    <>
                      <span>Show top 10 patterns only</span>
                      <ChevronUp className="w-3.5 h-3.5 text-gray-500" />
                    </>
                  ) : (
                    <>
                      <span>Show all {filteredAndSortedPatterns.length} patterns</span>
                      <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
};
