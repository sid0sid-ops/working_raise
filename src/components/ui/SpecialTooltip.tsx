import React from 'react';

export interface SpecialTooltipProps {
  label: React.ReactNode;
  position?: 'right' | 'top' | 'bottom' | 'left';
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
}

export const SpecialTooltip: React.FC<SpecialTooltipProps> = ({
  label,
  position = 'right',
  children,
  className = '',
  disabled = false,
}) => {
  const positionClasses = {
    right: 'left-full ml-2.5 top-1/2 -translate-y-1/2',
    left: 'right-full mr-2.5 top-1/2 -translate-y-1/2',
    top: 'bottom-full mb-2 left-1/2 -translate-x-1/2',
    bottom: 'top-full mt-2 left-1/2 -translate-x-1/2',
  };

  const arrowClasses = {
    right: '-left-1 top-1/2 -translate-y-1/2 border-y-4 border-y-transparent border-r-4 border-r-slate-900 dark:border-r-[#282a2c]',
    left: '-right-1 top-1/2 -translate-y-1/2 border-y-4 border-y-transparent border-l-4 border-l-slate-900 dark:border-l-[#282a2c]',
    top: '-bottom-1 left-1/2 -translate-x-1/2 border-x-4 border-x-transparent border-t-4 border-t-slate-900 dark:border-t-[#282a2c]',
    bottom: '-top-1 left-1/2 -translate-x-1/2 border-x-4 border-x-transparent border-b-4 border-b-slate-900 dark:border-b-[#282a2c]',
  };

  return (
    <div className={`relative group/tooltip inline-flex items-center justify-center ${className}`}>
      {children}
      {!disabled && (
        <div
          role="tooltip"
          className={`pointer-events-none absolute ${positionClasses[position]} z-[120] hidden group-hover/tooltip:flex group-hover:flex items-center px-2.5 py-1 rounded-lg text-[11px] font-medium whitespace-nowrap shadow-xl bg-slate-900 text-white border border-slate-700/60 dark:bg-[#282a2c] dark:text-[#e3e3e3] dark:border-[#37393b] animate-in fade-in zoom-in-95 duration-150`}
        >
          <span className={`absolute w-0 h-0 ${arrowClasses[position]}`} />
          {label}
        </div>
      )}
    </div>
  );
};
