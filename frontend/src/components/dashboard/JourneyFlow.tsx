import React from 'react';
import { ArrowRight, CheckCircle2, TrendingUp, Sparkles } from 'lucide-react';

export const JourneyFlow: React.FC = () => {
  // Funnel progression derived from dataset event counts & conversions
  const stages = [
    { name: 'Discovery', events: '1,305 events', type: 'Impressions & Clicks', pct: '100%', drop: null },
    { name: 'Engagement', events: '725 events', type: 'Product Views', pct: '55.5%', drop: '-44.5%' },
    { name: 'Consideration', events: '246 events', type: 'Add to Cart', pct: '18.8%', drop: '-36.7%' },
    { name: 'Decision', events: '90 events', type: 'Checkout Started', pct: '6.9%', drop: '-11.9%' },
    { name: 'Conversion', events: '28 orders', type: 'Purchases ($2.39k)', pct: '2.1%', drop: '-4.8%', isFinal: true },
  ];

  return (
    <div className="card-soft p-6 md:p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg md:text-xl font-bold font-display tracking-tight text-graphite-950">
              Customer Progression Flow
            </h2>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <TrendingUp className="w-3 h-3 text-emerald-600" />
              Full Funnel
            </span>
          </div>
          <p className="text-xs md:text-sm text-gray-500">
            Journey state progression from initial touchpoint to verified purchase.
          </p>
        </div>
      </div>

      {/* Funnel Stage Ribbons */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {stages.map((stage, idx) => {
          const isSuccess = stage.isFinal;
          return (
            <div
              key={idx}
              className={`p-4 rounded-2xl border transition-all relative ${
                isSuccess
                  ? 'bg-linear-to-b from-coral-50/40 to-white border-coral-200 shadow-2xs'
                  : 'bg-white border-gray-200/90'
              }`}
            >
              {/* Header */}
              <div className="flex items-center justify-between text-[11px] font-mono font-bold text-gray-400 mb-1">
                <span>Stage 0{idx + 1}</span>
                {stage.drop && (
                  <span className="text-gray-400 font-normal text-[10px]">
                    {stage.drop}
                  </span>
                )}
              </div>

              {/* Title & Stage info */}
              <div className="text-sm font-bold text-graphite-900 mb-1">
                {stage.name}
              </div>
              <div className="text-xs text-gray-500 mb-3">
                {stage.type}
              </div>

              {/* Volume & Percentage indicator */}
              <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-xs">
                <span className="font-mono text-gray-600">{stage.events}</span>
                <span
                  className={`font-mono font-bold ${
                    isSuccess ? 'text-coral-600' : 'text-graphite-900'
                  }`}
                >
                  {stage.pct}
                </span>
              </div>

              {/* Progress visual bar */}
              <div className="w-full bg-gray-100 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    isSuccess ? 'bg-coral-500' : 'bg-graphite-800'
                  }`}
                  style={{ width: stage.pct }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
