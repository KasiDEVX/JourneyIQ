import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Percent,
  DollarSign,
  Info,
  Layers,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import {
  AttributionAnalytics,
  AttributionComparison,
  AttributionModelType,
} from '@/types/analytics';
import { getAttribution, getAttributionComparison } from '@/services/api';
import { AttributionChart } from '@/components/charts/AttributionChart';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

const MODELS: { key: AttributionModelType; label: string; desc: string; thesis: string }[] = [
  {
    key: 'linear',
    label: 'Linear',
    desc: 'Equal credit distribution',
    thesis: 'Distributes conversion credit and revenue equally across all touchpoints on the conversion path.',
  },
  {
    key: 'markov',
    label: 'Markov Chains',
    desc: 'Removal-effect uplift',
    thesis: 'Calculates the incremental conversion probability drop when each channel state is eliminated from the journey network.',
  },
  {
    key: 'position_based',
    label: 'Position-Based (U-Shaped)',
    desc: '40% discovery / 40% decision',
    thesis: 'Prioritizes initial brand discovery (40%) and bottom-funnel closing (40%), dividing 20% across middle nurturing touches.',
  },
  {
    key: 'time_decay',
    label: 'Time Decay',
    desc: 'Exponential recency decay',
    thesis: 'Weights touchpoints using an exponential decay curve (7-day half-life), heavily rewarding interactions close to purchase.',
  },
  {
    key: 'first_touch',
    label: 'First Touch',
    desc: 'Acquisition awareness',
    thesis: 'Assigns 100% of conversion credit and revenue to the initial touchpoint that brought the customer into the funnel.',
  },
  {
    key: 'last_touch',
    label: 'Last Touch',
    desc: 'Closing conversion trigger',
    thesis: 'Assigns 100% of conversion credit to the immediate touchpoint prior to checkout completion.',
  },
];

export const Attribution: React.FC = () => {
  const [activeModel, setActiveModel] = useState<AttributionModelType>('linear');
  const [viewMode, setViewMode] = useState<'revenue' | 'credit'>('revenue');
  const [data, setData] = useState<AttributionAnalytics | null>(null);
  const [comparison, setComparison] = useState<AttributionComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [compLoading, setCompLoading] = useState(true);

  const loadData = async (model: AttributionModelType) => {
    setLoading(true);
    try {
      const res = await getAttribution(model);
      setData(res);
    } catch {
      // Handled by UI
    } finally {
      setLoading(false);
    }
  };

  const loadComparison = async () => {
    setCompLoading(true);
    try {
      const res = await getAttributionComparison();
      setComparison(res);
    } catch {
      // Handled by UI
    } finally {
      setCompLoading(false);
    }
  };

  useEffect(() => {
    loadData(activeModel);
  }, [activeModel]);

  useEffect(() => {
    loadComparison();
  }, []);

  const activeMeta = MODELS.find((m) => m.key === activeModel);

  return (
    <div className="space-y-8">
      {/* Page Title Banner */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <h1 className="text-2xl font-bold font-display tracking-tight text-graphite-950">
            Multi-Touch Attribution Engine
          </h1>
          <Badge variant="coral">Stage 4 Verified</Badge>
        </div>
        <p className="text-sm text-gray-500">
          Compare how mathematical attribution algorithms evaluate marketing ROI and channel efficiency.
        </p>
      </div>

      {/* Model Selector Card */}
      <div className="card-soft p-6 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-100 pb-5">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-graphite-900 font-display">
              Select Attribution Model
            </h2>
          </div>
          {/* Revenue vs % Toggle */}
          <div className="flex items-center gap-1.5 p-1 bg-ivory-100 rounded-full border border-gray-200 self-start md:self-auto">
            <button
              onClick={() => setViewMode('revenue')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                viewMode === 'revenue'
                  ? 'bg-white text-graphite-950 shadow-xs'
                  : 'text-gray-500 hover:text-graphite-700'
              }`}
            >
              <DollarSign className="w-3.5 h-3.5 text-coral-500" />
              <span>Attributed Revenue</span>
            </button>
            <button
              onClick={() => setViewMode('credit')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                viewMode === 'credit'
                  ? 'bg-white text-graphite-950 shadow-xs'
                  : 'text-gray-500 hover:text-graphite-700'
              }`}
            >
              <Percent className="w-3.5 h-3.5 text-emerald-600" />
              <span>Attribution Share %</span>
            </button>
          </div>
        </div>

        {/* Model Tabs Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {MODELS.map((m) => {
            const isActive = activeModel === m.key;
            return (
              <button
                key={m.key}
                onClick={() => setActiveModel(m.key)}
                className={`p-3.5 rounded-2xl border text-left transition-all ${
                  isActive
                    ? 'bg-graphite-950 text-white border-graphite-900 shadow-sm ring-2 ring-coral-500/30'
                    : 'bg-white text-graphite-800 border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="text-xs font-bold font-display">{m.label}</div>
                <div
                  className={`text-[10px] mt-0.5 ${
                    isActive ? 'text-gray-400' : 'text-gray-500'
                  }`}
                >
                  {m.desc}
                </div>
              </button>
            );
          })}
        </div>

        {/* Algorithm Explanation */}
        <div className="p-4 rounded-2xl bg-ivory-50 border border-ivory-200 flex items-start gap-3">
          <Info className="w-4 h-4 text-coral-500 shrink-0 mt-0.5" />
          <div className="text-xs text-graphite-700 leading-relaxed">
            <span className="font-bold text-graphite-900">{activeMeta?.label} Methodology:</span>{' '}
            {activeMeta?.thesis}
          </div>
        </div>

        {/* Chart View */}
        {loading || !data ? (
          <Skeleton className="h-80 w-full rounded-2xl" />
        ) : (
          <div className="p-4 bg-ivory-50/50 rounded-2xl border border-gray-100">
            <AttributionChart
              channels={data.channels}
              mode={viewMode}
              totalRevenue={data.total_revenue}
            />
          </div>
        )}
      </div>

      {/* Side-by-Side Model Comparison Table */}
      <div className="card-soft p-6 md:p-8 space-y-5">
        <div className="border-b border-gray-100 pb-4">
          <h2 className="text-lg font-bold font-display text-graphite-950">
            Cross-Model Comparison Matrix
          </h2>
          <p className="text-xs text-gray-500">
            Compare credit allocation percentages across all 6 attribution models simultaneously.
          </p>
        </div>

        {compLoading || !comparison ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto -mx-6 md:-mx-8 px-6 md:px-8">
            <table className="w-full text-left border-collapse min-w-[720px] text-xs">
              <thead>
                <tr className="border-b border-gray-200 text-[11px] font-bold uppercase tracking-wider text-gray-400 font-mono">
                  <th className="py-3 px-3">Channel</th>
                  <th className="py-3 px-3 text-right">Linear</th>
                  <th className="py-3 px-3 text-right">Markov</th>
                  <th className="py-3 px-3 text-right">Position</th>
                  <th className="py-3 px-3 text-right">Time Decay</th>
                  <th className="py-3 px-3 text-right">First Touch</th>
                  <th className="py-3 px-3 text-right">Last Touch</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 font-mono">
                {/* Extract unique channels from linear */}
                {(comparison.models.linear || []).map((ch) => {
                  const channelName = ch.channel;
                  const getCredit = (modelKey: string) => {
                    const match = (comparison.models[modelKey] || []).find(
                      (c) => c.channel === channelName
                    );
                    return match ? `${(match.credit * 100).toFixed(1)}%` : '0.0%';
                  };

                  return (
                    <tr key={channelName} className="hover:bg-ivory-50/80 transition-colors">
                      <td className="py-3 px-3 font-sans font-semibold text-graphite-900">
                        {channelName}
                      </td>
                      <td className="py-3 px-3 text-right text-gray-600">{getCredit('linear')}</td>
                      <td className="py-3 px-3 text-right font-bold text-coral-600">{getCredit('markov')}</td>
                      <td className="py-3 px-3 text-right text-gray-600">{getCredit('position_based')}</td>
                      <td className="py-3 px-3 text-right text-gray-600">{getCredit('time_decay')}</td>
                      <td className="py-3 px-3 text-right text-gray-600">{getCredit('first_touch')}</td>
                      <td className="py-3 px-3 text-right text-gray-600">{getCredit('last_touch')}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Required Factual Markov Section */}
      <div className="card-soft p-6 md:p-8 bg-graphite-950 text-white border-graphite-900 space-y-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-coral-400" />
          <h2 className="text-base font-bold font-display tracking-tight text-white">
            Algorithmic Integrity: Markov Chain Removal Effect
          </h2>
        </div>
        <p className="text-xs text-graphite-300 leading-relaxed">
          Markov attribution estimates channel contribution by measuring how conversion probability
          changes when a channel is removed from the observed journey network.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 text-xs">
          <div className="p-3.5 rounded-xl bg-graphite-900 border border-graphite-800">
            <div className="font-semibold text-ivory-100 mb-1">State Transition Graph</div>
            <p className="text-gray-400 text-[11px]">
              Every customer movement is modeled as a transition from START through channel nodes to CONVERSION or DROP.
            </p>
          </div>
          <div className="p-3.5 rounded-xl bg-graphite-900 border border-graphite-800">
            <div className="font-semibold text-ivory-100 mb-1">Removal Effect Equation</div>
            <p className="text-gray-400 text-[11px]">
              Removal Effect = Baseline Conversion Reach − Counterfactual Reach with Channel Removed.
            </p>
          </div>
          <div className="p-3.5 rounded-xl bg-graphite-900 border border-graphite-800">
            <div className="font-semibold text-ivory-100 mb-1">Revenue Conservation</div>
            <p className="text-gray-400 text-[11px]">
              Normalized shares sum to 1.0, ensuring 100% of converted revenue is conserved without double-counting.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
