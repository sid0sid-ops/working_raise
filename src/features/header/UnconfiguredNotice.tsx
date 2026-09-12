import React from 'react';
import { settingsJunction } from '../settings/junction';

export interface UnconfiguredNoticeProps {
  isTunnelConfigured: boolean;
  onOpenSettings?: () => void;
}

export const UnconfiguredNotice: React.FC<UnconfiguredNoticeProps> = ({
  isTunnelConfigured,
  onOpenSettings,
}) => {
  if (isTunnelConfigured) return null;

  const handleClick = () => {
    if (onOpenSettings) {
      onOpenSettings();
    } else {
      settingsJunction.open('gateway');
    }
  };

  return (
    <div className="fixed top-14 sm:top-16 left-0 sm:left-16 right-0 z-30 flex justify-center px-[clamp(0.5rem,2vw,1rem)] pt-1 pointer-events-none animate-in fade-in slide-in-from-top-1 duration-200">
      <div
        data-testid="gateway-unconfigured-notice"
        className="pointer-events-auto inline-flex items-center gap-1.5 sm:gap-2 py-1 px-[clamp(0.625rem,2vw,1rem)] rounded-full bg-amber-500/15 dark:bg-amber-950/75 border border-amber-500/30 text-amber-950 dark:text-amber-200 shadow-sm backdrop-blur-md text-[clamp(10px,2.4vw,12px)] max-w-[calc(100vw-1.5rem)] sm:max-w-none text-center sm:text-left"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse shrink-0" />
        <p className="leading-tight truncate sm:whitespace-normal">
          Please go to{' '}
          <button
            type="button"
            aria-label="Open Settings"
            onClick={handleClick}
            className="font-semibold underline hover:text-amber-950 dark:hover:text-white cursor-pointer"
          >
            Settings
          </button>{' '}
          and paste your Pipeline Tunneling URL to connect.
        </p>
      </div>
    </div>
  );
};
