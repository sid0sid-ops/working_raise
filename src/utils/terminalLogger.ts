export interface TerminalLogEvent {
  type: 'REQ' | 'RES' | 'ERR' | 'MOCK' | 'SYSTEM';
  method?: string;
  endpoint: string;
  payload?: any;
  status?: number;
  durationMs?: number;
  message?: string;
  error?: string;
  details?: string;
}

export function logToTerminal(event: TerminalLogEvent) {
  try {
    if (typeof window !== 'undefined') {
      const timeStr = new Date().toLocaleTimeString();
      const prefix = `[PIPELINE]`;

      // 1. Detailed browser console logging with styled badges
      if (event.type === 'REQ') {
        console.log(
          `%c${prefix} REQ %c${event.method || 'GET'} ${event.endpoint} %c(${timeStr})`,
          'background:#2563eb;color:#fff;padding:2px 6px;border-radius:4px;font-weight:bold;font-size:11px;',
          'color:#38bdf8;font-weight:bold;',
          'color:#94a3b8;',
          event.details || event.payload || ''
        );
      } else if (event.type === 'RES') {
        console.log(
          `%c${prefix} RES %c${event.method || ''} ${event.endpoint} %cHTTP ${event.status ?? 200} (${event.durationMs ?? 0}ms)`,
          'background:#16a34a;color:#fff;padding:2px 6px;border-radius:4px;font-weight:bold;font-size:11px;',
          'color:#4ade80;font-weight:bold;',
          'color:#94a3b8;',
          event.details || event.message || ''
        );
      } else if (event.type === 'ERR') {
        console.error(
          `%c${prefix} ERR %c${event.method || ''} ${event.endpoint} %c${event.error || 'Failed'} (${event.durationMs ?? 0}ms)`,
          'background:#dc2626;color:#fff;padding:2px 6px;border-radius:4px;font-weight:bold;font-size:11px;',
          'color:#f87171;font-weight:bold;',
          'color:#94a3b8;',
          event.details || ''
        );
      } else if (event.type === 'SYSTEM') {
        console.info(
          `%c${prefix} SYS %c${event.message || event.details || ''}`,
          'background:#7c3aed;color:#fff;padding:2px 6px;border-radius:4px;font-weight:bold;font-size:11px;',
          'color:#c084fc;font-weight:bold;'
        );
      }

      // 2. Fire-and-forget logging to Vite terminal middleware
      fetch('/__terminal_log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event),
      }).catch(() => {
        // Silently catch in case dev server endpoint is not active
      });
    }
  } catch {
    // ignore
  }
}

export const terminalLogger = {
  info: (message: string, details?: any) => {
    logToTerminal({
      type: 'SYSTEM',
      endpoint: 'CLIENT',
      message,
      details: typeof details === 'object' ? JSON.stringify(details) : details,
    });
  },
  error: (message: string, details?: any) => {
    logToTerminal({
      type: 'ERR',
      endpoint: 'CLIENT',
      error: message,
      details: typeof details === 'object' ? JSON.stringify(details) : details,
    });
  },
  req: (endpoint: string, method = 'POST', payload?: any) => {
    logToTerminal({
      type: 'REQ',
      endpoint,
      method,
      payload,
    });
  },
  res: (endpoint: string, method = 'POST', status = 200, durationMs = 0, message?: string) => {
    logToTerminal({
      type: 'RES',
      endpoint,
      method,
      status,
      durationMs,
      message,
    });
  },
};
