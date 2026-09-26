import React, { useState, useEffect } from 'react';
import {
  ArrowUpDown,
  Search,
  Globe,
  Share2,
  Mail,
  Video,
  Send,
  MessageSquare,
  Radio,
  Layers,
  ExternalLink,
} from 'lucide-react';
import { ChannelAnalytics } from '@/types/analytics';
import { getChannels } from '@/services/api';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';

interface ChannelPerformanceProps {
  initialData?: ChannelAnalytics[];
  loading?: boolean;
}

type SortField = 'revenue' | 'customers' | 'sessions' | 'conversions' | 'conversion_rate';

export const ChannelPerformance: React.FC<ChannelPerformanceProps> = ({
  initialData,
  loading: parentLoading,
}) => {
  const [data, setData] = useState<ChannelAnalytics[]>(initialData || []);
  const [loading, setLoading] = useState(initialData ? false : true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('revenue');
  const [sortAsc, setSortAsc] = useState(false);

  const fetchChannels = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getChannels();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch channel performance');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialData) {
      fetchChannels();
    }
  }, [initialData]);

  useEffect(() => {
    const onRefresh = () => fetchChannels();
    window.addEventListener('journeyiq:refresh', onRefresh);
    return () => window.removeEventListener('journeyiq:refresh', onRefresh);
  }, []);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const sortedData = [...data].sort((a, b) => {
    const factor = sortAsc ? 1 : -1;
    return (a[sortField] - b[sortField]) * factor;
  });

  const getChannelIcon = (channel: string) => {
    const ch = channel.toLowerCase();
    if (ch.includes('google search') || ch.includes('organic search')) return <Search className="w-4 h-4 text-blue-500" />;
    if (ch.includes('instagram')) return <Share2 className="w-4 h-4 text-pink-500" />;
    if (ch.includes('facebook')) return <Share2 className="w-4 h-4 text-indigo-500" />;
    if (ch.includes('youtube')) return <Video className="w-4 h-4 text-red-500" />;
    if (ch.includes('email')) return <Mail className="w-4 h-4 text-amber-500" />;
    if (ch.includes('sms')) return <MessageSquare className="w-4 h-4 text-emerald-500" />;
    if (ch.includes('direct')) return <Globe className="w-4 h-4 text-gray-500" />;
    if (ch.includes('referral')) return <Send className="w-4 h-4 text-purple-500" />;
    return <Radio className="w-4 h-4 text-coral-500" />;
  };

  const maxRevenue = Math.max(...data.map((c) => c.revenue), 1);

  return (
    <div className="card-soft p-6 md:p-8 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg md:text-xl font-bold font-display tracking-tight text-graphite-950">
              Channel Performance
            </h2>
            <Badge variant="neutral" size="sm">{data.length} Channels</Badge>
          </div>
          <p className="text-xs md:text-sm text-gray-500">
            Holistic cross-channel metrics derived from real customer journeys.
          </p>
        </div>
      </div>

      {/* Table Content */}
      {loading || parentLoading ? (
        <div className="space-y-3 pt-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-xl" />
          ))}
        </div>
      ) : error ? (
        <div className="p-6 text-center text-xs text-red-500 bg-red-50 rounded-2xl border border-red-200">
          {error}
        </div>
      ) : (
        <div className="overflow-x-auto -mx-6 md:-mx-8 px-6 md:px-8">
          <table className="w-full text-left border-collapse min-w-[640px]">
            <thead>
              <tr className="border-b border-gray-200/80 text-[11px] font-bold uppercase tracking-wider text-gray-400 font-mono select-none">
                <th className="py-3 px-3">Channel</th>
                <th
                  className="py-3 px-3 cursor-pointer hover:text-graphite-900"
                  onClick={() => handleSort('customers')}
                >
                  <span className="flex items-center gap-1">
                    Customers <ArrowUpDown className="w-3 h-3" />
                  </span>
                </th>
                <th
                  className="py-3 px-3 cursor-pointer hover:text-graphite-900"
                  onClick={() => handleSort('sessions')}
                >
                  <span className="flex items-center gap-1">
                    Sessions <ArrowUpDown className="w-3 h-3" />
                  </span>
                </th>
                <th
                  className="py-3 px-3 cursor-pointer hover:text-graphite-900"
                  onClick={() => handleSort('conversions')}
                >
                  <span className="flex items-center gap-1">
                    Conversions <ArrowUpDown className="w-3 h-3" />
                  </span>
                </th>
                <th
                  className="py-3 px-3 cursor-pointer hover:text-graphite-900"
                  onClick={() => handleSort('conversion_rate')}
                >
                  <span className="flex items-center gap-1">
                    Conv Rate <ArrowUpDown className="w-3 h-3" />
                  </span>
                </th>
                <th
                  className="py-3 px-3 text-right cursor-pointer hover:text-graphite-900"
                  onClick={() => handleSort('revenue')}
                >
                  <span className="flex items-center justify-end gap-1">
                    Revenue <ArrowUpDown className="w-3 h-3" />
                  </span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100/90 text-xs">
              {sortedData.map((item) => {
                const convRatePct = (item.conversion_rate * 100).toFixed(1);
                const revenueShare = (item.revenue / maxRevenue) * 100;

                return (
                  <tr
                    key={item.channel}
                    className="hover:bg-ivory-50/80 transition-colors group"
                  >
                    {/* Channel name & icon */}
                    <td className="py-3.5 px-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-xl bg-white border border-gray-200 flex items-center justify-center shadow-2xs shrink-0 group-hover:scale-105 transition-transform">
                          {getChannelIcon(item.channel)}
                        </div>
                        <span className="font-semibold text-graphite-900">
                          {item.channel}
                        </span>
                      </div>
                    </td>

                    {/* Customers */}
                    <td className="py-3.5 px-3 font-mono text-graphite-700 font-medium">
                      {item.customers.toLocaleString()}
                    </td>

                    {/* Sessions */}
                    <td className="py-3.5 px-3 font-mono text-gray-500">
                      {item.sessions.toLocaleString()}
                    </td>

                    {/* Conversions */}
                    <td className="py-3.5 px-3 font-mono font-semibold text-graphite-900">
                      {item.conversions}
                    </td>

                    {/* Conversion Rate */}
                    <td className="py-3.5 px-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold font-mono ${
                          item.conversions > 0
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-gray-100 text-gray-500 border border-gray-200'
                        }`}
                      >
                        {convRatePct}%
                      </span>
                    </td>

                    {/* Revenue + visual progress */}
                    <td className="py-3.5 px-3 text-right">
                      <div className="flex flex-col items-end gap-1">
                        <span className="font-mono font-bold text-graphite-950 text-sm">
                          ${item.revenue.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </span>
                        {/* Mini bar for quick visual comparative ratio */}
                        <div className="w-24 bg-gray-100 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="bg-coral-500 h-full rounded-full"
                            style={{ width: `${Math.max(4, revenueShare)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
