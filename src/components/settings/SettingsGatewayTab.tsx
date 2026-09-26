import { RefreshCw, ThumbsDown, ThumbsUp } from 'lucide-react';
import type React from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { chatService } from '../../services/ChatService';
import { useModeStore } from '../../stores/modeStore';
import type { FeedbackStats } from '../../types';
import { copyMarkdownToClipboard } from '../../utils/exportFormats';
import { getClientSystemAndTime } from '../../utils/formatters';
import {
  formatLastConnected,
  sanitizeTunnelUrl,
  validateTunnelUrl,
} from '../../utils/urlValidation';

export interface SettingsGatewayTabProps {
  onCloseSettings?: () => void;
}

export const SettingsGatewayTab: React.FC<SettingsGatewayTabProps> = () => {
  const {
    appMode,
    apiBaseUrl,
    setBaseUrl,
    gatewayUsername,
    setUsername,
    clearTunnelUrl,
    testConnection,
    isProbing,
    latencyMs,
    lastConnectedAt,
  } = useModeStore();

  const [detectedClient] = useState(getClientSystemAndTime);
  const [urlInput, setUrlInput] = useState(apiBaseUrl);
  const inputRef = useRef<HTMLInputElement>(null);
  const [usernameInput, setUsernameInput] = useState(
    gatewayUsername === 'Operator' || !gatewayUsername ? detectedClient : gatewayUsername
  );
  const [showStatusInfo, setShowStatusInfo] = useState(false);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [currentTime, setCurrentTime] = useState(Date.now());
  const [feedbackStats, setFeedbackStats] = useState<FeedbackStats | null>(null);
  const [isLoadingFeedbackStats, setIsLoadingFeedbackStats] = useState(false);

  const fetchFeedbackStats = async () => {
    setIsLoadingFeedbackStats(true);
    try {
      const res = await chatService.getFeedbackStats?.();
      if (res?.data) {
        setFeedbackStats(res.data);
      }
    } catch {
      // ignore
    } finally {
      setIsLoadingFeedbackStats(false);
    }
  };

  useEffect(() => {
    fetchFeedbackStats();
  }, [apiBaseUrl, appMode]);

  // Periodically refresh relative time display every 15 seconds
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(Date.now()), 15000);
    return () => clearInterval(timer);
  }, []);

  // Synchronize state with store changes
  useEffect(() => {
    setUrlInput(apiBaseUrl);
  }, [apiBaseUrl]);

  useEffect(() => {
    if (gatewayUsername && gatewayUsername !== 'Operator') {
      setUsernameInput(gatewayUsername);
    }
  }, [gatewayUsername]);

  // Real-time URL validation
  const validation = useMemo(() => validateTunnelUrl(urlInput), [urlInput]);

  const handleConnect = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanInput = urlInput.trim();

    // Check if there is an error in URL format
    const currentValidation = validateTunnelUrl(cleanInput);
    if (cleanInput && currentValidation.error) {
      setStatusNotice(currentValidation.error);
      return;
    }

    // Sanitize any trailing slashes or subpaths
    const sanitizedUrl = cleanInput ? sanitizeTunnelUrl(cleanInput) : apiBaseUrl;
    if (cleanInput) {
      setUrlInput(sanitizedUrl);
      setBaseUrl(sanitizedUrl);
    }
    setUsername(usernameInput);

    // Trigger background connection test
    setStatusNotice('Connecting to pipeline...');
    const result = await testConnection(sanitizedUrl || apiBaseUrl);
    if (result.success) {
      setStatusNotice('Connected successfully to pipeline!');
    } else {
      setStatusNotice(result.error || 'Connection attempt failed. Check terminal for details.');
    }
    setTimeout(() => setStatusNotice(null), 4000);
  };

  const handleCopyUrl = async () => {
    const textToCopy = urlInput.trim() || apiBaseUrl;
    if (!textToCopy) return;
    const success = await copyMarkdownToClipboard(textToCopy);
    if (success) {
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    }
  };

  const handlePaste = async () => {
    try {
      if (navigator.clipboard?.readText) {
        const text = await navigator.clipboard.readText();
        if (text && text.trim()) {
          setUrlInput(text.trim());
        }
      }
    } catch {
      // Clipboard permissions denied, fallback to manual paste
    }
  };

  const handleEmptyUrl = () => {
    setUrlInput('');
    clearTunnelUrl();
    inputRef.current?.focus();
  };

  const isConnected = appMode === 'connected';

  return (
    <div className="space-y-5 animate-in fade-in duration-200" data-testid="settings-gateway-tab">
      {/* Header with Status Dot & Info (i) SVG Button */}
      <div className="space-y-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2.5 min-w-0 flex-wrap">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white shrink-0">
              Pipeline Tunnel & Gateway
            </h3>

            {/* Status Dot (Red = Not Connected, Amber = Connecting, Green = Connected) */}
            <span
              data-testid="connection-status-dot"
              className={`relative inline-flex rounded-full h-2.5 w-2.5 shrink-0 transition-colors ${
                isConnected
                  ? 'bg-emerald-500 ring-2 ring-emerald-500/20'
                  : isProbing
                    ? 'bg-amber-500 animate-pulse ring-2 ring-amber-500/20'
                    : 'bg-rose-500 ring-2 ring-rose-500/20'
              }`}
            />

            {/* Last connected: X minutes ago shown next to status dot */}
            <span
              data-testid="last-connected-time"
              className="text-xs text-slate-500 dark:text-slate-400 font-medium shrink-0"
            >
              {formatLastConnected(lastConnectedAt, isConnected, currentTime)}
            </span>

            {/* Info (i) SVG Button: Shows status meaning depending on situation */}
            <button
              type="button"
              data-testid="status-info-toggle-btn"
              onClick={() => setShowStatusInfo((prev) => !prev)}
              aria-label="Connection Status Information"
              title={
                isConnected
                  ? `Connected (${latencyMs}ms) - Click for info`
                  : isProbing
                    ? 'Connecting... - Click for info'
                    : 'Not Connected - Click for info'
              }
              className={`p-1 rounded-lg text-xs flex items-center transition-all cursor-pointer ${
                showStatusInfo
                  ? 'bg-slate-200 dark:bg-white/15 text-slate-900 dark:text-white'
                  : isConnected
                    ? 'text-emerald-500 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/30'
                    : isProbing
                      ? 'text-amber-500 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30'
                      : 'text-rose-500 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30'
              }`}
            >
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
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
            </button>

            {/* Screen reader & test status text: visually hidden so only the dot and (i) button appear next to heading */}
            <span data-testid="connection-status-text" className="sr-only">
              {isProbing ? 'Connecting...' : isConnected ? 'Connected' : 'Not Connected'}
            </span>
          </div>
        </div>

        {/* Dynamic Contextual Status Info (revealed on clicking (i) info icon) */}
        {showStatusInfo && (
          <div
            data-testid="status-info-panel"
            className="p-3 rounded-xl bg-slate-50 dark:bg-[#1c1e24] border border-slate-200/80 dark:border-white/10 text-xs animate-in fade-in duration-150"
          >
            {isConnected ? (
              <div className="flex items-start gap-2 text-emerald-800 dark:text-emerald-300">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1 shrink-0" />
                <div>
                  <p className="font-semibold">Pipeline Connected</p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono mt-0.5 truncate">
                    Active gateway: {apiBaseUrl} ({latencyMs}ms)
                  </p>
                </div>
              </div>
            ) : isProbing ? (
              <div className="flex items-start gap-2 text-amber-800 dark:text-amber-300">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse mt-1 shrink-0" />
                <div>
                  <p className="font-semibold">Connecting to Pipeline</p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                    Probing endpoint {urlInput || apiBaseUrl}...
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-2 text-rose-800 dark:text-rose-300">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500 mt-1 shrink-0" />
                <div>
                  <p className="font-semibold">Pipeline Disconnected</p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                    Paste your Cloudflare Tunnel URL below and click Connect to establish
                    connection.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Connection Notice Banner */}
      {statusNotice && (
        <div
          data-testid="gateway-save-success-banner"
          className={`p-3 rounded-xl text-xs flex items-center gap-2 animate-in fade-in ${
            isConnected
              ? 'bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 text-emerald-800 dark:text-emerald-300'
              : 'bg-slate-100 dark:bg-white/[0.06] border border-slate-200 dark:border-white/10 text-slate-800 dark:text-slate-200'
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${isConnected ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}`}
          />
          <span className="font-medium">{statusNotice}</span>
        </div>
      )}

      {/* 1. Pipeline Tunnel URL Input (with real-time validation & warnings) */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-800 dark:text-slate-200 block">
          Pipeline Tunnel URL
        </label>
        <div className="flex items-center gap-2">
          <div className="relative flex-1 min-w-0">
            <input
              ref={inputRef}
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://xxxx.trycloudflare.com"
              data-testid="gateway-tunnel-url-input"
              className={`w-full text-xs pl-3.5 pr-16 py-2.5 rounded-xl bg-slate-50 dark:bg-[#12141d] border ${
                validation.error
                  ? 'border-rose-400 dark:border-rose-500 focus:ring-rose-500/20 focus:border-rose-500'
                  : validation.warning
                    ? 'border-amber-400 dark:border-amber-500 focus:ring-amber-500/20 focus:border-amber-500'
                    : 'border-slate-200 dark:border-[#37393b] focus:ring-slate-400/30 focus:border-slate-400'
              } text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 font-mono shadow-inner transition-all`}
            />

            {/* Inside-input adaptive controls: X (empty) + Paste icon */}
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5">
              {urlInput.length > 0 && (
                <button
                  type="button"
                  onClick={handleEmptyUrl}
                  title="Clear URL"
                  aria-label="Clear URL"
                  data-testid="gateway-clear-btn"
                  className="p-1 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 hover:bg-slate-200/60 dark:hover:bg-white/10 rounded-md transition-colors cursor-pointer"
                >
                  <svg
                    className="w-3.5 h-3.5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
              <button
                type="button"
                onClick={handlePaste}
                title="Paste from clipboard"
                aria-label="Paste from clipboard"
                data-testid="gateway-paste-url-btn"
                className="p-1 text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-[#a8c7fa] hover:bg-slate-200/60 dark:hover:bg-white/10 rounded-md transition-colors cursor-pointer"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
              </button>
            </div>
          </div>

          {/* Copy URL Button */}
          <button
            type="button"
            onClick={handleCopyUrl}
            disabled={!urlInput.trim()}
            data-testid="gateway-copy-url-btn"
            title={copiedUrl ? 'Copied to clipboard' : 'Copy URL to clipboard'}
            className="px-3 py-2.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 dark:bg-white/[0.08] dark:hover:bg-white/[0.12] text-slate-600 dark:text-slate-300 rounded-xl transition-colors cursor-pointer shrink-0 border border-slate-200 dark:border-[#37393b] flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {copiedUrl ? (
              <>
                <svg
                  className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400 shrink-0"
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
                <span className="text-emerald-600 dark:text-emerald-400 font-medium">Copied</span>
              </>
            ) : (
              <>
                <svg
                  className="w-3.5 h-3.5 shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
                <span className="hidden sm:inline">Copy URL</span>
              </>
            )}
          </button>
        </div>

        {/* Real-time URL format error */}
        {validation.error && (
          <div
            data-testid="gateway-url-error"
            className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 text-xs text-rose-700 dark:text-rose-300 flex items-center justify-between gap-2 animate-in fade-in duration-150"
          >
            <div className="flex items-center gap-1.5 min-w-0">
              <svg
                className="w-3.5 h-3.5 shrink-0 text-rose-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <circle cx="12" cy="12" r="10" strokeWidth="2" />
                <line x1="12" y1="8" x2="12" y2="12" strokeWidth="2" strokeLinecap="round" />
                <line x1="12" y1="16" x2="12.01" y2="16" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <span className="truncate">{validation.error}</span>
            </div>
            {validation.suggestedFix && (
              <button
                type="button"
                data-testid="gateway-url-fix-btn"
                onClick={() => setUrlInput(validation.suggestedFix!)}
                className="underline hover:text-rose-900 dark:hover:text-rose-100 font-medium text-[11px] shrink-0 cursor-pointer"
              >
                Apply https://
              </button>
            )}
          </div>
        )}

        {/* Real-time URL format warning */}
        {!validation.error && validation.warning && (
          <div
            data-testid="gateway-url-warning"
            className="p-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/50 text-xs text-amber-800 dark:text-amber-300 flex items-center justify-between gap-2 animate-in fade-in duration-150"
          >
            <div className="flex items-center gap-1.5 min-w-0">
              <svg
                className="w-3.5 h-3.5 shrink-0 text-amber-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <span className="truncate">{validation.warning}</span>
            </div>
            {validation.suggestedFix && (
              <button
                type="button"
                data-testid="gateway-url-trim-btn"
                onClick={() => setUrlInput(validation.suggestedFix!)}
                className="underline hover:text-amber-950 dark:hover:text-amber-100 font-medium text-[11px] shrink-0 cursor-pointer"
              >
                Trim to base URL
              </button>
            )}
          </div>
        )}
      </div>

      {/* 2. System User and Time (Auto-detected client OS & time) */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold text-slate-800 dark:text-slate-200 block">
          Client System & Time
        </label>
        <input
          type="text"
          value={usernameInput}
          onChange={(e) => setUsernameInput(e.target.value)}
          placeholder={detectedClient}
          data-testid="gateway-username-input"
          className="w-full text-xs px-3.5 py-2.5 rounded-xl bg-slate-50 dark:bg-[#12141d] border border-slate-200 dark:border-[#37393b] text-slate-700 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-400/30 focus:border-slate-400 shadow-inner transition-all font-mono"
        />
      </div>

      {/* 3. Primary Action Button: Connect */}
      <div className="pt-2 flex items-center gap-3">
        <button
          type="button"
          disabled={isProbing || Boolean(validation.error)}
          onClick={() => handleConnect()}
          data-testid="gateway-connect-btn"
          className="py-2.5 px-6 rounded-xl text-xs font-bold bg-white hover:bg-slate-200 text-black transition-all cursor-pointer shadow-sm active:scale-95 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isProbing ? (
            <div className="w-3.5 h-3.5 rounded-full border-2 border-black border-t-transparent animate-spin" />
          ) : (
            <svg
              className={`w-3.5 h-3.5 ${isConnected ? 'text-emerald-600 fill-emerald-600' : 'text-black fill-black'}`}
              stroke="currentColor"
              strokeWidth="2.5"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          )}
          <span>{isProbing ? 'Connecting...' : isConnected ? 'Connected' : 'Connect'}</span>
        </button>
      </div>

      {/* 4. Operator Satisfaction & Telemetry Analytics (Recommendation 4) */}
      <div
        className="pt-4 border-t border-slate-200 dark:border-white/10 space-y-3"
        data-testid="feedback-analytics-widget"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h4 className="text-xs font-semibold text-slate-900 dark:text-white uppercase tracking-wider">
              User Satisfaction & Telemetry
            </h4>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/60 font-semibold">
              /api/feedback/stats
            </span>
          </div>
          <button
            type="button"
            onClick={fetchFeedbackStats}
            disabled={isLoadingFeedbackStats}
            title="Refresh Feedback Stats"
            aria-label="Refresh Feedback Stats"
            className="p-1 rounded-lg text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/10 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingFeedbackStats ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {feedbackStats ? (
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#12141d] border border-slate-200 dark:border-[#37393b] space-y-3">
            {/* Top row: Satisfaction Ratio and Total Reviews */}
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                  Satisfaction Ratio
                </span>
                <div
                  className="text-xl font-bold font-mono text-slate-900 dark:text-white"
                  data-testid="satisfaction-ratio-value"
                >
                  {(feedbackStats.satisfaction_ratio * 100).toFixed(1)}%
                </div>
              </div>
              <div className="text-right">
                <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                  Total Reviews
                </span>
                <div
                  className="text-xl font-bold font-mono text-slate-900 dark:text-white"
                  data-testid="total-feedback-value"
                >
                  {feedbackStats.total_feedback}
                </div>
              </div>
            </div>

            {/* Gauge / Progress Bar */}
            <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2 overflow-hidden flex">
              <div
                className="bg-emerald-500 h-full transition-all duration-500"
                style={{ width: `${Math.round(feedbackStats.satisfaction_ratio * 100)}%` }}
              />
              <div
                className="bg-rose-500 h-full transition-all duration-500"
                style={{ width: `${100 - Math.round(feedbackStats.satisfaction_ratio * 100)}%` }}
              />
            </div>

            {/* Bottom row: Breakdown */}
            <div className="flex items-center justify-between text-xs pt-1">
              <div
                className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-semibold"
                data-testid="thumbs-up-count"
              >
                <ThumbsUp className="w-3.5 h-3.5" />
                <span>{feedbackStats.thumbs_up} helpful</span>
              </div>
              <div
                className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400 font-semibold"
                data-testid="thumbs-down-count"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
                <span>{feedbackStats.thumbs_down} unhelpful</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-3 text-xs text-slate-500 dark:text-slate-400 text-center rounded-xl bg-slate-50 dark:bg-[#12141d] border border-slate-200 dark:border-[#37393b]">
            {isLoadingFeedbackStats
              ? 'Loading satisfaction telemetry...'
              : 'No feedback data recorded yet.'}
          </div>
        )}
      </div>
    </div>
  );
};
