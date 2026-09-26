import type React from 'react';
import type { DocumentIngestionPhase } from '../../types';

// ─── Phase metadata ───────────────────────────────────────────────────────────

interface PhaseMeta {
  label: string;
  /** Tailwind / inline colour for the ring stroke */
  color: string;
  /** SVG animation class (fast spin, slow spin, medium spin, fastest spin, none) */
  spinClass: string;
  /** Whether the ring should appear slightly blurred (uploading) */
  blurred: boolean;
}

const PHASE_META: Record<DocumentIngestionPhase, PhaseMeta> = {
  uploading: {
    label: 'Uploading',
    color: '#38bdf8', // sky-400
    spinClass: 'animate-[spin_1.2s_linear_infinite]', // Fast spin
    blurred: true,
  },
  parsing: {
    label: 'Parsing',
    color: '#818cf8', // indigo-400
    spinClass: 'animate-[spin_3.5s_linear_infinite]', // Slow spin
    blurred: false,
  },
  chunking: {
    label: 'Chunking',
    color: '#34d399', // emerald-400
    spinClass: 'animate-[spin_2s_linear_infinite]', // Medium spin
    blurred: false,
  },
  embedding: {
    label: 'Embedding',
    color: '#fb923c', // orange-400
    spinClass: 'animate-[spin_0.8s_linear_infinite]', // Fastest spin
    blurred: false,
  },
  ready: {
    label: 'Ready',
    color: '#4ade80', // green-400
    spinClass: '', // None (static)
    blurred: false,
  },
  error: {
    label: 'Error',
    color: '#f87171', // red-400
    spinClass: '', // None (static)
    blurred: false,
  },
};

// ─── Component ────────────────────────────────────────────────────────────────

export interface IngestionProgressRingProps {
  phase: DocumentIngestionPhase;
  percent: number;
  /** Ring outer diameter in px (default 104 - big centered ring) */
  size?: number;
  /** Ring stroke width in px (default 6) */
  strokeWidth?: number;
}

/**
 * Big single circular progress ring in the center.
 * Renders exactly ONE unified SVG with background track + single progress arc.
 */
export const IngestionProgressRing: React.FC<IngestionProgressRingProps> = ({
  phase,
  percent,
  size = 104,
  strokeWidth = 6,
}) => {
  const meta = PHASE_META[phase] || PHASE_META.uploading;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const isIndeterminate = phase === 'uploading';
  const isTerminal = phase === 'ready' || phase === 'error';

  // Arc stroke offset:
  // - uploading: indeterminate 30% arc
  // - ready: full ring (offset 0)
  // - others: arc tracks percent (0% - 100%)
  const clampedPercent = Math.min(100, Math.max(0, percent));
  const dashOffset = isIndeterminate
    ? circumference * 0.7
    : phase === 'ready'
      ? 0
      : circumference - (circumference * clampedPercent) / 100;

  return (
    <div className="flex flex-col items-center justify-center gap-2 select-none">
      {/* Exactly ONE Big Progress Ring in Center */}
      <div
        className="relative flex items-center justify-center"
        style={{ width: size, height: size }}
        aria-label={`Ingestion ${meta.label} — ${percent}%`}
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        {/* Single SVG containing both track circle and progress arc */}
        <svg
          width={size}
          height={size}
          className={`w-full h-full -rotate-90 ${isTerminal ? '' : meta.spinClass}`}
          viewBox={`0 0 ${size} ${size}`}
        >
          {/* Static background track circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#1e293b" // slate-800
            strokeWidth={strokeWidth}
          />

          {/* Active progress stroke arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={meta.color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            style={{
              filter: meta.blurred ? 'blur(1.5px)' : undefined,
              transition: isIndeterminate ? undefined : 'stroke-dashoffset 0.4s ease',
            }}
          />
        </svg>

        {/* Big percentage / icon in the center */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          {isTerminal ? (
            phase === 'ready' ? (
              // Big ✓ Checkmark
              <svg viewBox="0 0 16 16" width={size * 0.38} height={size * 0.38} fill="none">
                <path
                  d="M3 8l3.5 3.5L13 5"
                  stroke="#4ade80"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            ) : (
              // Big ! Exclamation
              <svg viewBox="0 0 16 16" width={size * 0.38} height={size * 0.38} fill="none">
                <path
                  d="M8 3.5v5M8 11.5v1"
                  stroke="#f87171"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                />
              </svg>
            )
          ) : (
            <span
              className="font-mono font-bold tracking-tight tabular-nums"
              style={{ fontSize: size * 0.24, color: meta.color }}
            >
              {clampedPercent}%
            </span>
          )}
        </div>
      </div>

      {/* Prominent Phase label */}
      <span className="text-xs font-bold tracking-wider uppercase" style={{ color: meta.color }}>
        {meta.label}
      </span>
    </div>
  );
};
