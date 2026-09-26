/**
 * URL validation result for Cloudflare / Pipeline tunnel gateways.
 */
export interface UrlValidationResult {
  isValid: boolean;
  error: string | null;
  warning: string | null;
  suggestedFix?: string;
  hasTrailingSlash: boolean;
  hasPathSegment: boolean;
}

/**
 * Validates a Tunnel Gateway URL in real-time as the user types.
 *
 * Rules:
 * 1. Enforces `https://` prefix for remote tunnel endpoints.
 *    (Allows `http://localhost` and `http://127.0.0.1` for local development).
 * 2. Emits warnings if the URL contains trailing slashes or path segments.
 * 3. Suggests clean root origins.
 */
export function validateTunnelUrl(rawUrl: string): UrlValidationResult {
  const trimmed = rawUrl.trim();

  // If empty, no error yet (handled as required on connect)
  if (!trimmed) {
    return {
      isValid: false,
      error: null,
      warning: null,
      hasTrailingSlash: false,
      hasPathSegment: false,
    };
  }

  const isLocalDev =
    trimmed.startsWith('http://localhost') ||
    trimmed.startsWith('https://localhost') ||
    trimmed.startsWith('http://127.0.0.1') ||
    trimmed.startsWith('https://127.0.0.1') ||
    trimmed === 'http://localhost:8000';

  // 1. Incomplete prefix check
  if (
    trimmed.toLowerCase() === 'https://' ||
    trimmed.toLowerCase() === 'https:' ||
    trimmed.toLowerCase() === 'https'
  ) {
    return {
      isValid: false,
      error: 'Please enter the domain address after https://',
      warning: null,
      hasTrailingSlash: false,
      hasPathSegment: false,
    };
  }

  // 2. https:// prefix enforced
  if (!isLocalDev && !trimmed.toLowerCase().startsWith('https://')) {
    let suggestedFix: string | undefined;
    if (trimmed.toLowerCase().startsWith('http://')) {
      suggestedFix = 'https://' + trimmed.slice(7);
    } else if (!trimmed.includes('://')) {
      suggestedFix = 'https://' + trimmed;
    }

    return {
      isValid: false,
      error: 'Tunnel URL must begin with https:// (e.g., https://your-tunnel.trycloudflare.com)',
      warning: null,
      suggestedFix,
      hasTrailingSlash: trimmed.endsWith('/'),
      hasPathSegment: false,
    };
  }

  // 2. Parse URL and check structure
  try {
    const parsed = new URL(trimmed);

    // Hostname sanity check
    if (
      !parsed.hostname ||
      parsed.hostname.length < 3 ||
      (!isLocalDev && !parsed.hostname.includes('.'))
    ) {
      return {
        isValid: false,
        error: 'Please enter a valid domain address (e.g., https://xxxx.trycloudflare.com)',
        warning: null,
        hasTrailingSlash: trimmed.endsWith('/'),
        hasPathSegment: false,
      };
    }

    const hasTrailingSlash = trimmed.endsWith('/');
    const hasPathSegment = parsed.pathname !== '/' && parsed.pathname !== '';
    const suggestedOrigin = parsed.origin;

    let warning: string | null = null;
    if (hasTrailingSlash && hasPathSegment) {
      warning = `URL contains path segment ('${parsed.pathname}') and trailing slash. Gateway should be root domain (${suggestedOrigin}).`;
    } else if (hasPathSegment) {
      warning = `URL contains path segment ('${parsed.pathname}'). The base gateway should be the root domain without subpaths (${suggestedOrigin}).`;
    } else if (hasTrailingSlash) {
      warning = `URL contains trailing slash ('/'). Trailing slashes will be automatically trimmed on connection.`;
    }

    return {
      isValid: true,
      error: null,
      warning,
      suggestedFix: hasTrailingSlash || hasPathSegment ? suggestedOrigin : undefined,
      hasTrailingSlash,
      hasPathSegment,
    };
  } catch {
    return {
      isValid: false,
      error: 'Invalid URL format. Please check the address structure.',
      warning: null,
      hasTrailingSlash: trimmed.endsWith('/'),
      hasPathSegment: false,
    };
  }
}

/**
 * Sanitizes a tunnel URL by trimming whitespace, removing trailing slashes,
 * and normalizing to origin when path segments exist.
 */
export function sanitizeTunnelUrl(rawUrl: string): string {
  let trimmed = rawUrl.trim();
  if (!trimmed) return '';

  if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
    trimmed = 'https://' + trimmed;
  }

  try {
    const parsed = new URL(trimmed);
    return parsed.origin;
  } catch {
    return trimmed.replace(/\/+$/, '');
  }
}

/**
 * Formats relative time since last successful connection.
 * E.g., "Last connected: 5 minutes ago", "Last connected: Just now", "Last connected: Never"
 */
export function formatLastConnected(
  timestamp: number | null,
  isConnected: boolean,
  now: number = Date.now()
): string {
  if (isConnected) {
    return 'Last connected: Just now';
  }

  if (!timestamp || isNaN(timestamp) || timestamp <= 0) {
    return 'Last connected: Never';
  }

  const diffMs = now - timestamp;
  if (diffMs < 0) {
    return 'Last connected: Just now';
  }

  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHours = Math.floor(diffMin / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMin < 1) {
    return 'Last connected: Just now';
  }
  if (diffMin === 1) {
    return 'Last connected: 1 minute ago';
  }
  if (diffMin < 60) {
    return `Last connected: ${diffMin} minutes ago`;
  }
  if (diffHours === 1) {
    return 'Last connected: 1 hour ago';
  }
  if (diffHours < 24) {
    return `Last connected: ${diffHours} hours ago`;
  }
  if (diffDays === 1) {
    return 'Last connected: 1 day ago';
  }
  return `Last connected: ${diffDays} days ago`;
}
