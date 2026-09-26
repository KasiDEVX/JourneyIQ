import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';
import { AttributionChannel } from '@/types/analytics';

interface AttributionChartProps {
  channels: AttributionChannel[];
  mode: 'revenue' | 'credit';
  totalRevenue: number;
}

export const AttributionChart: React.FC<AttributionChartProps> = ({
  channels,
  mode,
  totalRevenue,
}) => {
  if (!channels || channels.length === 0) {
    return (
      <div className="h-72 flex items-center justify-center text-sm text-gray-400">
        No channel attribution data available.
      </div>
    );
  }

  // Format data for chart
  const data = channels.map((c) => ({
    name: c.channel,
    value: mode === 'revenue' ? c.attributed_revenue : Number((c.credit * 100).toFixed(1)),
    revenue: c.attributed_revenue,
    credit: (c.credit * 100).toFixed(1),
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <div className="bg-graphite-950 text-white px-3.5 py-2.5 rounded-xl shadow-xl border border-graphite-800 text-xs space-y-1">
          <p className="font-semibold text-ivory-100">{item.name}</p>
          <div className="flex items-center justify-between gap-4 text-gray-300">
            <span>Attributed Rev:</span>
            <span className="font-mono font-bold text-coral-400">
              ${item.revenue.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="flex items-center justify-between gap-4 text-gray-400">
            <span>Credit Share:</span>
            <span className="font-mono text-emerald-400">{item.credit}%</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-80 pt-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
        >
          <XAxis
            type="number"
            tickFormatter={(val) => (mode === 'revenue' ? `$${val}` : `${val}%`)}
            stroke="#94A3B8"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#E2E8F0' }}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="#475569"
            fontSize={12}
            fontWeight={500}
            tickLine={false}
            axisLine={{ stroke: '#E2E8F0' }}
            width={95}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.02)' }} />
          <Bar
            dataKey="value"
            radius={[0, 8, 8, 0]}
            barSize={18}
          >
            {data.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={index === 0 ? '#FF5722' : index === 1 ? '#FF7D5D' : '#334155'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
