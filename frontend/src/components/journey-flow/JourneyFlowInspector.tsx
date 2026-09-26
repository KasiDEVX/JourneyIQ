// src/components/journey-flow/JourneyFlowInspector.tsx
//
// Interactive Details Inspector for selected nodes and links in the Journey Flow Canvas.
// Displays exact in-depth traffic breakdown, inbound sources, outbound destinations,
// and conversion efficacy.

import React from 'react';
import {
  X,
  ArrowRight,
  LogIn,
  Trophy,
  Repeat,
  Compass,
  TrendingUp,
  Percent,
} from 'lucide-react';
import { JourneyFlowNode, JourneyFlowResponse } from '@/types/analytics';

interface Props {
  selectedNodeId: string | null;
  selectedLink: { source: string; target: string; value: number } | null;
  data: JourneyFlowResponse;
  onClose: () => void;
}

export const JourneyFlowInspector: React.FC<Props> = ({
  selectedNodeId,
  selectedLink,
  data,
  onClose,
}) => {
  if (!selectedNodeId && !selectedLink) return null;

  // Case 1: A specific link/transition is selected
  if (selectedLink) {
    const srcNode = data.nodes.find((n) => n.id === selectedLink.source);
    const tgtNode = data.nodes.find((n) => n.id === selectedLink.target);
    const srcLabel = srcNode?.label ?? selectedLink.source;
    const tgtLabel = tgtNode?.label ?? selectedLink.target;

    const shareOfTotal = (
      (selectedLink.value / (data.total_journeys || 1)) *
      100
    ).toFixed(1);

    const isEntry = selectedLink.source === '__START__';
    const isConv = selectedLink.target === '__CONVERSION__';

    return (
      <div
        className="w-full sm:w-80 bg-white/95 backdrop-blur-md border border-gray-200/90 rounded-2xl shadow-float p-4.5 text-xs animate-in fade-in slide-in-from-right-4 duration-200"
        role="dialog"
        aria-label="Transition Pathway Details"
      >
        <div className="flex items-center justify-between pb-3 border-b border-gray-100 mb-3">
          <div className="flex items-center gap-1.5 font-bold font-display text-graphite-950 text-sm">
            <Repeat className="w-4 h-4 text-coral-600" />
            <span>Pathway Details</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-graphite-900 hover:bg-gray-100 transition-colors"
            aria-label="Close details"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Transition title */}
        <div className="p-3 bg-ivory-50 rounded-xl border border-gray-200/70 mb-3">
          <div className="text-[10px] uppercase font-mono font-bold text-gray-400 mb-1">
            {isEntry ? 'Entry Transition' : isConv ? 'Conversion Step' : 'Channel Handoff'}
          </div>
          <div className="flex items-center gap-2 font-bold text-graphite-900 text-sm">
            <span className="truncate">{srcLabel}</span>
            <ArrowRight className="w-4 h-4 text-coral-500 shrink-0" />
            <span className="truncate text-coral-600">{tgtLabel}</span>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div className="bg-gray-50 p-2.5 rounded-xl border border-gray-100">
            <div className="text-[10px] text-gray-400 font-mono uppercase font-bold">
              Volume
            </div>
            <div className="text-base font-bold font-mono text-graphite-950 mt-0.5">
              {selectedLink.value.toLocaleString()}
            </div>
            <div className="text-[10px] text-gray-500">traversals</div>
          </div>
          <div className="bg-gray-50 p-2.5 rounded-xl border border-gray-100">
            <div className="text-[10px] text-gray-400 font-mono uppercase font-bold">
              Journey Share
            </div>
            <div className="text-base font-bold font-mono text-coral-600 mt-0.5">
              {shareOfTotal}%
            </div>
            <div className="text-[10px] text-gray-500">of all journeys</div>
          </div>
        </div>

        <p className="text-[11px] text-gray-500 leading-relaxed">
          {isEntry
            ? `${selectedLink.value} customers started their discovery trajectory through ${tgtLabel}.`
            : isConv
            ? `${selectedLink.value} customers successfully converted directly after engaging with ${srcLabel}.`
            : `${selectedLink.value} journeys transitioned directly from ${srcLabel} to ${tgtLabel}.`}
        </p>
      </div>
    );
  }

  // Case 2: A specific node is selected
  const node = data.nodes.find((n) => n.id === selectedNodeId);
  if (!node) return null;

  const isStart = node.type === 'start';
  const isConv = node.type === 'conversion';

  // Inbound links to this node
  const inboundLinks = data.links
    .filter((l) => l.target === node.id)
    .sort((a, b) => b.value - a.value);

  // Outbound links from this node
  const outboundLinks = data.links
    .filter((l) => l.source === node.id)
    .sort((a, b) => b.value - a.value);

  const totalInbound = inboundLinks.reduce((acc, l) => acc + l.value, 0);
  const totalOutbound = outboundLinks.reduce((acc, l) => acc + l.value, 0);

  // Direct conversions from this channel
  const directConversions =
    outboundLinks.find((l) => l.target === '__CONVERSION__')?.value ?? 0;
  const directEntries =
    inboundLinks.find((l) => l.source === '__START__')?.value ?? 0;

  const shareOfJourneys = (
    (Math.max(totalInbound, totalOutbound) / (data.total_journeys || 1)) *
    100
  ).toFixed(1);

  return (
    <div
      className="w-full sm:w-84 max-h-[460px] overflow-y-auto bg-white/95 backdrop-blur-md border border-gray-200/90 rounded-2xl shadow-float p-4.5 text-xs animate-in fade-in slide-in-from-right-4 duration-200 space-y-3.5"
      role="dialog"
      aria-label={`${node.label} details`}
    >
      {/* Header */}
      <div className="flex items-start justify-between pb-2.5 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isStart
                  ? 'bg-graphite-900'
                  : isConv
                  ? 'bg-emerald-600'
                  : 'bg-blue-600'
              }`}
            />
            <h3 className="font-bold font-display text-graphite-950 text-sm leading-tight">
              {node.label}
            </h3>
          </div>
          <span className="text-[10px] text-gray-400 font-mono uppercase font-bold tracking-wider mt-0.5 inline-block">
            {isStart
              ? 'Journey Entry Point'
              : isConv
              ? 'Final Conversion Goal'
              : 'Marketing Channel'}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-gray-400 hover:text-graphite-900 hover:bg-gray-100 transition-colors"
          aria-label="Close inspector"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* KPI Badges */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-ivory-50 p-2 rounded-xl border border-gray-100">
          <div className="text-[9.5px] uppercase font-mono font-bold text-gray-400">
            Total Traffic
          </div>
          <div className="text-base font-bold font-mono text-graphite-900 mt-0.5">
            {Math.max(totalInbound, totalOutbound).toLocaleString()}
          </div>
          <div className="text-[10px] text-gray-500">{shareOfJourneys}% of journeys</div>
        </div>

        <div className="bg-ivory-50 p-2 rounded-xl border border-gray-100">
          <div className="text-[9.5px] uppercase font-mono font-bold text-gray-400">
            {isConv ? 'Total Converted' : 'Conversions Driven'}
          </div>
          <div className="text-base font-bold font-mono text-emerald-600 mt-0.5">
            {isConv ? data.converted_journeys : directConversions}
          </div>
          <div className="text-[10px] text-gray-500">
            {isConv
              ? 'successful goals'
              : `${((directConversions / (totalOutbound || 1)) * 100).toFixed(1)}% closure`}
          </div>
        </div>
      </div>

      {/* Inbound Sources Breakdown */}
      {!isStart && inboundLinks.length > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-bold text-graphite-700">
            <span className="flex items-center gap-1">
              <LogIn className="w-3 h-3 text-blue-500" />
              <span>Inbound Sources ({inboundLinks.length})</span>
            </span>
            <span className="text-[10px] font-mono text-gray-400 font-normal">
              {totalInbound} total
            </span>
          </div>
          <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
            {inboundLinks.map((link) => {
              const srcNode = data.nodes.find((n) => n.id === link.source);
              const label = srcNode?.label ?? link.source;
              const pctVal = ((link.value / (totalInbound || 1)) * 100).toFixed(0);
              return (
                <div
                  key={link.source}
                  className="flex items-center justify-between p-1.5 rounded-lg bg-gray-50/80 border border-gray-100 text-[11px]"
                >
                  <span className="truncate max-w-[140px] text-graphite-800">
                    {label === 'Journey Start' ? '⚡ Direct Entry' : label}
                  </span>
                  <span className="font-mono font-semibold text-graphite-900 shrink-0">
                    {link.value}{' '}
                    <span className="text-[10px] font-normal text-gray-400">({pctVal}%)</span>
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Outbound Destinations Breakdown */}
      {!isConv && outboundLinks.length > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-bold text-graphite-700">
            <span className="flex items-center gap-1">
              <ArrowRight className="w-3 h-3 text-coral-500" />
              <span>Where Users Went Next ({outboundLinks.length})</span>
            </span>
            <span className="text-[10px] font-mono text-gray-400 font-normal">
              {totalOutbound} total
            </span>
          </div>
          <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
            {outboundLinks.map((link) => {
              const tgtNode = data.nodes.find((n) => n.id === link.target);
              const label = tgtNode?.label ?? link.target;
              const pctVal = ((link.value / (totalOutbound || 1)) * 100).toFixed(0);
              const isGoal = link.target === '__CONVERSION__';

              return (
                <div
                  key={link.target}
                  className={`flex items-center justify-between p-1.5 rounded-lg border text-[11px] ${
                    isGoal
                      ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900 font-medium'
                      : 'bg-gray-50/80 border-gray-100 text-graphite-800'
                  }`}
                >
                  <span className="truncate max-w-[140px]">
                    {isGoal ? '🏆 Conversion' : label}
                  </span>
                  <span className="font-mono font-semibold shrink-0">
                    {link.value}{' '}
                    <span className="text-[10px] font-normal text-gray-400">({pctVal}%)</span>
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
