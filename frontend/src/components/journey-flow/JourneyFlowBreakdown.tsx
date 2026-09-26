// src/components/journey-flow/JourneyFlowBreakdown.tsx
//
// Structured, highly scannable data breakdown for the Customer Journey Flow.
// Provides instant precision on:
// 1. Top Entry Channels (Acquisition)
// 2. Strongest Cross-Channel Handoffs (Transitions)
// 3. Top Closing Channels (Conversions)

import React from 'react';
import { ArrowRight, LogIn, Repeat, Trophy } from 'lucide-react';
import { JourneyFlowResponse } from '@/types/analytics';

interface Props {
  data: JourneyFlowResponse;
}

export const JourneyFlowBreakdown: React.FC<Props> = ({ data }) => {
  // 1. Entry Channels: links from __START__
  const entryLinks = data.links
    .filter((l) => l.source === '__START__')
    .sort((a, b) => b.value - a.value);

  // 2. Conversion Channels: links to __CONVERSION__
  const conversionLinks = data.links
    .filter((l) => l.target === '__CONVERSION__')
    .sort((a, b) => b.value - a.value);

  // 3. Inter-channel transitions: between two regular channels
  const bridgeLinks = data.links
    .filter((l) => l.source !== '__START__' && l.target !== '__CONVERSION__')
    .sort((a, b) => b.value - a.value)
    .slice(0, 8); // top 8 handoffs

  const totalEntries = entryLinks.reduce((acc, l) => acc + l.value, 0) || data.total_journeys || 1;
  const totalConversions = conversionLinks.reduce((acc, l) => acc + l.value, 0) || data.converted_journeys || 1;
  const totalBridges = bridgeLinks.reduce((acc, l) => acc + l.value, 0) || 1;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" aria-label="Journey flow metrics breakdown">
      {/* 1. Discovery / Acquisition */}
      <div className="bg-ivory-50/70 border border-gray-200/80 rounded-2xl p-4 flex flex-col">
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-200/70">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
              <LogIn className="w-3.5 h-3.5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-xs font-bold font-display text-graphite-900">1. Top Entry Channels</h3>
              <p className="text-[10px] text-gray-500">Where customer journeys begin</p>
            </div>
          </div>
          <span className="text-[11px] font-mono font-bold text-graphite-600">
            {entryLinks.length} channels
          </span>
        </div>

        <div className="space-y-2 flex-1">
          {entryLinks.slice(0, 6).map((link, idx) => {
            const share = ((link.value / totalEntries) * 100).toFixed(1);
            return (
              <div
                key={link.target}
                className="bg-white p-2.5 rounded-xl border border-gray-100 shadow-2xs hover:border-blue-200 transition-colors"
              >
                <div className="flex items-center justify-between text-xs mb-1">
                  <div className="flex items-center gap-1.5 font-medium text-graphite-900 truncate">
                    <span className="text-[10px] font-mono text-gray-400 font-bold">#{idx + 1}</span>
                    <span className="truncate">{link.target}</span>
                  </div>
                  <span className="font-mono font-bold text-graphite-800 shrink-0">
                    {link.value.toLocaleString()} <span className="text-[10px] font-normal text-gray-400">({share}%)</span>
                  </span>
                </div>
                {/* Visual share bar */}
                <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(100, Math.max(4, Number(share)))}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Top Cross-Channel Bridges */}
      <div className="bg-ivory-50/70 border border-gray-200/80 rounded-2xl p-4 flex flex-col">
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-200/70">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-coral-100 text-coral-700 flex items-center justify-center shrink-0">
              <Repeat className="w-3.5 h-3.5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-xs font-bold font-display text-graphite-900">2. Top Channel Handoffs</h3>
              <p className="text-[10px] text-gray-500">Most frequent cross-channel movements</p>
            </div>
          </div>
          <span className="text-[11px] font-mono font-bold text-graphite-600">
            {bridgeLinks.length} active
          </span>
        </div>

        <div className="space-y-2 flex-1">
          {bridgeLinks.length === 0 ? (
            <div className="text-center py-8 text-xs text-gray-400">No multi-touch transitions found.</div>
          ) : (
            bridgeLinks.map((link, idx) => {
              const maxVal = bridgeLinks[0]?.value || 1;
              const barPct = Math.round((link.value / maxVal) * 100);
              return (
                <div
                  key={`${link.source}-${link.target}`}
                  className="bg-white p-2.5 rounded-xl border border-gray-100 shadow-2xs hover:border-coral-200 transition-colors"
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <div className="flex items-center gap-1.5 text-graphite-900 font-medium truncate max-w-[190px]">
                      <span className="text-[10px] font-mono text-gray-400 font-bold">#{idx + 1}</span>
                      <span className="truncate text-gray-700">{link.source}</span>
                      <ArrowRight className="w-3 h-3 text-coral-500 shrink-0" aria-hidden="true" />
                      <span className="truncate text-graphite-950 font-semibold">{link.target}</span>
                    </div>
                    <span className="font-mono font-bold text-coral-600 shrink-0">
                      {link.value.toLocaleString()} <span className="text-[10px] font-normal text-gray-400">visits</span>
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-coral-500 rounded-full transition-all duration-300"
                      style={{ width: `${Math.max(6, barPct)}%` }}
                    />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 3. Conversion Closers */}
      <div className="bg-ivory-50/70 border border-gray-200/80 rounded-2xl p-4 flex flex-col">
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-200/70">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
              <Trophy className="w-3.5 h-3.5" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-xs font-bold font-display text-graphite-900">3. Final Touch Closers</h3>
              <p className="text-[10px] text-gray-500">Channels directly preceding conversion</p>
            </div>
          </div>
          <span className="text-[11px] font-mono font-bold text-emerald-700">
            {data.converted_journeys} conv.
          </span>
        </div>

        <div className="space-y-2 flex-1">
          {conversionLinks.length === 0 ? (
            <div className="text-center py-8 text-xs text-gray-400">
              No conversion events in current filter.
            </div>
          ) : (
            conversionLinks.map((link, idx) => {
              const convShare = ((link.value / totalConversions) * 100).toFixed(1);
              return (
                <div
                  key={link.source}
                  className="bg-white p-2.5 rounded-xl border border-gray-100 shadow-2xs hover:border-emerald-200 transition-colors"
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <div className="flex items-center gap-1.5 font-medium text-graphite-900 truncate">
                      <span className="text-[10px] font-mono text-gray-400 font-bold">#{idx + 1}</span>
                      <span className="truncate">{link.source}</span>
                    </div>
                    <span className="font-mono font-bold text-emerald-700 shrink-0">
                      {link.value.toLocaleString()} <span className="text-[10px] font-normal text-gray-400">({convShare}%)</span>
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, Math.max(5, Number(convShare)))}%` }}
                    />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
