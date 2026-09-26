import type React from 'react';

export interface BackendErrorDetails {
  title: string;
  message: string;
  cause?: string;
  action?: string;
  status?: number;
  isOffline?: boolean;
  isTimeout?: boolean;
  isAborted?: boolean;
}

export interface BackendErrorCardProps {
  error: BackendErrorDetails;
  targetUrl: string;
  onRetry?: () => void;
  onOpenSettings?: () => void;
}

export interface ResponseStoppedBannerProps {
  onRetry?: () => void;
  className?: string;
}

export const ResponseStoppedBanner: React.FC<ResponseStoppedBannerProps> = ({
  onRetry,
  className = '',
}) => {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`response-stopped-banner inline-flex items-center gap-2 py-1.5 px-2.5 rounded-xl bg-slate-100/90 dark:bg-white/[0.04] border border-slate-200/80 dark:border-white/10 text-xs text-slate-600 dark:text-slate-300 select-none animate-in fade-in duration-200 ${className}`}
      data-testid="response-stopped-banner"
    >
      <div className="w-3.5 h-3.5 rounded-full bg-slate-200 dark:bg-white/10 flex items-center justify-center text-slate-500 dark:text-slate-400 shrink-0">
        <div className="w-1.5 h-1.5 rounded-xs bg-slate-600 dark:bg-slate-300" />
      </div>
      <span className="font-medium text-slate-700 dark:text-slate-200">Response stopped.</span>
      {onRetry && (
        <>
          <span className="text-slate-300 dark:text-slate-600">·</span>
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1 font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 hover:underline cursor-pointer"
            aria-label="Retry response"
          >
            <svg
              className="w-3 h-3"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="1 4 1 10 7 10" />
              <polyline points="23 20 23 14 17 14" />
              <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" />
            </svg>
            <span>Retry</span>
          </button>
        </>
      )}
    </div>
  );
};

export const BackendErrorCard: React.FC<BackendErrorCardProps> = ({
  error,
  targetUrl: _targetUrl,
  onRetry,
  onOpenSettings,
}) => {
  const { title, message, cause, action, status, isOffline, isTimeout, isAborted } = error;

  const isUserAbort =
    isAborted ||
    title?.toLowerCase().includes('stopped') ||
    title?.toLowerCase().includes('aborted') ||
    message?.toLowerCase().includes('aborted') ||
    message?.toLowerCase().includes('cancelled locally') ||
    message?.toLowerCase().includes('response stopped');

  if (isUserAbort) {
    return <ResponseStoppedBanner onRetry={onRetry} className="my-1" />;
  }

  // Friendly, calm offline state (non-scary for normal users)
  if (isOffline) {
    return (
      <div
        role="alert"
        className="backend-error-card bg-slate-50/90 dark:bg-white/[0.04] border border-slate-200/90 dark:border-white/10 rounded-xl p-3.5 shadow-2xs transition-all max-w-2xl"
      >
        {/* Header Banner */}
        <div className="flex items-center justify-between gap-3 mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-6 h-6 rounded-lg bg-slate-200/80 dark:bg-white/10 text-slate-600 dark:text-slate-300 flex items-center justify-center shrink-0">
              <svg
                className="w-3.5 h-3.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="1" y1="1" x2="23" y2="23" />
                <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55" />
                <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39" />
                <path d="M10.71 5.05A16 16 0 0 1 22.58 9" />
                <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88" />
                <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
                <line x1="12" y1="20" x2="12.01" y2="20" />
              </svg>
            </div>
            <div className="min-w-0">
              <h3 className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                {title || 'Server is offline'}
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-200/80 dark:bg-white/10 text-slate-600 dark:text-slate-400">
              OFFLINE
            </span>
          </div>
        </div>

        {/* Message */}
        <p className="text-[12px] text-slate-600 dark:text-slate-300 leading-relaxed font-normal mb-2.5">
          {message ||
            'The backend server is currently offline or unreachable. Please check if the server is running.'}
        </p>

        {/* Cause & Action if present */}
        {(cause || action) && (
          <details className="mb-2.5 text-[11px] text-slate-500 dark:text-slate-400">
            <summary className="cursor-pointer hover:underline select-none">
              Technical details
            </summary>
            <div className="mt-1.5 p-2 rounded-lg bg-slate-100/90 dark:bg-white/5 border border-slate-200/80 dark:border-white/10 space-y-1">
              {cause && (
                <div>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Cause: </span>
                  <span>{cause}</span>
                </div>
              )}
              {action && (
                <div>
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Action: </span>
                  <span>{action}</span>
                </div>
              )}
            </div>
          </details>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-2 pt-1.5 border-t border-slate-200/60 dark:border-white/[0.06]">
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              aria-label="Retry query"
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-500 active:scale-95 rounded-lg transition-all cursor-pointer shadow-2xs"
            >
              <svg
                className="w-3 h-3"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="1 4 1 10 7 10" />
                <polyline points="23 20 23 14 17 14" />
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" />
              </svg>
              <span>Retry</span>
            </button>
          )}

          {onOpenSettings && (
            <button
              type="button"
              onClick={onOpenSettings}
              aria-label="Configure Gateway & Tunnel"
              className="px-2.5 py-1 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-white/80 hover:bg-slate-100 dark:bg-white/5 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10 rounded-lg transition-all cursor-pointer"
            >
              Settings
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      role="alert"
      className="backend-error-card bg-rose-50/70 dark:bg-[#1a1219]/90 border border-rose-200/80 dark:border-rose-500/25 rounded-xl p-3.5 shadow-2xs transition-all max-w-2xl"
    >
      {/* Header Banner */}
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-6 h-6 rounded-lg bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 flex items-center justify-center shrink-0">
            {isTimeout ? (
              <svg
                className="w-3.5 h-3.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            ) : (
              <svg
                className="w-3.5 h-3.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            )}
          </div>
          <div className="min-w-0">
            <h3 className="text-xs font-semibold text-rose-950 dark:text-rose-200 truncate">
              {title || 'Pipeline Communication Issue'}
            </h3>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300">
            {isTimeout ? 'TIMEOUT' : status ? `HTTP ${status}` : 'ERROR'}
          </span>
        </div>
      </div>

      {/* Error Message Details */}
      <p className="text-[12px] text-rose-900/90 dark:text-rose-200/90 leading-relaxed font-normal mb-2">
        {message}
      </p>

      {/* Cause & Action if present */}
      {(cause || action) && (
        <div className="p-2.5 bg-white/80 dark:bg-black/30 rounded-lg border border-rose-200/60 dark:border-rose-500/20 text-[11px] space-y-1 mb-2.5">
          {cause && (
            <div className="text-slate-700 dark:text-slate-300">
              <span className="font-semibold text-rose-700 dark:text-rose-400">Cause: </span>
              <span>{cause}</span>
            </div>
          )}
          {action && (
            <div className="text-slate-700 dark:text-slate-300">
              <span className="font-semibold text-emerald-700 dark:text-emerald-400">Action: </span>
              <span>{action}</span>
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-2 pt-1.5 border-t border-rose-200/60 dark:border-white/[0.06]">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            aria-label="Retry query"
            className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-white bg-rose-600 hover:bg-rose-500 active:scale-95 rounded-lg transition-all cursor-pointer shadow-2xs"
          >
            <svg
              className="w-3 h-3"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="1 4 1 10 7 10" />
              <polyline points="23 20 23 14 17 14" />
              <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" />
            </svg>
            <span>Retry Query</span>
          </button>
        )}

        {onOpenSettings && (
          <button
            type="button"
            onClick={onOpenSettings}
            className="px-2.5 py-1 text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-white/80 hover:bg-slate-100 dark:bg-white/5 dark:hover:bg-white/10 border border-slate-200 dark:border-white/10 rounded-lg transition-all cursor-pointer"
          >
            Configure Gateway & Tunnel
          </button>
        )}
      </div>
    </div>
  );
};
