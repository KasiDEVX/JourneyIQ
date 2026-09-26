import React from 'react';

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '' }) => {
  return (
    <div
      className={`animate-pulse bg-gray-200/80 rounded-xl ${className}`}
      aria-hidden="true"
    />
  );
};

export const CardSkeleton: React.FC<{ rows?: number }> = ({ rows = 3 }) => {
  return (
    <div className="card-soft p-6 space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-7 w-7 rounded-full" />
      </div>
      <Skeleton className="h-9 w-36" />
      <div className="space-y-2 pt-2">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-3.5 w-full" />
        ))}
      </div>
    </div>
  );
};
