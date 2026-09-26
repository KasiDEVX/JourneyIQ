import React from 'react';
import { AlertCircle, RefreshCw, Layers } from 'lucide-react';
import { Button } from './Button';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  isError?: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  actionLabel,
  onAction,
  isError = false,
}) => {
  return (
    <div className="card-soft p-12 text-center flex flex-col items-center justify-center max-w-lg mx-auto my-8 border border-dashed border-gray-300">
      <div
        className={`w-12 h-12 rounded-2xl flex items-center justify-center mb-4 ${
          isError ? 'bg-red-50 text-red-500' : 'bg-coral-50 text-coral-500'
        }`}
      >
        {icon || (isError ? <AlertCircle className="w-6 h-6" /> : <Layers className="w-6 h-6" />)}
      </div>
      <h3 className="text-base font-semibold text-graphite-900 mb-1">{title}</h3>
      <p className="text-sm text-gray-500 mb-6 max-w-sm">{description}</p>
      {onAction && (
        <Button
          variant={isError ? 'primary' : 'secondary'}
          size="sm"
          onClick={onAction}
          icon={<RefreshCw className="w-3.5 h-3.5" />}
        >
          {actionLabel || 'Retry'}
        </Button>
      )}
    </div>
  );
};
