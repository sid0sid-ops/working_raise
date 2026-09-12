import React from 'react';
import { cn } from '../../utils/formatters';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'outline';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  className,
  variant = 'default',
  ...props
}) => {
  const base = 'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium tracking-wide';
  const variants = {
    default: 'bg-slate-100 text-slate-800 border border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
    success: 'bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/80 dark:text-emerald-300 dark:border-emerald-800/80',
    warning: 'bg-amber-50 text-amber-800 border border-amber-200 dark:bg-amber-950/80 dark:text-amber-300 dark:border-amber-800/80',
    danger: 'bg-rose-50 text-rose-800 border border-rose-200 dark:bg-rose-950/80 dark:text-rose-300 dark:border-rose-800/80',
    info: 'bg-sky-50 text-sky-800 border border-sky-200 dark:bg-sky-950/80 dark:text-sky-300 dark:border-sky-800/80',
    outline: 'border border-slate-300 text-slate-600 bg-transparent dark:border-slate-700 dark:text-slate-400',
  };

  return (
    <span className={cn(base, variants[variant], className)} {...props}>
      {children}
    </span>
  );
};
