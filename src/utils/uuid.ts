/**
 * Cross-Session UUID and Chat Session Date Utilities
 */

/**
 * Generates an RFC4122 v4 compliant UUID.
 * Uses native crypto.randomUUID() when available, with a robust fallback.
 */
export function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    try {
      return crypto.randomUUID();
    } catch {
      // fallback if crypto.randomUUID fails in restricted iframe/context
    }
  }

  // RFC4122 v4 UUID generator
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Truncates user query to create a readable chat session title.
 */
export function truncateSessionTitle(text: string, maxLength: number = 42): string {
  const cleaned = text.trim().replace(/\s+/g, ' ');
  if (!cleaned) return 'New Chat';
  if (cleaned.length <= maxLength) return cleaned;
  return `${cleaned.slice(0, maxLength).trim()}...`;
}

/**
 * Formats a session timestamp or date string into human-friendly representation for the sidebar.
 * e.g. "Today", "Yesterday", "Sep 5, 2026", or relative string like "Just now".
 */
export function formatSessionDate(dateVal?: string | number | Date): string {
  if (!dateVal) return 'Recent';

  // If it's already a relative label like "Just now", "2m ago", "Today"
  if (
    typeof dateVal === 'string' &&
    (dateVal === 'Just now' || dateVal.includes('ago') || dateVal === 'Today')
  ) {
    return dateVal;
  }

  const d = new Date(dateVal);
  if (isNaN(d.getTime())) {
    // If not a parseable date, return the string as-is
    return typeof dateVal === 'string' ? dateVal : 'Recent';
  }

  const now = new Date();
  const diffMs = now.getTime() - d.getTime();

  // If created within the last few minutes
  if (diffMs < 60 * 1000) {
    return 'Just now';
  }

  // Same day
  if (
    d.getDate() === now.getDate() &&
    d.getMonth() === now.getMonth() &&
    d.getFullYear() === now.getFullYear()
  ) {
    return `Today, ${d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
  }

  // Yesterday
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (
    d.getDate() === yesterday.getDate() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getFullYear() === yesterday.getFullYear()
  ) {
    return `Yesterday, ${d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
  }

  // Within current year: "Sep 5"
  if (d.getFullYear() === now.getFullYear()) {
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  // Older years: "Sep 5, 2025"
  return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
}
