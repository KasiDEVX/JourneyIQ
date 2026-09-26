// src/components/dashboard/CustomerJourneyFlow.tsx
//
// Stage 7 — Interactive Customer Journey Flow Viewer.
// Displays the multi-touch channel network with:
// 1. Executive Key Takeaways Bar (instant at-a-glance insight)
// 2. Stage-based Interactive Flow Map (SVG)
// 3. Tabular Data Breakdown View (precise acquisition, handoff, and conversion figures)
// 4. Compact preview mode for Dashboard linking to /journeys

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  RefreshCw,
  AlertCircle,
  Activity,
  TrendingUp,
  Repeat,
  Trophy,
  ArrowRight,
  Filter,
} from 'lucide-react';
import { JourneyFlowResponse, ConversionFilter } from '@/types/analytics';
import { getJourneyFlow } from '@/services/api';
import { JourneyFlowGraph } from '@/components/journey-flow/JourneyFlowGraph';
import { JourneyFlowControls } from '@/components/journey-flow/JourneyFlowControls';
import { JourneyFlowBreakdown } from '@/components/journey-flow/JourneyFlowBreakdown';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

const GRAPH_WIDTH = 960;

interface Props {
  compact?: boolean;
}

export const CustomerJourneyFlow: React.FC<Props> = ({ compact = false }) => {
  const [data, setData] = useState<JourneyFlowResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [conversion, setConversion] = useState<ConversionFilter>('all');
  const [limit, setLimit] = useState<number>(compact ? 500 : 1000);
  const [viewMode, setViewMode] = useState<'graph' | 'breakdown'>('graph');

  const fetchFlow = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getJourneyFlow(conversion, limit);
      setData(result);
    } catch (err: any) {
      setError(err.message || 'Failed to load journey flow data.');
    } finally {
      setLoading(false);
    }
  }, [conversion, limit]);

  useEffect(() => {
    fetchFlow();
  }, [fetchFlow]);

  // Derived executive takeaways for instant understanding
  const insights = useMemo(() => {
    if (!data || data.links.length === 0) return null;

    // Top entry channel
    const entryLinks = data.links
      .filter((l) => l.source === '__START__')
      .sort((a, b) => b.value - a.value);
    const topEntry = entryLinks[0];
    const topEntryShare =
      topEntry && data.total_journeys > 0
        ? ((topEntry.value / data.total_journeys) * 100).toFixed(0)
        : null;

    // Top cross-channel bridge
    const bridgeLinks = data.links
      .filter((l) => l.source !== '__START__' && l.target !== '__CONVERSION__')
      .sort((a, b) => b.value - a.value);
    const topBridge = bridgeLinks[0];

    // Top conversion closer
    const convLinks = data.links
      .filter((l) => l.target === '__CONVERSION__')
      .sort((a, b) => b.value - a.value);
    const topCloser = convLinks[0];
    const topCloserShare =
      topCloser && data.converted_journeys > 0
        ? ((topCloser.value / data.converted_journeys) * 100).toFixed(0)
        : null;

    const convRate =
      data.total_journeys > 0
        ? ((data.converted_journeys / data.total_journeys) * 100).toFixed(1)
        : '0.0';

    return {
      topEntry,
      topEntryShare,
      topBridge,
      topCloser,
      topCloserShare,
      convRate,
    };
  }, [data]);

  return (
    <section className="card-soft p-5 md:p-7 space-y-5" aria-labelledby="journey-flow-heading">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2
              id="journey-flow-heading"
              className="text-lg md:text-xl font-bold font-display tracking-tight text-graphite-950"
            >
              {compact ? 'Customer Progression Network' : 'Interactive Journey Flow'}
            </h2>
            <Badge variant="coral">{compact ? 'Flow Preview' : 'Visual Progression'}</Badge>
          </div>
          <p className="text-xs md:text-sm text-gray-500">
            {compact
              ? 'Multi-touch channel paths reconstructed across customer trajectories.'
              : 'How prospects transition between discovery channels, intermediate touchpoints, and conversion.'}
          </p>
        </div>

        {compact ? (
          <div className="flex items-center gap-3">
            {data && !loading && (
              <span className="hidden sm:inline-block text-xs font-mono text-gray-500">
                <strong className="text-graphite-950">{data.total_journeys}</strong> journeys ·{' '}
                <strong className="text-emerald-700">{data.converted_journeys}</strong> conversions
              </span>
            )}
            <Link
              to="/journeys"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-graphite-950 hover:bg-graphite-800 text-white text-xs font-semibold shadow-xs transition-all shrink-0"
              aria-label="View full interactive journey network on Journeys page"
            >
              <span>Explore Full Network</span>
              <ArrowRight className="w-3.5 h-3.5 text-coral-400" />
            </Link>
          </div>
        ) : (
          /* Live metric summary pill */
          data && !loading && (
            <div className="flex items-center gap-3 text-xs font-mono self-start sm:self-auto">
              <div className="px-3 py-1.5 rounded-xl bg-ivory-100/90 border border-gray-200 text-graphite-700">
                <span className="font-bold text-graphite-950">{data.nodes.length}</span> Channels
              </div>
              <div className="px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 font-bold">
                {data.converted_journeys} Converted ({insights?.convRate}%)
              </div>
            </div>
          )
        )}
      </div>

      {/* Filter and Mode Controls */}
      {compact ? (
        <div className="flex flex-wrap items-center justify-between gap-3 p-1.5 bg-ivory-100/70 border border-gray-200/80 rounded-2xl">
          <div className="flex items-center gap-2 px-1">
            <Filter className="w-3.5 h-3.5 text-gray-400 shrink-0 ml-1" aria-hidden="true" />
            <span className="text-[11px] font-bold text-gray-500 uppercase font-mono tracking-wider">
              Filter:
            </span>
            <div className="flex items-center gap-1 p-0.5 bg-white/70 rounded-xl border border-gray-200/70 text-xs">
              {(['all', 'converted', 'non_converted'] as const).map((opt) => (
                <button
                  key={opt}
                  onClick={() => setConversion(opt)}
                  disabled={loading}
                  aria-pressed={conversion === opt}
                  className={`px-3 py-1 rounded-lg font-medium text-[11px] transition-all ${
                    conversion === opt
                      ? 'bg-graphite-950 text-white shadow-xs font-semibold'
                      : 'text-gray-600 hover:text-graphite-950'
                  }`}
                >
                  {opt === 'all' ? 'All' : opt === 'converted' ? 'Converted' : 'Non-Converted'}
                </button>
              ))}
            </div>
          </div>
          <Link
            to="/journeys"
            className="text-xs font-medium text-coral-600 hover:text-coral-700 px-2 py-1 flex items-center gap-1"
          >
            <span>Advanced Controls</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      ) : (
        <JourneyFlowControls
          conversion={conversion}
          limit={limit}
          viewMode={viewMode}
          onConversionChange={setConversion}
          onLimitChange={setLimit}
          onViewModeChange={setViewMode}
          totalJourneys={data?.total_journeys ?? 0}
          convertedJourneys={data?.converted_journeys ?? 0}
          nonConvertedJourneys={data?.non_converted_journeys ?? 0}
          loading={loading}
        />
      )}

      {/* Executive Key Takeaways Strip (Full mode only) */}
      {!compact && !loading && insights && (
        <div
          className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-gradient-to-r from-coral-50/50 via-ivory-50 to-emerald-50/50 rounded-2xl border border-gray-200/80 text-xs"
          role="region"
          aria-label="Key flow insights"
        >
          {/* Takeaway 1: Top Entry */}
          <div className="flex items-center gap-2.5 p-2 rounded-xl bg-white/70 border border-gray-100 shadow-2xs">
            <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <TrendingUp className="w-4 h-4" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">
                Primary Entry Point
              </div>
              <div className="font-bold text-graphite-900 truncate">
                {insights.topEntry?.target || 'None'}
                {insights.topEntryShare && (
                  <span className="ml-1 text-[11px] font-normal text-blue-600 font-mono">
                    ({insights.topEntryShare}% starts)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Takeaway 2: Top Handoff */}
          <div className="flex items-center gap-2.5 p-2 rounded-xl bg-white/70 border border-gray-100 shadow-2xs">
            <div className="w-7 h-7 rounded-lg bg-coral-50 text-coral-600 flex items-center justify-center shrink-0">
              <Repeat className="w-4 h-4" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">
                Strongest Multi-Touch Loop
              </div>
              <div className="font-bold text-graphite-900 truncate">
                {insights.topBridge ? (
                  <span>
                    {insights.topBridge.source} → {insights.topBridge.target}
                  </span>
                ) : (
                  'Direct Single-Touch'
                )}
              </div>
            </div>
          </div>

          {/* Takeaway 3: Top Closer */}
          <div className="flex items-center gap-2.5 p-2 rounded-xl bg-white/70 border border-gray-100 shadow-2xs">
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
              <Trophy className="w-4 h-4" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">
                Top Conversion Closer
              </div>
              <div className="font-bold text-graphite-900 truncate">
                {insights.topCloser?.source || 'In Progress'}
                {insights.topCloserShare && (
                  <span className="ml-1 text-[11px] font-normal text-emerald-600 font-mono">
                    ({insights.topCloserShare}% of conv.)
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Flow Content */}
      {loading ? (
        <div className="space-y-3" aria-busy="true" aria-label="Loading journey flow">
          <Skeleton className="h-10 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-2xl" />
        </div>
      ) : error ? (
        <div
          className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-5 bg-amber-50/60 border border-amber-200/80 rounded-2xl"
          role="alert"
        >
          <div className="flex items-center gap-2.5 text-xs text-amber-900">
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchFlow}
            icon={<RefreshCw className="w-3 h-3" aria-hidden="true" />}
          >
            Retry
          </Button>
        </div>
      ) : !data || data.nodes.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
          <Activity className="w-8 h-8 text-gray-300" aria-hidden="true" />
          <p className="text-sm text-gray-400 font-mono">No journeys match the selected filter criteria.</p>
        </div>
      ) : viewMode === 'graph' ? (
        <div className="space-y-3">
          <div
            className="rounded-2xl bg-[#FAF9F5] border border-gray-200/80 p-2 sm:p-4 shadow-xs"
            role="region"
            aria-label="Interactive customer journey progression network map"
          >
            <JourneyFlowGraph data={data} width={GRAPH_WIDTH} compact={compact} />
          </div>

          {/* Legend */}
          {!compact && (
            <div className="flex flex-wrap items-center justify-between gap-4 text-[11px] text-gray-500 font-mono px-1">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm bg-graphite-950 border border-gray-700" />
                  <span>Entry Node</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm bg-white border border-gray-300" />
                  <span>Marketing Channel</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm bg-emerald-100 border border-emerald-500" />
                  <span>Conversion Goal</span>
                </span>
              </div>
              <span className="text-[10px] text-gray-400">
                Ribbon thickness indicates journey volume · Hover channels or ribbons to inspect paths
              </span>
            </div>
          )}
        </div>
      ) : (
        <JourneyFlowBreakdown data={data} />
      )}
    </section>
  );
};
