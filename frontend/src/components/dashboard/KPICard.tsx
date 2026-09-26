import React from 'react';

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  badge?: {
    text: string;
    variant?: 'coral' | 'emerald' | 'amber' | 'neutral';
  };
  icon?: React.ReactNode;
  accent?: boolean;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  badge,
  icon,
  accent = false,
}) => {
  return (
    <div
      className={`card-soft p-6 relative overflow-hidden transition-all duration-200 group ${
        accent ? 'border-coral-200/80 bg-linear-to-b from-white to-coral-50/20' : ''
      }`}
    >
      {/* Top row: Label and Icon */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500 font-mono">
          {title}
        </span>
        {icon && (
          <div
            className={`w-8 h-8 rounded-xl flex items-center justify-center transition-colors ${
              accent
                ? 'bg-coral-100/70 text-coral-600'
                : 'bg-ivory-100 text-graphite-600 group-hover:bg-gray-100'
            }`}
          >
            {icon}
          </div>
        )}
      </div>

      {/* Main value */}
      <div className="flex items-baseline gap-2 mb-2">
        <div className="text-3xl font-extrabold font-display tracking-tight text-graphite-950 font-mono">
          {value}
        </div>
      </div>

      {/* Bottom metadata */}
      {(subtitle || badge) && (
        <div className="flex items-center gap-2 pt-1 border-t border-gray-100/80">
          {badge && (
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold tracking-tight ${
                badge.variant === 'coral'
                  ? 'bg-coral-50 text-coral-600 border border-coral-200'
                  : badge.variant === 'emerald'
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : badge.variant === 'amber'
                  ? 'bg-amber-50 text-amber-800 border border-amber-200'
                  : 'bg-gray-100 text-gray-600 border border-gray-200'
              }`}
            >
              {badge.text}
            </span>
          )}
          {subtitle && (
            <span className="text-xs text-gray-400 font-medium truncate">
              {subtitle}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
