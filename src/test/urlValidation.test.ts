import { describe, it, expect } from 'vitest';
import {
  validateTunnelUrl,
  sanitizeTunnelUrl,
  formatLastConnected,
} from '../utils/urlValidation';

describe('Tunnel URL Validation and Formatting Suite', () => {
  describe('validateTunnelUrl', () => {
    it('returns valid: false without error for empty input', () => {
      const res = validateTunnelUrl('');
      expect(res.isValid).toBe(false);
      expect(res.error).toBeNull();
      expect(res.warning).toBeNull();
    });

    it('enforces https:// prefix for remote tunnel endpoints', () => {
      const res = validateTunnelUrl('http://my-tunnel.trycloudflare.com');
      expect(res.isValid).toBe(false);
      expect(res.error).toContain('Tunnel URL must begin with https://');
      expect(res.suggestedFix).toBe('https://my-tunnel.trycloudflare.com');
    });

    it('suggests prepending https:// when no protocol is typed', () => {
      const res = validateTunnelUrl('my-tunnel.trycloudflare.com');
      expect(res.isValid).toBe(false);
      expect(res.error).toContain('Tunnel URL must begin with https://');
      expect(res.suggestedFix).toBe('https://my-tunnel.trycloudflare.com');
    });

    it('handles incomplete https:// prefix while typing', () => {
      const res1 = validateTunnelUrl('https://');
      expect(res1.isValid).toBe(false);
      expect(res1.error).toContain('Please enter the domain address after https://');

      const res2 = validateTunnelUrl('https:');
      expect(res2.isValid).toBe(false);
      expect(res2.error).toContain('Please enter the domain address after https://');
    });

    it('accepts valid https tunnel URL without warnings', () => {
      const res = validateTunnelUrl('https://rag-secure-gateway.trycloudflare.com');
      expect(res.isValid).toBe(true);
      expect(res.error).toBeNull();
      expect(res.warning).toBeNull();
      expect(res.hasTrailingSlash).toBe(false);
      expect(res.hasPathSegment).toBe(false);
    });

    it('permits localhost and 127.0.0.1 for local developer testbeds', () => {
      const res1 = validateTunnelUrl('http://localhost:8000');
      expect(res1.isValid).toBe(true);
      expect(res1.error).toBeNull();
      expect(res1.warning).toBeNull();

      const res2 = validateTunnelUrl('http://127.0.0.1:8000');
      expect(res2.isValid).toBe(true);
      expect(res2.error).toBeNull();
      expect(res2.warning).toBeNull();
    });

    it('detects trailing slashes and warns with suggestion', () => {
      const res = validateTunnelUrl('https://my-tunnel.trycloudflare.com/');
      expect(res.isValid).toBe(true);
      expect(res.error).toBeNull();
      expect(res.hasTrailingSlash).toBe(true);
      expect(res.warning).toContain("URL contains trailing slash ('/')");
      expect(res.suggestedFix).toBe('https://my-tunnel.trycloudflare.com');
    });

    it('detects path segments and warns with base origin suggestion', () => {
      const res = validateTunnelUrl('https://my-tunnel.trycloudflare.com/api/v1');
      expect(res.isValid).toBe(true);
      expect(res.error).toBeNull();
      expect(res.hasPathSegment).toBe(true);
      expect(res.warning).toContain("URL contains path segment ('/api/v1')");
      expect(res.suggestedFix).toBe('https://my-tunnel.trycloudflare.com');
    });

    it('detects both path segments and trailing slash', () => {
      const res = validateTunnelUrl('https://my-tunnel.trycloudflare.com/api/v1/');
      expect(res.isValid).toBe(true);
      expect(res.error).toBeNull();
      expect(res.hasTrailingSlash).toBe(true);
      expect(res.hasPathSegment).toBe(true);
      expect(res.warning).toContain('and trailing slash');
      expect(res.suggestedFix).toBe('https://my-tunnel.trycloudflare.com');
    });
  });

  describe('sanitizeTunnelUrl', () => {
    it('strips trailing slashes from valid URL', () => {
      expect(sanitizeTunnelUrl('https://tunnel.trycloudflare.com/')).toBe('https://tunnel.trycloudflare.com');
      expect(sanitizeTunnelUrl('https://tunnel.trycloudflare.com///')).toBe('https://tunnel.trycloudflare.com');
    });

    it('strips path segments to retain base origin', () => {
      expect(sanitizeTunnelUrl('https://tunnel.trycloudflare.com/api/chat')).toBe('https://tunnel.trycloudflare.com');
      expect(sanitizeTunnelUrl('https://tunnel.trycloudflare.com/api/chat/')).toBe('https://tunnel.trycloudflare.com');
    });

    it('ensures https:// prefix if scheme missing', () => {
      expect(sanitizeTunnelUrl('my-tunnel.trycloudflare.com')).toBe('https://my-tunnel.trycloudflare.com');
      expect(sanitizeTunnelUrl('my-tunnel.trycloudflare.com/api/')).toBe('https://my-tunnel.trycloudflare.com');
    });

    it('preserves port numbers on localhost', () => {
      expect(sanitizeTunnelUrl('http://localhost:8000/api/')).toBe('http://localhost:8000');
    });

    it('returns empty string on empty input', () => {
      expect(sanitizeTunnelUrl('')).toBe('');
      expect(sanitizeTunnelUrl('   ')).toBe('');
    });
  });

  describe('formatLastConnected', () => {
    const fixedNow = 1700000000000;

    it('returns "Last connected: Just now" when actively connected', () => {
      expect(formatLastConnected(fixedNow - 3600000, true, fixedNow)).toBe('Last connected: Just now');
    });

    it('returns "Last connected: Never" when timestamp is null, undefined, or <= 0', () => {
      expect(formatLastConnected(null, false, fixedNow)).toBe('Last connected: Never');
      expect(formatLastConnected(0, false, fixedNow)).toBe('Last connected: Never');
      expect(formatLastConnected(-500, false, fixedNow)).toBe('Last connected: Never');
    });

    it('formats less than 1 minute as "Just now"', () => {
      expect(formatLastConnected(fixedNow - 25000, false, fixedNow)).toBe('Last connected: Just now');
    });

    it('formats 1 minute ago', () => {
      expect(formatLastConnected(fixedNow - 65 * 1000, false, fixedNow)).toBe('Last connected: 1 minute ago');
    });

    it('formats multiple minutes ago', () => {
      expect(formatLastConnected(fixedNow - 14 * 60 * 1000, false, fixedNow)).toBe('Last connected: 14 minutes ago');
    });

    it('formats 1 hour ago', () => {
      expect(formatLastConnected(fixedNow - 62 * 60 * 1000, false, fixedNow)).toBe('Last connected: 1 hour ago');
    });

    it('formats multiple hours ago', () => {
      expect(formatLastConnected(fixedNow - 5 * 60 * 60 * 1000, false, fixedNow)).toBe('Last connected: 5 hours ago');
    });

    it('formats 1 day ago', () => {
      expect(formatLastConnected(fixedNow - 25 * 60 * 60 * 1000, false, fixedNow)).toBe('Last connected: 1 day ago');
    });

    it('formats multiple days ago', () => {
      expect(formatLastConnected(fixedNow - 3 * 24 * 60 * 60 * 1000, false, fixedNow)).toBe('Last connected: 3 days ago');
    });
  });
});
