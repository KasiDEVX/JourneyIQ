import React from 'react';
import {
  Menu,
  RotateCw,
  Calendar,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface HeaderProps {
  onOpenMobileMenu: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  apiOnline: boolean | null;
  lastUpdated: Date | null;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenMobileMenu,
  onRefresh,
  isRefreshing,
  apiOnline,
  lastUpdated,
}) => {
  return (
    <header className="sticky top-0 z-30 bg-[#F6F7F9]/85 backdrop-blur-md border-b border-gray-200/80 px-6 py-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Left: Title & Subtitle */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenMobileMenu}
            className="lg:hidden p-2 rounded-xl text-graphite-700 hover:bg-gray-200/80 transition-colors"
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-bold font-display tracking-tight text-graphite-950">
                Journey Intelligence
              </h1>
              <span className="hidden md:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-coral-50 text-coral-600 border border-coral-200/60">
                <Sparkles className="w-3 h-3 text-coral-500" />
                Live Engine
              </span>
            </div>
            <p className="text-xs sm:text-sm text-gray-500 mt-0.5">
              Understand how customers move from discovery to conversion.
            </p>
          </div>
        </div>

        {/* Right: Date, Refresh & Status */}
        <div className="flex items-center gap-2.5 shrink-0 self-end sm:self-auto">
          {/* Cohort/Date Indicator Pill */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-gray-200 text-xs text-graphite-700 shadow-xs">
            <Calendar className="w-3.5 h-3.5 text-gray-400" />
            <span className="font-medium text-graphite-800">All Campaigns</span>
            <span className="w-1 h-1 rounded-full bg-gray-300" />
            <span className="text-gray-500 font-mono text-[11px]">500 Customers</span>
          </div>

          {/* Refresh Action */}
          <Button
            variant="secondary"
            size="sm"
            onClick={onRefresh}
            disabled={isRefreshing}
            icon={
              <RotateCw
                className={`w-3.5 h-3.5 text-graphite-600 ${isRefreshing ? 'animate-spin' : ''}`}
              />
            }
          >
            <span className="hidden sm:inline">Refresh</span>
          </Button>

          {/* Connection status badge */}
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border shadow-xs ${
              apiOnline === true
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : apiOnline === false
                ? 'bg-red-50 text-red-700 border-red-200'
                : 'bg-amber-50 text-amber-700 border-amber-200'
            }`}
          >
            {apiOnline === true ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            )}
            <span className="hidden md:inline">
              {apiOnline === true ? 'API Connected' : 'API Connecting'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
