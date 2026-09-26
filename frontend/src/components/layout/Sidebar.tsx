import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  GitFork,
  BarChart3,
  Layers,
  Users,
  Settings,
  HelpCircle,
  Activity,
  X,
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  apiOnline: boolean | null;
}

const navItems = [
  { name: 'Overview', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Journeys', path: '/journeys', icon: GitFork },
  { name: 'Attribution', path: '/attribution', icon: BarChart3 },
  { name: 'Channels', path: '/channels', icon: Layers },
  { name: 'Customers', path: '/customers', icon: Users },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose, apiOnline }) => {
  const location = useLocation();

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden backdrop-blur-xs transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Rail */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-graphite-950 text-white flex flex-col justify-between transition-transform duration-300 ease-in-out border-r border-graphite-850 ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Top: Logo & Nav */}
        <div>
          {/* Brand Wordmark */}
          <div className="h-20 flex items-center justify-between px-6 border-b border-graphite-900">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-coral-500 flex items-center justify-center shadow-lg shadow-coral-500/25">
                <span className="text-white font-extrabold text-base tracking-tighter">JQ</span>
              </div>
              <div>
                <span className="font-display font-bold text-lg text-white tracking-tight flex items-center gap-1.5">
                  Journey<span className="text-coral-500">IQ</span>
                </span>
                <span className="block text-[10px] font-medium tracking-wider text-graphite-500 uppercase">
                  Attribution Intelligence
                </span>
              </div>
            </div>

            {/* Mobile close button */}
            <button
              onClick={onClose}
              className="lg:hidden p-1.5 rounded-lg text-graphite-400 hover:text-white hover:bg-graphite-900"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5">
            <div className="px-3 py-2 text-[11px] font-semibold tracking-wider text-graphite-500 uppercase">
              Analytics
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                location.pathname === item.path ||
                (item.path === '/dashboard' && location.pathname === '/');

              return (
                <NavLink
                  key={item.name}
                  to={item.path}
                  onClick={onClose}
                  className={`flex items-center gap-3 px-3.5 py-2.5 rounded-2xl text-sm font-medium transition-all duration-150 ${
                    isActive
                      ? 'sidebar-pill-active text-coral-400 font-semibold shadow-inner'
                      : 'text-graphite-400 hover:text-ivory-100 hover:bg-graphite-900/80'
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-coral-500' : 'text-graphite-400'
                    }`}
                  />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Bottom Section */}
        <div className="p-4 border-t border-graphite-900 space-y-3">
          {/* API Status Pill */}
          <div className="px-3.5 py-2 rounded-xl bg-graphite-900/70 border border-graphite-800 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-graphite-400" />
              <span className="text-graphite-300 font-medium">FastAPI Engine</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  apiOnline === true
                    ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]'
                    : apiOnline === false
                    ? 'bg-red-400'
                    : 'bg-amber-400 animate-pulse'
                }`}
              />
              <span className="text-[11px] text-graphite-400 font-mono">
                {apiOnline === true ? 'Live' : apiOnline === false ? 'Offline' : 'Connecting'}
              </span>
            </div>
          </div>

          {/* Quick Settings & Help */}
          <div className="flex items-center justify-between text-graphite-400 px-2 py-1 text-xs">
            <button className="flex items-center gap-1.5 hover:text-white transition-colors">
              <Settings className="w-3.5 h-3.5" />
              <span>Config</span>
            </button>
            <button className="flex items-center gap-1.5 hover:text-white transition-colors">
              <HelpCircle className="w-3.5 h-3.5" />
              <span>Docs</span>
            </button>
          </div>

          {/* User profile capsule */}
          <div className="pt-2 border-t border-graphite-900 flex items-center gap-3 px-2">
            <div className="w-8 h-8 rounded-full bg-linear-to-tr from-graphite-700 to-graphite-600 flex items-center justify-center text-xs font-bold text-white border border-graphite-700">
              GA
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-ivory-100 truncate">Marketing Ops</p>
              <p className="text-[10px] text-graphite-400 truncate">demo@journeyiq.io</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
