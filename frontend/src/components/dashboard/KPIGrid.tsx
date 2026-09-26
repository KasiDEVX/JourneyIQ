import React from 'react';
import { Users, Layers, ShoppingBag, DollarSign, Clock, GitMerge, Radio, Activity } from 'lucide-react';
import { OverviewAnalytics } from '@/types/analytics';
import { KPICard } from './KPICard';
import { CardSkeleton } from '@/components/ui/Skeleton';

interface KPIGridProps {
  data: OverviewAnalytics | null;
  loading: boolean;
}

export const KPIGrid: React.FC<KPIGridProps> = ({ data, loading }) => {
  if (loading || !data) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  return (
    <div className="space-y-4">
      {/* 4 Primary Top KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5">
        <KPICard
          title="Total Customers"
          value={formatNumber(data.customers)}
          subtitle="Unique mapped profiles"
          badge={{ text: `${formatNumber(data.events)} events`, variant: 'neutral' }}
          icon={<Users className="w-4 h-4" />}
        />

        <KPICard
          title="Customer Sessions"
          value={formatNumber(data.sessions)}
          subtitle="30-min window threshold"
          badge={{ text: `${data.unique_channels} channels active`, variant: 'neutral' }}
          icon={<Layers className="w-4 h-4" />}
        />

        <KPICard
          title="Conversions"
          value={formatNumber(data.conversions)}
          subtitle={`${data.customers - data.conversions} dropped out`}
          badge={{ text: `${(data.conversion_rate * 100).toFixed(1)}% rate`, variant: 'emerald' }}
          icon={<ShoppingBag className="w-4 h-4" />}
        />

        <KPICard
          title="Conversion Revenue"
          value={formatCurrency(data.total_revenue)}
          subtitle={`AOV ${formatCurrency(data.average_order_value)}`}
          badge={{ text: 'Attributable', variant: 'coral' }}
          icon={<DollarSign className="w-4 h-4" />}
          accent={true}
        />
      </div>

      {/* Secondary Efficiency Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-white p-3.5 rounded-2xl border border-gray-200/90 shadow-2xs">
        <div className="flex items-center gap-3 px-3 py-1.5 border-r border-gray-100 last:border-0">
          <div className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center text-graphite-600">
            <Clock className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-gray-400">Avg Duration</div>
            <div className="text-xs font-bold text-graphite-900 font-mono">
              {(data.average_journey_duration_minutes / 60).toFixed(1)} hrs
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 px-3 py-1.5 border-r border-gray-100 last:border-0">
          <div className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center text-graphite-600">
            <GitMerge className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-gray-400">Avg Touches</div>
            <div className="text-xs font-bold text-graphite-900 font-mono">
              {data.average_touchpoints.toFixed(1)} per journey
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 px-3 py-1.5 border-r border-gray-100 last:border-0">
          <div className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center text-graphite-600">
            <Radio className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-gray-400">Channels</div>
            <div className="text-xs font-bold text-graphite-900 font-mono">
              {data.unique_channels} active media
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 px-3 py-1.5">
          <div className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center text-graphite-600">
            <Activity className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="text-[10px] uppercase font-bold text-gray-400">Avg Order Value</div>
            <div className="text-xs font-bold text-graphite-900 font-mono">
              {formatCurrency(data.average_order_value)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
