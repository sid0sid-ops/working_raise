import type React from 'react';

export interface CircularUploadProgressProps {
  progress?: number; // 0 to 100
  size?: number; // diameter in pixels (default: 24)
  strokeWidth?: number; // stroke width (default: 2.5)
  className?: string;
  showPercentText?: boolean;
}

export const CircularUploadProgress: React.FC<CircularUploadProgressProps> = ({
  progress = 45,
  size = 24,
  strokeWidth = 2.5,
  className = '',
  showPercentText = false,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedProgress = Math.min(100, Math.max(0, progress));
  const strokeDashoffset = circumference - (clampedProgress / 100) * circumference;

  return (
    <div
      className={`relative inline-flex items-center justify-center shrink-0 ${className}`}
      style={{ width: size, height: size }}
      role="progressbar"
      aria-valuenow={clampedProgress}
      aria-valuemin={0}
      aria-valuemax={100}
      title={`Uploading & parsing in GraphRAG... (${Math.round(clampedProgress)}%)`}
    >
      {/* Background and Progress SVG */}
      <svg className="w-full h-full -rotate-90 transform" viewBox={`0 0 ${size} ${size}`}>
        {/* Background Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          className="text-slate-200/80 dark:text-white/10"
        />

        {/* Animated Progress Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="none"
          className="text-indigo-600 dark:text-[#a8c7fa] transition-all duration-300 ease-out"
        />
      </svg>

      {/* Moving Orbit Spinner Accent */}
      {clampedProgress < 100 && (
        <div
          className="absolute inset-0 animate-spin pointer-events-none"
          style={{ animationDuration: '1.4s' }}
        >
          <div
            className="w-1.5 h-1.5 rounded-full bg-indigo-500 dark:bg-[#a8c7fa] shadow-xs"
            style={{
              position: 'absolute',
              top: 0,
              left: '50%',
              transform: 'translateX(-50%)',
            }}
          />
        </div>
      )}

      {showPercentText && (
        <span className="absolute text-[8px] font-mono font-semibold text-slate-700 dark:text-slate-200 select-none">
          {Math.round(clampedProgress)}%
        </span>
      )}
    </div>
  );
};
