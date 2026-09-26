import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'coral' | 'emerald' | 'amber' | 'neutral' | 'dark';
  size?: 'sm' | 'md';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  className = '',
}) => {
  const baseClasses = 'inline-flex items-center font-medium tracking-tight rounded-full transition-colors';

  const sizeClasses = {
    sm: 'px-2.5 py-0.5 text-xs',
    md: 'px-3 py-1 text-xs',
  }[size];

  const variantClasses = {
    default: 'bg-ivory-100 text-graphite-700 border border-ivory-300',
    coral: 'bg-coral-50 text-coral-600 border border-coral-200 font-semibold',
    emerald: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    amber: 'bg-amber-50 text-amber-800 border border-amber-200',
    neutral: 'bg-gray-100 text-gray-700 border border-gray-200',
    dark: 'bg-graphite-900 text-ivory-100 border border-graphite-700',
  }[variant];

  return (
    <span className={`${baseClasses} ${sizeClasses} ${variantClasses} ${className}`}>
      {children}
    </span>
  );
};
