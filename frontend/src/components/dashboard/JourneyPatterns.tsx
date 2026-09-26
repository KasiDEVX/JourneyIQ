import React, { useState, useEffect } from 'react';
import { ArrowRight, GitFork, ShoppingBag, DollarSign, Users, Clock } from 'lucide-react';
import { JourneyPattern } from '@/types/analytics';
import { getJourneyPatterns } from '@/services/api';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';
import { formatINR } from '@/utils/currency';

interface JourneyPatternsProps {
  initialData?: JourneyPattern[];
  limit?: number;
  showControls?: boolean;
}

export const JourneyPatterns: React.FC<JourneyPatternsProps> = ({
  initialData,
  limit = 10,
  showControls = true,
}) => {
  const [data, setData] = useState<JourneyPattern[]>(initialData || []);
  const [loading, setLoading] = useState(initialData ? false : true);
  const [error, setError] = useState<string | null>(null);

  const fetchPatterns = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getJourneyPatterns(limit);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load journey patterns');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialData) {
      fetchPatterns();
    }
  }, [initialData, limit]);

  useEffect(() => {
    const onRefresh = () => fetchPatterns();
    window.addEventListener('journeyiq:refresh', onRefresh);
    return () => window.removeEventListener('journeyiq:refresh', onRefresh);
  }, []);

  const getChannelColor = (ch: string) => {
    const lower = ch.toLowerCase();
    if (lower.includes('google search') || lower.includes('organic search')) return 'bg-blue-50 text-blue-700 border-blue-200';
    if (lower.includes('instagram')) return 'bg-pink-50 text-pink-700 border-pink-200';
    if (lower.includes('facebook')) return 'bg-indigo-50 text-indigo-700 border-indigo-200';
    if (lower.includes('email')) return 'bg-amber-50 text-amber-800 border-amber-200';
    if (lower.includes('youtube')) return 'bg-red-50 text-red-700 border-red-200';
    if (lower.includes('sms')) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    return 'bg-gray-100 text-graphite-800 border-gray-200';
  };

  return (
    <div className="card-soft p-6 md:p-8 space-y-5">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg md:text-xl font-bold font-display tracking-tight text-graphite-950">
              Top Customer Journeys
            </h2>
            <Badge variant="coral" size="sm">Path Intelligence</Badge>
          </div>
          <p className="text-xs md:text-sm text-gray-500">
            Most frequent multi-touch sequences from acquisition to checkout.
          </p>
        </div>
      </div>

      {/* List of Patterns */}
      {loading ? (
        <div className="space-y-3 pt-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-2xl" />
          ))}
        </div>
      ) : error ? (
        <div className="p-6 text-center text-xs text-red-500 bg-red-50 rounded-2xl border border-red-200">
          {error}
        </div>
      ) : data.length === 0 ? (
        <div className="p-8 text-center text-xs text-gray-400">
          No customer journeys recorded yet.
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((pattern, idx) => {
            const convPct = (pattern.conversion_rate * 100).toFixed(1);
            return (
              <div
                key={idx}
                className="p-4 rounded-2xl bg-white border border-gray-200/90 hover:border-gray-300 hover:shadow-xs transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                {/* Left: Sequence of channel pills with arrows */}
                <div className="flex-1">
                  <div className="flex items-center gap-2 text-[11px] font-mono font-bold text-gray-400 mb-2">
                    <span>Rank #{idx + 1}</span>
                    <span className="w-1 h-1 rounded-full bg-gray-300" />
                    <span>{pattern.average_touchpoints.toFixed(0)} Touchpoints</span>
                  </div>

                  {/* Flow Pills */}
                  <div className="flex items-center flex-wrap gap-1.5">
                    {pattern.path.length === 0 ? (
                      <span className="px-3 py-1 rounded-full text-xs font-mono text-gray-400 bg-gray-100 border border-gray-200">
                        Direct / No Marketing Touchpoint
                      </span>
                    ) : (
                      pattern.path.map((ch, chIdx) => (
                        <React.Fragment key={chIdx}>
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-semibold border shadow-2xs ${getChannelColor(
                              ch
                            )}`}
                          >
                            {ch}
                          </span>
                          {chIdx < pattern.path.length - 1 && (
                            <ArrowRight className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                          )}
                        </React.Fragment>
                      ))
                    )}
                  </div>
                </div>

                {/* Right: Metrics Capsule */}
                <div className="flex items-center gap-4 pt-3 md:pt-0 border-t md:border-t-0 border-gray-100 shrink-0">
                  {/* Customers */}
                  <div className="text-left md:text-right">
                    <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">
                      Volume
                    </div>
                    <div className="text-xs font-mono font-bold text-graphite-900">
                      {pattern.customers} <span className="text-gray-400 text-[10px] font-normal">cust</span>
                    </div>
                  </div>

                  {/* Conversions & Rate */}
                  <div className="text-left md:text-right">
                    <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">
                      Conv Rate
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-mono font-bold ${
                          pattern.conversions > 0
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-gray-100 text-gray-500 border border-gray-200'
                        }`}
                      >
                        {convPct}%
                      </span>
                    </div>
                  </div>

                  {/* Revenue */}
                  <div className="text-left md:text-right min-w-[80px]">
                    <div className="text-[10px] uppercase font-bold text-gray-400 font-mono">
                      Revenue
                    </div>
                    <div className="text-sm font-mono font-extrabold text-coral-600">
                      {formatINR(pattern.revenue)}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
