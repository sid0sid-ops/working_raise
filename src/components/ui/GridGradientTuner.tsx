import type React from 'react';
import { useEffect, useMemo, useState } from 'react';

export interface GridConfig {
  shape: 'circle' | 'ellipse';
  centerX: number;
  centerY: number;
  radiusX: number;
  radiusY: number;
  useClosestSide: boolean;
  innerCore: number;
  fadeMid: number;
  outerCutoff: number;
  dotSize: number;
  spacing: number;
  opacityLight: number;
  opacityDark: number;
}

export const DEFAULT_GRID_CONFIG: GridConfig = {
  shape: 'ellipse',
  centerX: 50,
  centerY: 50,
  radiusX: 57,
  radiusY: 80,
  useClosestSide: false,
  innerCore: 15,
  fadeMid: 60,
  outerCutoff: 100,
  dotSize: 1,
  spacing: 34,
  opacityLight: 0.76,
  opacityDark: 0.36,
};

export interface BoxLightConfig {
  shape: 'ellipse' | 'circle';
  preset: 'indigo' | 'cyan' | 'amber' | 'emerald' | 'monochrome' | 'custom';
  primaryColor: string;
  secondaryColor: string;
  spreadX: number; // 80 - 180 %
  spreadY: number; // 60 - 220 %
  offsetX: number; // -80 to +80 px
  offsetY: number; // -80 to +80 px
  blur: number; // 10 - 120 px
  opacityLight: number; // 0.05 - 0.90
  opacityDark: number; // 0.05 - 1.00
  innerCore: number; // 5 - 40 %
  midSpread: number; // 30 - 75 %
  outerCutoff: number; // 70 - 100 %
  pulse: boolean;
  showOnlyNewChat: boolean;
}

export const DEFAULT_BOX_LIGHT_CONFIG: BoxLightConfig = {
  shape: 'ellipse',
  preset: 'indigo',
  primaryColor: '#6366f1',
  secondaryColor: '#a855f7',
  spreadX: 125,
  spreadY: 135,
  offsetX: 0,
  offsetY: 0,
  blur: 48,
  opacityLight: 0.45,
  opacityDark: 0.7,
  innerCore: 20,
  midSpread: 55,
  outerCutoff: 90,
  pulse: false,
  showOnlyNewChat: true,
};

export const BOX_LIGHT_PRESETS: Record<
  'indigo' | 'cyan' | 'amber' | 'emerald' | 'monochrome',
  { name: string; primary: string; secondary: string; darkOpacity: number; lightOpacity: number }
> = {
  indigo: {
    name: 'Indigo & Violet',
    primary: '#6366f1',
    secondary: '#a855f7',
    darkOpacity: 0.7,
    lightOpacity: 0.45,
  },
  cyan: {
    name: 'Electric Cyan',
    primary: '#06b6d4',
    secondary: '#3b82f6',
    darkOpacity: 0.65,
    lightOpacity: 0.4,
  },
  amber: {
    name: 'Sunset Glow',
    primary: '#f59e0b',
    secondary: '#f43f5e',
    darkOpacity: 0.6,
    lightOpacity: 0.38,
  },
  emerald: {
    name: 'Aurora Emerald',
    primary: '#10b981',
    secondary: '#06b6d4',
    darkOpacity: 0.65,
    lightOpacity: 0.4,
  },
  monochrome: {
    name: 'Pure Aura',
    primary: '#ffffff',
    secondary: '#94a3b8',
    darkOpacity: 0.5,
    lightOpacity: 0.3,
  },
};

export const computeBoxLightGradient = (config: BoxLightConfig): string => {
  const hexToRgb = (hex: string) => {
    const clean = hex.replace('#', '');
    if (clean.length === 3) {
      return {
        r: parseInt(clean[0] + clean[0], 16),
        g: parseInt(clean[1] + clean[1], 16),
        b: parseInt(clean[2] + clean[2], 16),
      };
    }
    return {
      r: parseInt(clean.substring(0, 2), 16) || 99,
      g: parseInt(clean.substring(2, 4), 16) || 102,
      b: parseInt(clean.substring(4, 6), 16) || 241,
    };
  };

  const p = hexToRgb(config.primaryColor);
  const s = hexToRgb(config.secondaryColor);

  const shapeStr =
    config.shape === 'ellipse' ? 'ellipse 100% 100% at 50% 50%' : 'circle closest-side at 50% 50%';

  return `radial-gradient(${shapeStr}, rgba(${p.r}, ${p.g}, ${p.b}, 0.85) ${config.innerCore}%, rgba(${s.r}, ${s.g}, ${s.b}, 0.45) ${config.midSpread}%, transparent ${config.outerCutoff}%)`;
};

export const applyStoredTunerConfigToDom = () => {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  try {
    const gridSaved = localStorage.getItem('raise_grid_config');
    if (gridSaved) {
      const cfg: GridConfig = {
        ...DEFAULT_GRID_CONFIG,
        ...(JSON.parse(gridSaved) as Partial<GridConfig>),
      };
      const shapePart =
        cfg.shape === 'circle'
          ? cfg.useClosestSide
            ? `circle closest-side at ${cfg.centerX}% ${cfg.centerY}%`
            : `circle ${cfg.radiusX}% at ${cfg.centerX}% ${cfg.centerY}%`
          : `ellipse ${cfg.radiusX}% ${cfg.radiusY}% at ${cfg.centerX}% ${cfg.centerY}%`;
      const intermediate = Math.round((cfg.fadeMid + cfg.outerCutoff) / 2);
      const maskString = `radial-gradient(${shapePart}, #000 ${cfg.innerCore}%, rgba(0, 0, 0, 0.75) ${cfg.fadeMid}%, rgba(0, 0, 0, 0.2) ${intermediate}%, transparent ${cfg.outerCutoff}%)`;

      const root = document.documentElement;
      root.style.setProperty('--grid-mask', maskString);
      root.style.setProperty('--grid-dot-size', `${cfg.dotSize}px`);
      root.style.setProperty('--grid-spacing', `${cfg.spacing}px`);
      root.style.setProperty('--grid-dot-color', `rgba(15, 23, 42, ${cfg.opacityLight})`);
      root.style.setProperty('--grid-dot-color-dark', `rgba(255, 255, 255, ${cfg.opacityDark})`);
    }

    const boxLightSaved = localStorage.getItem('raise_box_light_config');
    if (boxLightSaved) {
      const cfg: BoxLightConfig = {
        ...DEFAULT_BOX_LIGHT_CONFIG,
        ...(JSON.parse(boxLightSaved) as Partial<BoxLightConfig>),
      };
      const gradient = computeBoxLightGradient(cfg);
      const root = document.documentElement;
      root.style.setProperty('--box-light-primary', cfg.primaryColor);
      root.style.setProperty('--box-light-secondary', cfg.secondaryColor);
      root.style.setProperty('--box-light-width', `${cfg.spreadX}%`);
      root.style.setProperty('--box-light-height', `${cfg.spreadY}%`);
      root.style.setProperty('--box-light-offset-x', `${cfg.offsetX}px`);
      root.style.setProperty('--box-light-offset-y', `${cfg.offsetY}px`);
      root.style.setProperty('--box-light-blur', `${cfg.blur}px`);
      root.style.setProperty('--box-light-opacity-light', `${cfg.opacityLight}`);
      root.style.setProperty('--box-light-opacity-dark', `${cfg.opacityDark}`);
      root.style.setProperty('--box-light-gradient', gradient);
      if (cfg.pulse) {
        root.style.setProperty(
          '--box-light-animation',
          'boxLightBreathe 4s ease-in-out infinite alternate'
        );
      } else {
        root.style.setProperty('--box-light-animation', 'none');
      }
    }
  } catch {}
};

export interface GridGradientTunerProps {
  embedded?: boolean;
  defaultTab?: 'grid' | 'light';
  onSaveAndClose?: () => void;
  onBackToSettings?: () => void;
  onClose?: () => void;
}

export const GridGradientTuner: React.FC<GridGradientTunerProps> = ({
  embedded = false,
  defaultTab = 'grid',
  onSaveAndClose,
  onBackToSettings,
  onClose,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'grid' | 'light'>(defaultTab);
  const [copied, setCopied] = useState(false);

  const handleSaveAndClose = () => {
    try {
      localStorage.setItem('raise_grid_config', JSON.stringify(gridConfig));
      localStorage.setItem('raise_box_light_config', JSON.stringify(boxLightConfig));
    } catch {}
    if (onSaveAndClose) {
      onSaveAndClose();
    } else {
      setIsOpen(false);
    }
  };

  // Grid Config
  const [gridConfig, setGridConfig] = useState<GridConfig>(() => {
    try {
      const saved = localStorage.getItem('raise_grid_config');
      if (saved) {
        return { ...DEFAULT_GRID_CONFIG, ...(JSON.parse(saved) as Partial<GridConfig>) };
      }
    } catch {}
    return DEFAULT_GRID_CONFIG;
  });

  // Box Light Config
  const [boxLightConfig, setBoxLightConfig] = useState<BoxLightConfig>(() => {
    try {
      const saved = localStorage.getItem('raise_box_light_config');
      if (saved) {
        return { ...DEFAULT_BOX_LIGHT_CONFIG, ...(JSON.parse(saved) as Partial<BoxLightConfig>) };
      }
    } catch {}
    return DEFAULT_BOX_LIGHT_CONFIG;
  });

  // Grid mask computation
  const maskString = useMemo(() => {
    const shapePart =
      gridConfig.shape === 'circle'
        ? gridConfig.useClosestSide
          ? `circle closest-side at ${gridConfig.centerX}% ${gridConfig.centerY}%`
          : `circle ${gridConfig.radiusX}% at ${gridConfig.centerX}% ${gridConfig.centerY}%`
        : `ellipse ${gridConfig.radiusX}% ${gridConfig.radiusY}% at ${gridConfig.centerX}% ${gridConfig.centerY}%`;

    const intermediate = Math.round((gridConfig.fadeMid + gridConfig.outerCutoff) / 2);

    return `radial-gradient(${shapePart}, #000 ${gridConfig.innerCore}%, rgba(0, 0, 0, 0.75) ${gridConfig.fadeMid}%, rgba(0, 0, 0, 0.2) ${intermediate}%, transparent ${gridConfig.outerCutoff}%)`;
  }, [gridConfig]);

  // Apply grid config to CSS variables
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--grid-mask', maskString);
    root.style.setProperty('--grid-dot-size', `${gridConfig.dotSize}px`);
    root.style.setProperty('--grid-spacing', `${gridConfig.spacing}px`);
    root.style.setProperty('--grid-dot-color', `rgba(15, 23, 42, ${gridConfig.opacityLight})`);
    root.style.setProperty(
      '--grid-dot-color-dark',
      `rgba(255, 255, 255, ${gridConfig.opacityDark})`
    );

    try {
      localStorage.setItem('raise_grid_config', JSON.stringify(gridConfig));
    } catch {}
  }, [gridConfig, maskString]);

  // Apply box light config to CSS variables
  useEffect(() => {
    const root = document.documentElement;
    const gradient = computeBoxLightGradient(boxLightConfig);

    root.style.setProperty('--box-light-primary', boxLightConfig.primaryColor);
    root.style.setProperty('--box-light-secondary', boxLightConfig.secondaryColor);
    root.style.setProperty('--box-light-width', `${boxLightConfig.spreadX}%`);
    root.style.setProperty('--box-light-height', `${boxLightConfig.spreadY}%`);
    root.style.setProperty('--box-light-offset-x', `${boxLightConfig.offsetX}px`);
    root.style.setProperty('--box-light-offset-y', `${boxLightConfig.offsetY}px`);
    root.style.setProperty('--box-light-blur', `${boxLightConfig.blur}px`);
    root.style.setProperty('--box-light-opacity-light', `${boxLightConfig.opacityLight}`);
    root.style.setProperty('--box-light-opacity-dark', `${boxLightConfig.opacityDark}`);
    root.style.setProperty('--box-light-gradient', gradient);

    // If tuner is open on light tab, preview light in active conversation too
    const showInActiveChat =
      !boxLightConfig.showOnlyNewChat || ((isOpen || embedded) && activeTab === 'light');
    root.style.setProperty('--box-light-active-chat-display', showInActiveChat ? 'block' : 'none');

    // Breathing pulse animation
    if (boxLightConfig.pulse) {
      root.style.setProperty(
        '--box-light-animation',
        'boxLightBreathe 4s ease-in-out infinite alternate'
      );
    } else {
      root.style.setProperty('--box-light-animation', 'none');
    }

    try {
      localStorage.setItem('raise_box_light_config', JSON.stringify(boxLightConfig));
    } catch {}
  }, [boxLightConfig, isOpen, activeTab, embedded]);

  const handleReset = () => {
    if (activeTab === 'grid') {
      setGridConfig(DEFAULT_GRID_CONFIG);
    } else {
      setBoxLightConfig(DEFAULT_BOX_LIGHT_CONFIG);
    }
  };

  const handleCopyCSS = () => {
    let cssCode = '';
    if (activeTab === 'grid') {
      cssCode = `/* Generated Dotted Grid Configuration */
.bg-dot-pattern::before {
  background-size: ${gridConfig.spacing}px ${gridConfig.spacing}px;
  -webkit-mask-image: ${maskString};
  mask-image: ${maskString};
}

/* Dot sizing & contrast */
:root {
  --grid-dot-size: ${gridConfig.dotSize}px;
  --grid-dot-color: rgba(15, 23, 42, ${gridConfig.opacityLight});
  --grid-dot-color-dark: rgba(255, 255, 255, ${gridConfig.opacityDark});
}`;
    } else {
      const gradient = computeBoxLightGradient(boxLightConfig);
      cssCode = `/* Generated Box Light Glow Configuration */
.query-aura-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(calc(-50% + ${boxLightConfig.offsetX}px), calc(-50% + ${boxLightConfig.offsetY}px));
  width: ${boxLightConfig.spreadX}%;
  height: ${boxLightConfig.spreadY}%;
  border-radius: 9999px;
  pointer-events: none;
  z-index: 0;
  background: ${gradient};
  filter: blur(${boxLightConfig.blur}px);
  opacity: ${boxLightConfig.opacityDark};
}

html:not(.dark) .query-aura-glow,
html.light .query-aura-glow {
  opacity: ${boxLightConfig.opacityLight};
}

/* Sizing & contrast variables */
:root {
  --box-light-width: ${boxLightConfig.spreadX}%;
  --box-light-height: ${boxLightConfig.spreadY}%;
  --box-light-offset-x: ${boxLightConfig.offsetX}px;
  --box-light-offset-y: ${boxLightConfig.offsetY}px;
  --box-light-blur: ${boxLightConfig.blur}px;
  --box-light-opacity-dark: ${boxLightConfig.opacityDark};
  --box-light-opacity-light: ${boxLightConfig.opacityLight};
}`;
    }

    navigator.clipboard.writeText(cssCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleApplyPreset = (presetKey: keyof typeof BOX_LIGHT_PRESETS) => {
    const p = BOX_LIGHT_PRESETS[presetKey];
    setBoxLightConfig((prev) => ({
      ...prev,
      preset: presetKey,
      primaryColor: p.primary,
      secondaryColor: p.secondary,
      opacityDark: p.darkOpacity,
      opacityLight: p.lightOpacity,
    }));
  };

  const renderContent = () => (
    <>
      {/* Header */}
      <div className="px-3.5 sm:px-4 py-2.5 sm:py-3 border-b border-slate-200 dark:border-white/10 flex items-center justify-between bg-slate-50/80 dark:bg-white/[0.02] shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          {onBackToSettings && (
            <button
              type="button"
              onClick={onBackToSettings}
              className="p-1 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-200/60 dark:hover:bg-white/10 rounded-md transition-colors cursor-pointer shrink-0"
              title="Back to Settings"
              aria-label="Back to Settings"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          )}
          <span
            className={`w-2.5 h-2.5 rounded-full shrink-0 ${activeTab === 'grid' ? 'bg-indigo-500' : 'bg-amber-500'}`}
          />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white truncate">
            {activeTab === 'grid' ? 'Grid Gradient Tuner' : 'Box Light Glow Tuner'}
          </h3>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={handleReset}
            className="px-2 py-1 text-[11px] font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-white/10 rounded-md transition-colors cursor-pointer"
            title="Reset active tab to defaults"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={handleSaveAndClose}
            className="px-2.5 py-1 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition-colors cursor-pointer flex items-center gap-1 shadow-xs active:scale-95"
            title="Save changes and close tuner"
            aria-label="Save changes and close tuner"
          >
            <svg
              className="w-3 h-3 text-white"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              viewBox="0 0 24 24"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <span>OK</span>
          </button>
          {(onClose || !embedded) && (
            <button
              type="button"
              onClick={() => {
                if (onClose) onClose();
                else setIsOpen(false);
              }}
              className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-white/10 rounded-md transition-colors cursor-pointer"
              title="Close tuner"
              aria-label="Close tuner"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Tab Selector */}
      <div className="flex border-b border-slate-200 dark:border-white/10 bg-slate-100/70 dark:bg-white/[0.03]">
        <button
          type="button"
          onClick={() => setActiveTab('grid')}
          className={`flex-1 py-2 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer border-b-2 ${
            activeTab === 'grid'
              ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400 bg-white dark:bg-white/5'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <svg
            className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
            />
          </svg>
          <span>Grid Pattern</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('light')}
          className={`flex-1 py-2 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer border-b-2 ${
            activeTab === 'light'
              ? 'border-amber-500 text-amber-600 dark:border-amber-400 dark:text-amber-400 bg-white dark:bg-white/5'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          <svg
            className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <span>Box Light Glow</span>
        </button>
      </div>

      {/* Scrollable Body */}
      <div
        className="flex-1 overflow-y-auto max-h-[calc(85vh-7.5rem)]"
        style={{ scrollbarWidth: 'thin' }}
      >
        {/* Tab Content: Box Light Glow */}
        {activeTab === 'light' ? (
          <div className="p-4 space-y-3.5 text-xs text-slate-700 dark:text-slate-300">
            {/* Color Presets */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wider">
                Color Themes
              </label>
              <div className="grid grid-cols-3 gap-1.5">
                {(['indigo', 'cyan', 'amber', 'emerald', 'monochrome'] as const).map((key) => {
                  const preset = BOX_LIGHT_PRESETS[key];
                  const isSelected = boxLightConfig.preset === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => handleApplyPreset(key)}
                      className={`px-2 py-1.5 rounded-lg border text-center font-medium transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                        isSelected
                          ? 'bg-amber-50/80 dark:bg-amber-500/15 border-amber-500 text-amber-700 dark:text-amber-300 font-semibold shadow-2xs'
                          : 'border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 text-slate-600 dark:text-slate-400'
                      }`}
                    >
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{
                          background: `linear-gradient(135deg, ${preset.primary}, ${preset.secondary})`,
                        }}
                      />
                      <span className="truncate text-[10px]">{preset.name.split(' ')[0]}</span>
                    </button>
                  );
                })}
                <button
                  type="button"
                  onClick={() => setBoxLightConfig((p) => ({ ...p, preset: 'custom' }))}
                  className={`px-2 py-1.5 rounded-lg border text-center font-medium transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                    boxLightConfig.preset === 'custom'
                      ? 'bg-amber-50/80 dark:bg-amber-500/15 border-amber-500 text-amber-700 dark:text-amber-300 font-semibold shadow-2xs'
                      : 'border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  <span className="w-2.5 h-2.5 rounded-full bg-gradient-to-tr from-pink-500 via-purple-500 to-indigo-500 shrink-0" />
                  <span className="text-[10px]">Custom</span>
                </button>
              </div>
            </div>

            {/* Custom Color Pickers */}
            <div className="grid grid-cols-2 gap-2 p-2 rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200/80 dark:border-white/10">
              <div>
                <span className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-1">
                  Primary Core Color
                </span>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={boxLightConfig.primaryColor}
                    onChange={(e) =>
                      setBoxLightConfig((p) => ({
                        ...p,
                        preset: 'custom',
                        primaryColor: e.target.value,
                      }))
                    }
                    className="w-6 h-6 rounded cursor-pointer border-0 bg-transparent"
                  />
                  <span className="font-mono text-[11px] text-slate-800 dark:text-slate-200 uppercase">
                    {boxLightConfig.primaryColor}
                  </span>
                </div>
              </div>

              <div>
                <span className="block text-[10px] font-medium text-slate-500 dark:text-slate-400 mb-1">
                  Secondary Accent Color
                </span>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={boxLightConfig.secondaryColor}
                    onChange={(e) =>
                      setBoxLightConfig((p) => ({
                        ...p,
                        preset: 'custom',
                        secondaryColor: e.target.value,
                      }))
                    }
                    className="w-6 h-6 rounded cursor-pointer border-0 bg-transparent"
                  />
                  <span className="font-mono text-[11px] text-slate-800 dark:text-slate-200 uppercase">
                    {boxLightConfig.secondaryColor}
                  </span>
                </div>
              </div>
            </div>

            {/* Light Shape */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wider">
                Glow Shape
              </label>
              <div className="grid grid-cols-2 gap-1.5 p-0.5 bg-slate-100 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/10">
                <button
                  type="button"
                  onClick={() => setBoxLightConfig((p) => ({ ...p, shape: 'ellipse' }))}
                  className={`py-1 text-center rounded-md font-medium transition-all cursor-pointer ${
                    boxLightConfig.shape === 'ellipse'
                      ? 'bg-white dark:bg-amber-600 text-slate-900 dark:text-white shadow-xs font-semibold'
                      : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                  }`}
                >
                  Elliptical Aura
                </button>
                <button
                  type="button"
                  onClick={() => setBoxLightConfig((p) => ({ ...p, shape: 'circle' }))}
                  className={`py-1 text-center rounded-md font-medium transition-all cursor-pointer ${
                    boxLightConfig.shape === 'circle'
                      ? 'bg-white dark:bg-amber-600 text-slate-900 dark:text-white shadow-xs font-semibold'
                      : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                  }`}
                >
                  Circular Beam
                </button>
              </div>
            </div>

            {/* Spread Dimensions: Horizontal & Vertical */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span>Width (Spread X)</span>
                  <span className="font-mono text-amber-600 dark:text-amber-400">
                    {boxLightConfig.spreadX}%
                  </span>
                </div>
                <input
                  type="range"
                  min="80"
                  max="180"
                  step="5"
                  value={boxLightConfig.spreadX}
                  onChange={(e) =>
                    setBoxLightConfig((p) => ({ ...p, spreadX: Number(e.target.value) }))
                  }
                  className="w-full accent-amber-600 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span>Height (Spread Y)</span>
                  <span className="font-mono text-amber-600 dark:text-amber-400">
                    {boxLightConfig.spreadY}%
                  </span>
                </div>
                <input
                  type="range"
                  min="60"
                  max="220"
                  step="5"
                  value={boxLightConfig.spreadY}
                  onChange={(e) =>
                    setBoxLightConfig((p) => ({ ...p, spreadY: Number(e.target.value) }))
                  }
                  className="w-full accent-amber-600 cursor-pointer"
                />
              </div>
            </div>

            {/* Position Offsets: Center X & Center Y */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span>Offset X</span>
                  <span className="font-mono text-amber-600 dark:text-amber-400">
                    {boxLightConfig.offsetX}px
                  </span>
                </div>
                <input
                  type="range"
                  min="-80"
                  max="80"
                  step="2"
                  value={boxLightConfig.offsetX}
                  onChange={(e) =>
                    setBoxLightConfig((p) => ({ ...p, offsetX: Number(e.target.value) }))
                  }
                  className="w-full accent-amber-600 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span>Offset Y</span>
                  <span className="font-mono text-amber-600 dark:text-amber-400">
                    {boxLightConfig.offsetY}px
                  </span>
                </div>
                <input
                  type="range"
                  min="-80"
                  max="80"
                  step="2"
                  value={boxLightConfig.offsetY}
                  onChange={(e) =>
                    setBoxLightConfig((p) => ({ ...p, offsetY: Number(e.target.value) }))
                  }
                  className="w-full accent-amber-600 cursor-pointer"
                />
              </div>
            </div>

            {/* Blur Softness */}
            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span>Blur Softness</span>
                <span className="font-mono text-amber-600 dark:text-amber-400">
                  {boxLightConfig.blur}px
                </span>
              </div>
              <input
                type="range"
                min="10"
                max="120"
                step="2"
                value={boxLightConfig.blur}
                onChange={(e) => setBoxLightConfig((p) => ({ ...p, blur: Number(e.target.value) }))}
                className="w-full accent-amber-600 cursor-pointer"
              />
            </div>

            {/* Core & Boundary Falloff */}
            <div className="grid grid-cols-3 gap-1.5">
              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span>Core</span>
                  <span className="font-mono text-amber-600 dark:text-amber-400">
                    {boxLightConfig.innerCore}%
                  </span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="40"
                  step="5"
                  value={boxLightConfig.innerCore}
                  onChange={(e) =>
                    setBoxLightConfig((p) => ({ ...p, innerCore: Number(e.target.value) }))
                  }
                  className="w-full accent-amber-600 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span>Mid</span>
                  <span className="font-mono text-amber-600 dark:text-amber-400">
                    {boxLightConfig.midSpread}%
                  </span>
                </div>
                <input
                  type="range"
                  min="30"
                  max="75"
                  step="5"
                  value={boxLightConfig.midSpread}
                  onChange={(e) =>
                    setBoxLightConfig((p) => ({ ...p, midSpread: Number(e.target.value) }))
                  }
                  className="w-full accent-amber-600 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span>Cutoff</span>
                  <span className="font-mono text-amber-600 dark:text-amber-400">
                    {boxLightConfig.outerCutoff}%
                  </span>
                </div>
                <input
                  type="range"
                  min="70"
                  max="100"
                  step="5"
                  value={boxLightConfig.outerCutoff}
                  onChange={(e) =>
                    setBoxLightConfig((p) => ({ ...p, outerCutoff: Number(e.target.value) }))
                  }
                  className="w-full accent-amber-600 cursor-pointer"
                />
              </div>
            </div>

            {/* Opacities: Light & Dark Mode */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span>Light Mode Opacity</span>
                  <span className="font-mono text-amber-600 dark:text-amber-400">
                    {boxLightConfig.opacityLight}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.90"
                  step="0.02"
                  value={boxLightConfig.opacityLight}
                  onChange={(e) =>
                    setBoxLightConfig((p) => ({ ...p, opacityLight: Number(e.target.value) }))
                  }
                  className="w-full accent-amber-600 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span>Dark Mode Opacity</span>
                  <span className="font-mono text-amber-600 dark:text-amber-400">
                    {boxLightConfig.opacityDark}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="1.00"
                  step="0.02"
                  value={boxLightConfig.opacityDark}
                  onChange={(e) =>
                    setBoxLightConfig((p) => ({ ...p, opacityDark: Number(e.target.value) }))
                  }
                  className="w-full accent-amber-600 cursor-pointer"
                />
              </div>
            </div>

            {/* Toggles: Breathing Pulse & Show Only New Chat */}
            <div className="space-y-2 pt-1">
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200/80 dark:border-white/10">
                <div className="flex items-center gap-1.5">
                  <span
                    className={`w-2 h-2 rounded-full ${boxLightConfig.pulse ? 'bg-amber-500 animate-ping' : 'bg-slate-400'}`}
                  />
                  <span className="text-[11px] font-medium text-slate-700 dark:text-slate-300">
                    Breathing Pulse Animation
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={boxLightConfig.pulse}
                  onChange={(e) => setBoxLightConfig((p) => ({ ...p, pulse: e.target.checked }))}
                  className="rounded border-slate-300 dark:border-white/20 bg-white dark:bg-white/10 text-amber-600 focus:ring-0 cursor-pointer"
                />
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200/80 dark:border-white/10">
                <span className="text-[11px] font-medium text-slate-700 dark:text-slate-300">
                  Show only in New Chat (Recommended)
                </span>
                <input
                  type="checkbox"
                  checked={boxLightConfig.showOnlyNewChat}
                  onChange={(e) =>
                    setBoxLightConfig((p) => ({ ...p, showOnlyNewChat: e.target.checked }))
                  }
                  className="rounded border-slate-300 dark:border-white/20 bg-white dark:bg-white/10 text-amber-600 focus:ring-0 cursor-pointer"
                />
              </div>
            </div>
          </div>
        ) : (
          /* Tab Content: Grid Pattern */
          <div className="p-4 space-y-3.5 text-xs text-slate-700 dark:text-slate-300">
            {/* Pattern Shape Selection */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1.5 uppercase tracking-wider">
                Pattern Shape
              </label>
              <div className="grid grid-cols-2 gap-1.5 p-0.5 bg-slate-100 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/10">
                <button
                  type="button"
                  onClick={() => setGridConfig((p) => ({ ...p, shape: 'circle' }))}
                  className={`py-1 text-center rounded-md font-medium transition-all cursor-pointer ${
                    gridConfig.shape === 'circle'
                      ? 'bg-white dark:bg-indigo-600 text-slate-900 dark:text-white shadow-xs font-semibold'
                      : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                  }`}
                >
                  Circular Pattern
                </button>
                <button
                  type="button"
                  onClick={() => setGridConfig((p) => ({ ...p, shape: 'ellipse' }))}
                  className={`py-1 text-center rounded-md font-medium transition-all cursor-pointer ${
                    gridConfig.shape === 'ellipse'
                      ? 'bg-white dark:bg-indigo-600 text-slate-900 dark:text-white shadow-xs font-semibold'
                      : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                  }`}
                >
                  Elliptical Pattern
                </button>
              </div>
            </div>

            {/* Circle Sizing Mode */}
            {gridConfig.shape === 'circle' && (
              <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200/80 dark:border-white/10">
                <span className="text-[11px] font-medium text-slate-700 dark:text-slate-300">
                  Fit Closest Boundary (Auto)
                </span>
                <input
                  type="checkbox"
                  checked={gridConfig.useClosestSide}
                  onChange={(e) =>
                    setGridConfig((p) => ({ ...p, useClosestSide: e.target.checked }))
                  }
                  className="rounded border-slate-300 dark:border-white/20 bg-white dark:bg-white/10 text-indigo-600 focus:ring-0 cursor-pointer"
                />
              </div>
            )}

            {/* Center X */}
            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span>Center X Position</span>
                <span className="font-mono text-indigo-600 dark:text-indigo-400">
                  {gridConfig.centerX}%
                </span>
              </div>
              <input
                type="range"
                min="20"
                max="80"
                value={gridConfig.centerX}
                onChange={(e) => setGridConfig((p) => ({ ...p, centerX: Number(e.target.value) }))}
                className="w-full accent-indigo-600 cursor-pointer"
              />
            </div>

            {/* Center Y */}
            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span>Center Y Position</span>
                <span className="font-mono text-indigo-600 dark:text-indigo-400">
                  {gridConfig.centerY}%
                </span>
              </div>
              <input
                type="range"
                min="20"
                max="80"
                value={gridConfig.centerY}
                onChange={(e) => setGridConfig((p) => ({ ...p, centerY: Number(e.target.value) }))}
                className="w-full accent-indigo-600 cursor-pointer"
              />
            </div>

            {/* Radius / Spread Slider */}
            {(!gridConfig.useClosestSide || gridConfig.shape === 'ellipse') && (
              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span>
                    {gridConfig.shape === 'circle' ? 'Circle Radius' : 'Horizontal Radius (X)'}
                  </span>
                  <span className="font-mono text-indigo-600 dark:text-indigo-400">
                    {gridConfig.radiusX}%
                  </span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="90"
                  value={gridConfig.radiusX}
                  onChange={(e) =>
                    setGridConfig((p) => ({ ...p, radiusX: Number(e.target.value) }))
                  }
                  className="w-full accent-indigo-600 cursor-pointer"
                />
              </div>
            )}

            {gridConfig.shape === 'ellipse' && (
              <div>
                <div className="flex justify-between text-[11px] mb-1">
                  <span>Vertical Radius (Y)</span>
                  <span className="font-mono text-indigo-600 dark:text-indigo-400">
                    {gridConfig.radiusY}%
                  </span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="90"
                  value={gridConfig.radiusY}
                  onChange={(e) =>
                    setGridConfig((p) => ({ ...p, radiusY: Number(e.target.value) }))
                  }
                  className="w-full accent-indigo-600 cursor-pointer"
                />
              </div>
            )}

            {/* Inner Core (100% Visibility Zone) */}
            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span>Center Peak Opacity Zone</span>
                <span className="font-mono text-indigo-600 dark:text-indigo-400">
                  {gridConfig.innerCore}%
                </span>
              </div>
              <input
                type="range"
                min="10"
                max="65"
                value={gridConfig.innerCore}
                onChange={(e) =>
                  setGridConfig((p) => ({ ...p, innerCore: Number(e.target.value) }))
                }
                className="w-full accent-indigo-600 cursor-pointer"
              />
            </div>

            {/* Edge Fade Cutoff (Where dots reach 0% opacity) */}
            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span>Boundary Cutoff (0% Dots)</span>
                <span className="font-mono text-indigo-600 dark:text-indigo-400">
                  {gridConfig.outerCutoff}%
                </span>
              </div>
              <input
                type="range"
                min="60"
                max="100"
                value={gridConfig.outerCutoff}
                onChange={(e) =>
                  setGridConfig((p) => ({ ...p, outerCutoff: Number(e.target.value) }))
                }
                className="w-full accent-indigo-600 cursor-pointer"
              />
            </div>

            {/* Dot Size */}
            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span>Dot Diameter</span>
                <span className="font-mono text-indigo-600 dark:text-indigo-400">
                  {gridConfig.dotSize}px
                </span>
              </div>
              <input
                type="range"
                min="1.0"
                max="3.0"
                step="0.1"
                value={gridConfig.dotSize}
                onChange={(e) => setGridConfig((p) => ({ ...p, dotSize: Number(e.target.value) }))}
                className="w-full accent-indigo-600 cursor-pointer"
              />
            </div>

            {/* Grid Spacing */}
            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span>Grid Spacing</span>
                <span className="font-mono text-indigo-600 dark:text-indigo-400">
                  {gridConfig.spacing}px
                </span>
              </div>
              <input
                type="range"
                min="16"
                max="40"
                step="2"
                value={gridConfig.spacing}
                onChange={(e) => setGridConfig((p) => ({ ...p, spacing: Number(e.target.value) }))}
                className="w-full accent-indigo-600 cursor-pointer"
              />
            </div>

            {/* Contrast / Opacity Sliders */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span>Light Opacity</span>
                  <span className="font-mono text-indigo-600 dark:text-indigo-400">
                    {gridConfig.opacityLight}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="0.8"
                  step="0.02"
                  value={gridConfig.opacityLight}
                  onChange={(e) =>
                    setGridConfig((p) => ({ ...p, opacityLight: Number(e.target.value) }))
                  }
                  className="w-full accent-indigo-600 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-[10px] mb-1">
                  <span>Dark Opacity</span>
                  <span className="font-mono text-indigo-600 dark:text-indigo-400">
                    {gridConfig.opacityDark}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="0.9"
                  step="0.02"
                  value={gridConfig.opacityDark}
                  onChange={(e) =>
                    setGridConfig((p) => ({ ...p, opacityDark: Number(e.target.value) }))
                  }
                  className="w-full accent-indigo-600 cursor-pointer"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer Action */}
      <div className="px-3.5 sm:px-4 py-2.5 sm:py-3 border-t border-slate-200 dark:border-white/10 bg-slate-50/80 dark:bg-white/[0.02] flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[10.5px] text-slate-500 dark:text-slate-400 truncate">
            {activeTab === 'light' ? 'Light glow live' : 'Grid pattern live'}
          </span>
          <button
            type="button"
            onClick={handleCopyCSS}
            className="px-2.5 py-1 text-[11px] rounded-lg border border-slate-300 dark:border-white/15 bg-white dark:bg-white/5 hover:bg-slate-100 dark:hover:bg-white/10 text-slate-700 dark:text-slate-300 font-medium flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer active:scale-95 shrink-0"
            title="Copy CSS code"
          >
            {copied ? (
              <>
                <svg
                  className="w-3 h-3 text-emerald-600 dark:text-emerald-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2.5"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                <span>Copied!</span>
              </>
            ) : (
              <>
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
                  />
                </svg>
                <span>Copy CSS</span>
              </>
            )}
          </button>
        </div>

        <button
          type="button"
          onClick={handleSaveAndClose}
          className="px-4 py-1.5 rounded-lg active:scale-95 text-white text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500 flex items-center gap-1.5 transition-all shadow-sm cursor-pointer shrink-0"
          title="Save changes and close tuner"
          aria-label="Save changes and close tuner"
        >
          <svg
            className="w-3.5 h-3.5 text-white"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            viewBox="0 0 24 24"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span>OK</span>
        </button>
      </div>
    </>
  );

  // When embedded inside Settings
  if (embedded) {
    return <div className="w-full h-full flex flex-col overflow-hidden">{renderContent()}</div>;
  }

  // Floating dock mode
  return (
    <div className="fixed bottom-4 right-4 z-50 select-none font-sans">
      {!isOpen ? (
        <div className="flex items-center gap-1.5 p-1 bg-white/95 dark:bg-[#181b26]/95 border border-slate-300/80 dark:border-white/15 rounded-full shadow-xl backdrop-blur-xl transition-all">
          {/* Grid Tuner Button */}
          <button
            type="button"
            onClick={() => {
              setActiveTab('grid');
              setIsOpen(true);
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-white/10 text-slate-700 dark:text-slate-200 hover:text-slate-950 dark:hover:text-white transition-all cursor-pointer active:scale-95 text-xs font-medium"
            title="Customize Background Dotted Grid Gradient"
            aria-label="Customize Background Dotted Grid Gradient"
          >
            <span className="w-2 h-2 rounded-full bg-indigo-500" />
            <svg
              className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
              />
            </svg>
            <span>Grid Tuner</span>
          </button>

          <div className="w-px h-4 bg-slate-300 dark:bg-white/15" />

          {/* Box Light Tuner Button */}
          <button
            type="button"
            onClick={() => {
              setActiveTab('light');
              setIsOpen(true);
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-white/10 text-slate-700 dark:text-slate-200 hover:text-slate-950 dark:hover:text-white transition-all cursor-pointer active:scale-95 text-xs font-medium"
            title="Customize Light Glow Behind Question Box"
            aria-label="Customize Light Glow Behind Question Box"
          >
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <svg
              className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
            <span>Box Light</span>
          </button>
        </div>
      ) : (
        <div className="w-84 sm:w-96 max-h-[85vh] bg-white/98 dark:bg-[#14161f]/98 border border-slate-300 dark:border-white/15 rounded-2xl shadow-2xl backdrop-blur-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-150">
          <div className="overflow-y-auto max-h-[85vh]" style={{ scrollbarWidth: 'thin' }}>
            {renderContent()}
          </div>
        </div>
      )}
    </div>
  );
};
