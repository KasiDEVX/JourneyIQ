import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';
import { Layers, IndianRupee, TrendingUp, Users } from 'lucide-react';
import { formatINR } from '@/utils/currency';
import { ChannelAnalytics } from '@/types/analytics';
import { getChannels } from '@/services/api';
import { ChannelPerformance } from '@/components/dashboard/ChannelPerformance';
import { Skeleton } from '@/components/ui/Skeleton';
import { Badge } from '@/components/ui/Badge';

export const Channels: React.FC = () => {
  const [data, setData] = useState<ChannelAnalytics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getChannels();
        setData(res);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch channels');
      } finally {
        setLoading(false);
      }
    };
    load();

    const onRefresh = () => load();
    window.addEventListener('journeyiq:refresh', onRefresh);
    return () => window.removeEventListener('journeyiq:refresh', onRefresh);
  }, []);

  const revenueChartData = data.slice(0, 8).map((c) => ({
    name: c.channel,
    revenue: c.revenue,
    conversions: c.conversions,
  }));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <h1 className="text-2xl font-bold font-display tracking-tight text-graphite-950">
            Channel Efficiency & Conversion Analytics
          </h1>
          <Badge variant="coral">Cross-Channel Analysis</Badge>
        </div>
        <p className="text-sm text-gray-500">
          Analyze customer acquisition volume, session frequency, and commercial conversion yield per touchpoint medium.
        </p>
      </div>

      {/* Visual Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue by Channel */}
        <div className="card-soft p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-graphite-900 font-display">
                Conversion Revenue by Channel
              </h2>
              <p className="text-xs text-gray-400">Total gross value from channel interactions</p>
            </div>
            <div className="w-7 h-7 rounded-lg bg-coral-50 text-coral-500 flex items-center justify-center">
              <IndianRupee className="w-4 h-4" />
            </div>
          </div>

          {loading ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={revenueChartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                  <XAxis
                    dataKey="name"
                    stroke="#94A3B8"
                    fontSize={10}
                    tickLine={false}
                    interval={0}
                    angle={-20}
                    textAnchor="end"
                  />
                  <YAxis
                    stroke="#94A3B8"
                    fontSize={11}
                    tickLine={false}
                    tickFormatter={(v) => `₹${v}`}
                  />
                  <Tooltip
                    formatter={(value: any) => [formatINR(Number(value)), 'Revenue']}
                    contentStyle={{
                      backgroundColor: '#0F172A',
                      borderColor: '#1E293B',
                      borderRadius: '12px',
                      color: '#FFF',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="revenue" fill="#FF5722" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Conversions by Channel */}
        <div className="card-soft p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-graphite-900 font-display">
                Converted Customers by Channel
              </h2>
              <p className="text-xs text-gray-400">Number of converting paths touched</p>
            </div>
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>

          {loading ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={revenueChartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                  <XAxis
                    dataKey="name"
                    stroke="#94A3B8"
                    fontSize={10}
                    tickLine={false}
                    interval={0}
                    angle={-20}
                    textAnchor="end"
                  />
                  <YAxis
                    stroke="#94A3B8"
                    fontSize={11}
                    tickLine={false}
                  />
                  <Tooltip
                    formatter={(value: any) => [`${value} converted customers`, 'Conversions']}
                    contentStyle={{
                      backgroundColor: '#0F172A',
                      borderColor: '#1E293B',
                      borderRadius: '12px',
                      color: '#FFF',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="conversions" fill="#0EA5E9" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* Main Channel Performance Table */}
      <ChannelPerformance initialData={data} loading={loading} />
    </div>
  );
};
