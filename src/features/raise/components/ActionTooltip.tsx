import React from 'react';

export interface ActionTooltipProps {
  label: string;
  children: React.ReactNode;
  position?: 'top' | 'bottom';
  className?: string;
}

export const ActionTooltip: React.FC<ActionTooltipProps> = ({
  label,
  children,
  position = 'top',
  className = '',
}) => {
  return (
    <div className={`relative group/tip inline-flex items-center justify-center ${className}`}>
      {children}
      <div
        role="tooltip"
        className={`pointer-events-none absolute ${
          position === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'
        } left-1/2 -translate-x-1/2 opacity-0 group-hover/tip:opacity-100 transition-opacity duration-150 flex items-center px-2.5 py-1 text-[11px] font-medium tracking-normal text-white bg-slate-900/95 dark:bg-slate-800/95 rounded-md shadow-lg border border-slate-700/60 dark:border-white/10 whitespace-nowrap z-50`}
      >
        {label}
        <div
          className={`absolute left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-slate-900/95 dark:bg-slate-800/95 border-slate-700/60 dark:border-white/10 rotate-45 ${
            position === 'top'
              ? 'top-full -mt-1 border-r border-b'
              : 'bottom-full -mb-1 border-l border-t'
          }`}
        />
      </div>
    </div>
  );
};
