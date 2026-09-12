import React from 'react';
import { cn } from '../../utils/formatters';

export interface StatusIndicatorProps {
  status: 'online' | 'offline' | 'degraded' | 'mock';
  label?: string;
  pulse?: boolean;
  className?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  pulse = true,
  className,
}) => {
  const colors = {
    online: 'bg-emerald-500 text-emerald-700 dark:text-emerald-400',
    offline: 'bg-rose-500 text-rose-700 dark:text-rose-400',
    degraded: 'bg-amber-500 text-amber-700 dark:text-amber-400',
    mock: 'bg-yellow-400 text-yellow-800 dark:text-yellow-300',
  };

  const ringColors = {
    online: 'bg-emerald-400',
    offline: 'bg-rose-400',
    degraded: 'bg-amber-400',
    mock: 'bg-yellow-400',
  };

  return (
    <span className={cn('inline-flex items-center gap-1.5 text-xs font-medium', className)}>
      <span className="relative flex h-2 w-2">
        {pulse && status !== 'offline' && (
          <span
            className={cn(
              'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
              ringColors[status]
            )}
          />
        )}
        <span
          className={cn(
            'relative inline-flex rounded-full h-2 w-2',
            colors[status].split(' ')[0]
          )}
        />
      </span>
      {label && <span className={colors[status].split(' ')[1]}>{label}</span>}
    </span>
  );
};
