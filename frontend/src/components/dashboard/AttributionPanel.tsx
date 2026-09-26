import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  BarChart2,
  Percent,
  IndianRupee,
  Info,
  CheckCircle2,
} from 'lucide-react';
import {
  AttributionAnalytics,
  AttributionModelType,
} from '@/types/analytics';
import { getAttribution } from '@/services/api';
import { AttributionChart } from '@/components/charts/AttributionChart';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';
import { formatINR } from '@/utils/currency';

const MODELS: { key: AttributionModelType; label: string; desc: string }[] = [
  { key: 'linear', label: 'Linear', desc: 'Equal credit across all path touchpoints' },
  { key: 'markov', label: 'Markov', desc: 'Algorithmic incremental removal effect' },
  { key: 'position_based', label: 'Position-Based', desc: '40% first, 40% last, 20% middle nurturing' },
  { key: 'time_decay', label: 'Time Decay', desc: 'Exponential half-life recency weighting' },
  { key: 'first_touch', label: 'First Touch', desc: '100% credit to discovery channel' },
  { key: 'last_touch', label: 'Last Touch', desc: '100% credit to conversion closer' },
];

export const AttributionPanel: React.FC = () => {
  const [activeModel, setActiveModel] = useState<AttributionModelType>('linear');
  const [viewMode, setViewMode] = useState<'revenue' | 'credit'>('revenue');
  const [data, setData] = useState<AttributionAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAttributionData = async (model: AttributionModelType) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAttribution(model);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load attribution results');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAttributionData(activeModel);
  }, [activeModel]);

  // Listen to global refresh event
  useEffect(() => {
    const onRefresh = () => fetchAttributionData(activeModel);
    window.addEventListener('journeyiq:refresh', onRefresh);
    return () => window.removeEventListener('journeyiq:refresh', onRefresh);
  }, [activeModel]);

  const activeModelMeta = MODELS.find((m) => m.key === activeModel);

  return (
    <div className="card-soft p-6 md:p-8 space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-gray-100 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-lg md:text-xl font-bold font-display tracking-tight text-graphite-950">
              Attribution Intelligence
            </h2>
            <Badge variant="coral" size="sm">Multi-Touch</Badge>
          </div>
          <p className="text-xs md:text-sm text-gray-500">
            How different attribution models distribute conversion value across channels.
          </p>
        </div>

        {/* View mode toggle (Revenue vs Credit %) */}
        <div className="flex items-center gap-1.5 p-1 bg-ivory-100 rounded-full border border-gray-200 self-start lg:self-auto">
          <button
            onClick={() => setViewMode('revenue')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
              viewMode === 'revenue'
                ? 'bg-white text-graphite-950 shadow-xs'
                : 'text-gray-500 hover:text-graphite-700'
            }`}
          >
            <IndianRupee className="w-3.5 h-3.5 text-coral-500" />
            <span>Attributed Rev</span>
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
            <span>Credit Share %</span>
          </button>
        </div>
      </div>

      {/* Model Selector Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
        {MODELS.map((model) => {
          const isActive = activeModel === model.key;
          return (
            <button
              key={model.key}
              onClick={() => setActiveModel(model.key)}
              className={`px-4 py-2 rounded-full text-xs font-medium shrink-0 transition-all duration-150 flex items-center gap-1.5 ${
                isActive
                  ? 'bg-graphite-950 text-white font-semibold shadow-xs'
                  : 'bg-white text-gray-600 hover:bg-gray-100 hover:text-graphite-900 border border-gray-200'
              }`}
            >
              <span>{model.label}</span>
              {isActive && <CheckCircle2 className="w-3 h-3 text-coral-400" />}
            </button>
          );
        })}
      </div>

      {/* Active Model Description Banner */}
      <div className="p-3 bg-ivory-50 rounded-2xl border border-ivory-200 flex items-center justify-between text-xs text-graphite-700">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-coral-500 shrink-0" />
          <span className="font-semibold text-graphite-900">{activeModelMeta?.label}:</span>
          <span className="text-gray-500 hidden sm:inline">{activeModelMeta?.desc}</span>
        </div>
        <div className="font-mono text-gray-500 font-medium">
          Total Attributed:{' '}
          <span className="font-bold text-graphite-900">
            {data ? formatINR(data.total_revenue) : '₹0.00'}
          </span>
        </div>
      </div>

      {/* Chart & Channel Breakdown */}
      {loading ? (
        <div className="space-y-4 pt-4">
          <Skeleton className="h-64 w-full rounded-2xl" />
        </div>
      ) : error ? (
        <div className="p-8 text-center bg-red-50/50 rounded-2xl border border-red-200 text-xs text-red-600">
          {error}
        </div>
      ) : data ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          {/* Main Horizontal Chart */}
          <div className="lg:col-span-8 bg-ivory-50/50 p-4 rounded-2xl border border-gray-100">
            <AttributionChart
              channels={data.channels}
              mode={viewMode}
              totalRevenue={data.total_revenue}
            />
          </div>

          {/* Side Ranking List */}
          <div className="lg:col-span-4 space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-gray-400 pb-1 border-b border-gray-100">
              Channel Contribution
            </div>
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {data.channels.map((ch, idx) => {
                const percentage = (ch.credit * 100).toFixed(1);
                return (
                  <div
                    key={ch.channel}
                    className="p-2.5 rounded-xl bg-white border border-gray-100 hover:border-gray-200 transition-colors flex items-center justify-between text-xs"
                  >
                    <div className="min-w-0 flex-1 mr-3">
                      <div className="flex items-center gap-1.5">
                        <span className="w-4 h-4 rounded-full bg-gray-100 text-[10px] font-bold text-gray-500 flex items-center justify-center font-mono">
                          {idx + 1}
                        </span>
                        <span className="font-medium text-graphite-900 truncate">
                          {ch.channel}
                        </span>
                      </div>
                      {/* Mini visual bar */}
                      <div className="w-full bg-gray-100 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-coral-500 h-full rounded-full transition-all duration-300"
                          style={{ width: `${Math.min(100, Math.max(5, ch.credit * 100))}%` }}
                        />
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="font-mono font-bold text-graphite-900">
                        {formatINR(ch.attributed_revenue)}
                      </div>
                      <div className="text-[11px] font-mono text-emerald-600 font-semibold">
                        {percentage}%
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
