// src/components/journey-flow/JourneyFlowControls.tsx
//
// Filter and presentation controls for the Journey Flow visualization.
// Features conversion filter, view mode toggle (Flow Map vs Data Breakdown),
// journey limit selector, and live journey stats.

import React from 'react';
import { Filter, GitFork, LayoutGrid, Users } from 'lucide-react';
import { ConversionFilter } from '@/types/analytics';

interface Props {
  conversion: ConversionFilter;
  limit: number;
  viewMode: 'graph' | 'breakdown';
  onConversionChange: (value: ConversionFilter) => void;
  onLimitChange: (value: number) => void;
  onViewModeChange: (value: 'graph' | 'breakdown') => void;
  totalJourneys: number;
  convertedJourneys: number;
  nonConvertedJourneys: number;
  loading: boolean;
}

const CONVERSION_OPTIONS: { value: ConversionFilter; label: string }[] = [
  { value: 'all', label: 'All Journeys' },
  { value: 'converted', label: 'Converted' },
  { value: 'non_converted', label: 'Non-Converted' },
];

const LIMIT_OPTIONS = [100, 250, 500, 1000, 2000, 5000];

export const JourneyFlowControls: React.FC<Props> = ({
  conversion,
  limit,
  viewMode,
  onConversionChange,
  onLimitChange,
  onViewModeChange,
  totalJourneys,
  convertedJourneys,
  nonConvertedJourneys,
  loading,
}) => {
  return (
    <div
      className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 p-1.5 bg-ivory-100/70 border border-gray-200/80 rounded-2xl"
      role="toolbar"
      aria-label="Journey flow controls"
    >
      {/* Left: Journey Type Tabs */}
      <div className="flex items-center gap-2 px-1">
        <Filter className="w-3.5 h-3.5 text-gray-400 shrink-0 ml-1" aria-hidden="true" />
        <span className="text-[11px] font-bold text-gray-500 uppercase font-mono tracking-wider hidden sm:inline">
          Filter:
        </span>
        <div
          className="flex items-center gap-1 p-0.5 bg-white/70 rounded-xl border border-gray-200/70 text-xs"
          role="group"
          aria-label="Filter journeys by outcome"
        >
          {CONVERSION_OPTIONS.map((opt) => {
            const isActive = conversion === opt.value;
            return (
              <button
                key={opt.value}
                id={`flow-filter-${opt.value}`}
                onClick={() => onConversionChange(opt.value)}
                disabled={loading}
                aria-pressed={isActive}
                className={`
                  px-3 py-1.5 rounded-lg font-medium text-[11px] transition-all
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-coral-500
                  disabled:opacity-50 disabled:cursor-not-allowed
                  ${
                    isActive
                      ? 'bg-graphite-950 text-white shadow-xs font-semibold'
                      : 'text-gray-600 hover:text-graphite-950 hover:bg-gray-100/70'
                  }
                `}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Right Controls: View Mode Toggle + Stats + Limit Selector */}
      <div className="flex flex-wrap items-center justify-between lg:justify-end gap-2 px-1">
        {/* View Mode Toggle */}
        <div
          className="flex items-center gap-1 p-0.5 bg-white/70 rounded-xl border border-gray-200/70 text-xs"
          role="group"
          aria-label="Toggle presentation view"
        >
          <button
            onClick={() => onViewModeChange('graph')}
            aria-pressed={viewMode === 'graph'}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
              viewMode === 'graph'
                ? 'bg-coral-50 text-coral-700 font-bold border border-coral-200/70 shadow-2xs'
                : 'text-gray-500 hover:text-graphite-900'
            }`}
          >
            <GitFork className="w-3 h-3" aria-hidden="true" />
            <span>Flow Map</span>
          </button>
          <button
            onClick={() => onViewModeChange('breakdown')}
            aria-pressed={viewMode === 'breakdown'}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
              viewMode === 'breakdown'
                ? 'bg-coral-50 text-coral-700 font-bold border border-coral-200/70 shadow-2xs'
                : 'text-gray-500 hover:text-graphite-900'
            }`}
          >
            <LayoutGrid className="w-3 h-3" aria-hidden="true" />
            <span>Breakdown</span>
          </button>
        </div>

        {/* Live Journey Count Pill */}
        {!loading && totalJourneys > 0 && (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-white/80 border border-gray-200/70 text-[11px] font-mono text-gray-500">
            <Users className="w-3 h-3 text-gray-400" aria-hidden="true" />
            <span className="font-bold text-graphite-800">{totalJourneys.toLocaleString()}</span>
            <span>journeys</span>
            {convertedJourneys > 0 && (
              <span className="text-emerald-700 font-bold">({convertedJourneys} converted)</span>
            )}
          </div>
        )}

        {/* Limit Dropdown */}
        <div className="flex items-center gap-1.5 pl-1">
          <label htmlFor="flow-limit-select" className="text-[11px] font-mono text-gray-400 uppercase">
            Limit:
          </label>
          <select
            id="flow-limit-select"
            value={limit}
            onChange={(e) => onLimitChange(Number(e.target.value))}
            disabled={loading}
            aria-label="Maximum journeys analyzed"
            className="text-xs font-mono bg-white border border-gray-200/80 rounded-lg px-2 py-1 text-graphite-800 focus:outline-none focus:ring-1 focus:ring-coral-500 cursor-pointer"
          >
            {LIMIT_OPTIONS.map((v) => (
              <option key={v} value={v}>
                {v.toLocaleString()}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};
