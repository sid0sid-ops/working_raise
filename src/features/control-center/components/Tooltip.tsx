import { Info } from 'lucide-react';
import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

interface TooltipProps {
  content: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  as?: 'button' | 'span';
  size?: 'sm' | 'md';
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  className = '',
  as = 'button',
  size = 'md',
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLElement>(null);

  const updatePosition = () => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const tooltipWidth = size === 'sm' ? 120 : 260;
    const tooltipHeight = size === 'sm' ? 32 : 110;

    // Calculate optimal position above the trigger, centered horizontally
    let top = rect.top - tooltipHeight - 8;
    let left = rect.left + rect.width / 2 - tooltipWidth / 2;

    // If it goes above the viewport, position it below the trigger
    if (top < 10) {
      top = rect.bottom + 8;
    }

    // Keep within horizontal screen bounds
    if (left < 10) left = 10;
    if (left + tooltipWidth > window.innerWidth - 10) {
      left = window.innerWidth - tooltipWidth - 10;
    }

    setCoords({ top, left });
  };

  const handleMouseEnter = () => {
    updatePosition();
    setIsVisible(true);
  };

  const handleMouseLeave = () => {
    setIsVisible(false);
  };

  useEffect(() => {
    if (isVisible) {
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);
      return () => {
        window.removeEventListener('scroll', updatePosition, true);
        window.removeEventListener('resize', updatePosition);
      };
    }
  }, [isVisible]);

  const Component = as;

  return (
    <>
      <Component
        ref={triggerRef as any}
        {...(Component === 'button' ? { type: 'button' } : { tabIndex: 0, role: 'button' })}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={handleMouseEnter}
        onBlur={handleMouseLeave}
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
        className={`inline-flex items-center text-slate-400 hover:text-white transition-colors cursor-help p-1 rounded focus:outline-none ${className}`}
        aria-label="Technical details"
      >
        {children || <Info className="w-3.5 h-3.5" />}
      </Component>

      {isVisible &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            role="tooltip"
            style={{
              position: 'fixed',
              top: `${coords.top}px`,
              left: `${coords.left}px`,
              zIndex: 999999,
            }}
            className={`${
              size === 'sm'
                ? 'w-auto max-w-[180px] px-2.5 py-1 text-[11px] font-sans font-medium text-center rounded-md bg-[#131622] border border-white/20'
                : 'w-[260px] p-3 rounded-lg bg-[#0a0c12] border border-white/25 text-[11px] leading-relaxed'
            } text-slate-200 shadow-[0_10px_30px_rgba(0,0,0,0.8)] backdrop-blur-md pointer-events-none animate-in fade-in-50 duration-100`}
          >
            {content}
          </div>,
          document.body
        )}
    </>
  );
};
