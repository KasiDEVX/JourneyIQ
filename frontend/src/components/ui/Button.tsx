import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'coral';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'secondary',
  size = 'md',
  icon,
  className = '',
  disabled,
  ...props
}) => {
  const base = 'inline-flex items-center justify-center font-medium rounded-full transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] select-none';

  const sizes = {
    sm: 'px-3 py-1.5 text-xs gap-1.5',
    md: 'px-4 py-2 text-sm gap-2',
    lg: 'px-5 py-2.5 text-base gap-2.5',
  }[size];

  const variants = {
    primary: 'bg-graphite-900 hover:bg-graphite-850 text-white shadow-sm hover:shadow',
    secondary: 'bg-white hover:bg-ivory-100 text-graphite-800 border border-ivory-300 shadow-sm',
    outline: 'bg-transparent hover:bg-ivory-100 text-graphite-700 border border-gray-300',
    ghost: 'bg-transparent hover:bg-gray-100 text-graphite-600',
    coral: 'bg-coral-500 hover:bg-coral-600 text-white shadow-sm shadow-coral-500/20',
  }[variant];

  return (
    <button
      className={`${base} ${sizes} ${variants} ${className}`}
      disabled={disabled}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </button>
  );
};
