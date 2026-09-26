// src/components/journey-flow/JourneyFlowTooltip.tsx
//
// Tooltip for the Journey Flow visualization.
// Appears on hover over nodes or links.
// Displays exact metrics according to specification.

import React from 'react';

export interface NodeTooltipData {
  kind: 'node';
  label: string;
  type: 'start' | 'channel' | 'conversion';
  incomingJourneys: number;
  outgoingJourneys: number;
  totalJourneys: number;
  convertedJourneys: number;
}

export interface LinkTooltipData {
  kind: 'link';
  fromLabel: string;
  toLabel: string;
  journeyCount: number;
  totalJourneys: number;
}

export type TooltipData = NodeTooltipData | LinkTooltipData;

interface Props {
  data: TooltipData;
  x: number;
  y: number;
}

export const JourneyFlowTooltip: React.FC<Props> = ({ data, x, y }) => {
  const style: React.CSSProperties = {
    position: 'fixed',
    left: x + 16,
    top: y - 8,
    zIndex: 50,
    pointerEvents: 'none',
  };

  return (
    <div
      style={style}
      role="tooltip"
      className="bg-graphite-900 text-white rounded-xl shadow-xl px-4 py-3 text-xs min-w-[220px] max-w-[280px] border border-graphite-700/80 pointer-events-none"
    >
      {data.kind === 'node' ? (
        <NodeTooltipContent data={data} />
      ) : (
        <LinkTooltipContent data={data} />
      )}
    </div>
  );
};

const NodeTooltipContent: React.FC<{ data: NodeTooltipData }> = ({ data }) => {
  if (data.type === 'conversion') {
    return (
      <div className="space-y-2">
        <div className="font-semibold font-display text-sm text-white leading-tight">
          {data.label}
        </div>
        <div className="text-emerald-400 text-[10px] uppercase font-mono font-bold tracking-wider">
          Conversion Goal
        </div>
        <div className="border-t border-graphite-700 pt-2 space-y-1.5 font-mono text-xs">
          <div className="flex justify-between gap-4">
            <span className="text-graphite-400">Conversion journeys</span>
            <span className="font-bold text-white">{data.convertedJourneys.toLocaleString()}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-graphite-400">Total conversion flow</span>
            <span className="font-bold text-emerald-400">{data.incomingJourneys.toLocaleString()}</span>
          </div>
        </div>
      </div>
    );
  }

  if (data.type === 'start') {
    return (
      <div className="space-y-2">
        <div className="font-semibold font-display text-sm text-white leading-tight">
          {data.label}
        </div>
        <div className="text-graphite-400 text-[10px] uppercase font-mono font-bold tracking-wider">
          Journey Entry Point
        </div>
        <div className="border-t border-graphite-700 pt-2 space-y-1.5 font-mono text-xs">
          <div className="flex justify-between gap-4">
            <span className="text-graphite-400">Outgoing journey volume</span>
            <span className="font-bold text-white">{data.outgoingJourneys.toLocaleString()}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="font-semibold font-display text-sm text-white leading-tight">
        {data.label}
      </div>
      <div className="text-gray-400 text-[10px] uppercase font-mono font-bold tracking-wider">
        Channel
      </div>
      <div className="border-t border-graphite-700 pt-2 space-y-1.5 font-mono text-xs">
        <div className="flex justify-between gap-4">
          <span className="text-graphite-400">Incoming journey volume</span>
          <span className="font-bold text-white">{data.incomingJourneys.toLocaleString()}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-graphite-400">Outgoing journey volume</span>
          <span className="font-bold text-white">{data.outgoingJourneys.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
};

const LinkTooltipContent: React.FC<{ data: LinkTooltipData }> = ({ data }) => {
  const percentage = data.totalJourneys > 0
    ? ((data.journeyCount / data.totalJourneys) * 100).toFixed(1)
    : '0.0';

  return (
    <div className="space-y-2">
      <div className="space-y-1">
        <div className="text-[10px] uppercase font-mono font-bold text-graphite-400 tracking-wider">
          Transition Link
        </div>
        <div className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-xs">
          <span className="text-graphite-400 font-mono">From:</span>
          <span className="font-bold text-white truncate">{data.fromLabel}</span>
          <span className="text-graphite-400 font-mono">To:</span>
          <span className="font-bold text-coral-400 truncate">{data.toLabel}</span>
        </div>
      </div>
      <div className="border-t border-graphite-700 pt-2 space-y-1.5 font-mono text-xs">
        <div className="flex justify-between gap-4">
          <span className="text-graphite-400">Journey count</span>
          <span className="font-bold text-white">{data.journeyCount.toLocaleString()}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-graphite-400">Percentage of displayed journeys</span>
          <span className="font-bold text-coral-300">{percentage}%</span>
        </div>
      </div>
    </div>
  );
};
