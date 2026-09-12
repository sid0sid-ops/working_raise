import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { RaisePage } from '../features/raise/RaisePage';
import { SettingsGatewayTab } from '../components/settings/SettingsGatewayTab';
import { useModeStore } from '../stores/modeStore';
import { systemService } from '../services/SystemService';
import { getStoredTunnelUrl, getStoredUsername, setStoredTunnelUrl, setStoredUsername } from '../app/config';

describe('Cloudflare Tunnel & Gateway Connection Suite', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    useModeStore.setState({
      appMode: 'offline',
      apiBaseUrl: 'http://localhost:8000',
      isTunnelConfigured: false,
      gatewayUsername: 'Operator',
      latencyMs: undefined,
      isProbing: false,
      probeError: null,
    });
  });

  describe('LocalStorage & Configuration Persistence', () => {
    it('persists and retrieves tunnel URL from raise_tunnel_url', () => {
      expect(getStoredTunnelUrl()).toBe('');
      expect(localStorage.getItem('raise_tunnel_url')).toBeNull();
      const testTunnel = 'https://rag-secure-tunnel.trycloudflare.com';
      setStoredTunnelUrl(testTunnel);
      expect(getStoredTunnelUrl()).toBe(testTunnel);
      expect(localStorage.getItem('raise_tunnel_url')).toBe(testTunnel);
    });

    it('persists and retrieves username from raise_gateway_username', () => {
      expect(getStoredUsername()).toBe('Operator');
      expect(localStorage.getItem('raise_gateway_username')).toBeNull();
      const testUser = 'Dr. Elena Vance';
      setStoredUsername(testUser);
      expect(getStoredUsername()).toBe(testUser);
      expect(localStorage.getItem('raise_gateway_username')).toBe(testUser);
    });
  });

  describe('Top Header Navigation Layout & Gateway Status in Menu', () => {
    it('shows Disconnected status in menu when gateway is offline, and keeps header clean', () => {
      useModeStore.setState({
        appMode: 'offline',
        isTunnelConfigured: true,
        apiBaseUrl: 'https://pump-bent-framing-bay.trycloudflare.com',
      });

      render(<RaisePage />);

      // Verify Header is clean - no gateway button, no user badge, no settings button
      expect(screen.queryByTestId('header-connect-gateway-btn')).not.toBeInTheDocument();
      expect(screen.queryByTestId('header-settings-btn')).not.toBeInTheDocument();
      expect(screen.queryByTestId('header-user-badge')).not.toBeInTheDocument();

      // Verify User button exists in the menu sidebar with offline dot
      const userBtn = screen.getByTestId('user-gateway-menu-btn');
      expect(userBtn).toBeInTheDocument();
      expect(screen.getByTestId('user-offline-dot')).toBeInTheDocument();

      // Verify the URL/status tooltip is completely removed per user request
      expect(screen.queryByTestId('hover-tunnel-url')).not.toBeInTheDocument();
      expect(screen.queryByText('https://pump-bent-framing-bay.trycloudflare.com')).not.toBeInTheDocument();
    });

    it('shows User Avatar with Online green tick when connected, and keeps header clean', () => {
      useModeStore.setState({
        appMode: 'connected',
        isTunnelConfigured: true,
        gatewayUsername: 'Sarah Connor',
        apiBaseUrl: 'https://pump-bent-framing-bay.trycloudflare.com',
      });

      render(<RaisePage />);

      // Verify Header is clean
      expect(screen.queryByTestId('header-connect-gateway-btn')).not.toBeInTheDocument();
      expect(screen.queryByTestId('header-settings-btn')).not.toBeInTheDocument();
      expect(screen.queryByTestId('header-user-badge')).not.toBeInTheDocument();

      // Verify User button in menu with online dot
      const userBtn = screen.getByTestId('user-gateway-menu-btn');
      expect(userBtn).toBeInTheDocument();
      expect(screen.getByTestId('user-online-dot')).toBeInTheDocument();
      expect(userBtn).toHaveTextContent('S');

      // Verify the URL/status tooltip is completely removed per user request
      expect(screen.queryByTestId('hover-tunnel-url')).not.toBeInTheDocument();
      expect(screen.queryByText('https://pump-bent-framing-bay.trycloudflare.com')).not.toBeInTheDocument();
    });

    it('clicking user button opens tabs popover where clicking settings or gateway tab opens dialog', () => {
      useModeStore.setState({
        appMode: 'offline',
        isTunnelConfigured: true,
      });

      render(<RaisePage />);

      const userBtn = screen.getByTestId('user-gateway-menu-btn');
      // Initially popover is closed
      expect(screen.queryByTestId('user-profile-popover')).not.toBeInTheDocument();

      // Click user button to open small tabs
      fireEvent.click(userBtn);
      expect(screen.getByTestId('user-profile-popover')).toBeInTheDocument();

      // Tab 1: Settings with exact logo
      const railSettingsBtn = screen.getByTestId('rail-settings-btn');
      expect(railSettingsBtn).toBeInTheDocument();
      expect(railSettingsBtn).toHaveTextContent(/Settings/i);

      // Tab 2: Usage
      const usageBtn = screen.getByTestId('user-menu-usage-btn');
      expect(usageBtn).toBeInTheDocument();
      expect(usageBtn).toHaveTextContent(/Usage/i);

      // Tab 3: Logout
      const logoutBtn = screen.getByTestId('user-menu-logout-btn');
      expect(logoutBtn).toBeInTheDocument();
      expect(logoutBtn).toHaveTextContent(/Logout/i);

      // Clicking Settings tab opens Settings dialog
      fireEvent.click(railSettingsBtn);
      expect(screen.getByRole('dialog', { name: /Settings/i })).toBeInTheDocument();
    });
  });

  describe('Unconfigured Notice Banner', () => {
    it('displays unconfigured banner when Tunnel URL is not set', () => {
      useModeStore.setState({
        isTunnelConfigured: false,
      });

      render(<RaisePage />);

      const banner = screen.getByTestId('gateway-unconfigured-notice');
      expect(banner).toBeInTheDocument();
      expect(banner).toHaveTextContent(/Please go to Settings and paste your Pipeline Tunneling? URL to connect/i);
    });

    it('hides unconfigured banner when Tunnel URL is configured', () => {
      useModeStore.setState({
        isTunnelConfigured: true,
      });

      render(<RaisePage />);

      expect(screen.queryByTestId('gateway-unconfigured-notice')).not.toBeInTheDocument();
    });

    it('clicking Settings in banner opens Gateway settings tab', () => {
      useModeStore.setState({
        isTunnelConfigured: false,
      });

      render(<RaisePage />);

      const settingsBtn = screen.getByRole('button', { name: /open settings/i });
      fireEvent.click(settingsBtn);

      expect(screen.getByText('Pipeline Tunnel & Gateway')).toBeInTheDocument();
    });
  });

  describe('SettingsGatewayTab UI & Testing Actions', () => {
    it('renders input fields for Tunnel URL and User Name', () => {
      render(<SettingsGatewayTab />);

      expect(screen.getByTestId('gateway-tunnel-url-input')).toBeInTheDocument();
      expect(screen.getByTestId('gateway-username-input')).toBeInTheDocument();
      expect(screen.getByTestId('gateway-connect-btn')).toBeInTheDocument();
      expect(screen.getByTestId('gateway-clear-btn')).toBeInTheDocument();
    });

    it('saves Tunnel URL and Username to localStorage on Connect and triggers background check', async () => {
      vi.spyOn(systemService, 'testConnection').mockResolvedValueOnce({
        success: true,
        status: 200,
        latencyMs: 42,
        endpoint: '/health',
      });

      render(<SettingsGatewayTab />);

      const urlInput = screen.getByTestId('gateway-tunnel-url-input');
      const userInput = screen.getByTestId('gateway-username-input');

      fireEvent.change(urlInput, { target: { value: 'https://my-tunnel.trycloudflare.com' } });
      fireEvent.change(userInput, { target: { value: 'Ada Lovelace' } });

      const connectBtn = screen.getByTestId('gateway-connect-btn');
      fireEvent.click(connectBtn);

      await waitFor(() => {
        expect(localStorage.getItem('raise_tunnel_url')).toBe('https://my-tunnel.trycloudflare.com');
        expect(localStorage.getItem('raise_gateway_username')).toBe('Ada Lovelace');
        expect(systemService.testConnection).toHaveBeenCalled();
      });
    });

    it('clears saved Tunnel URL when Clear URL is clicked', () => {
      setStoredTunnelUrl('https://old-tunnel.trycloudflare.com');
      useModeStore.setState({
        apiBaseUrl: 'https://old-tunnel.trycloudflare.com',
        isTunnelConfigured: true,
      });

      render(<SettingsGatewayTab />);

      const clearBtn = screen.getByTestId('gateway-clear-btn');
      fireEvent.click(clearBtn);

      expect(localStorage.getItem('raise_tunnel_url')).toBeNull();
      expect(useModeStore.getState().isTunnelConfigured).toBe(false);
    });

    it('triggers testConnection on Connect and reports connected status with latency', async () => {
      vi.spyOn(systemService, 'testConnection').mockResolvedValueOnce({
        success: true,
        status: 200,
        latencyMs: 84,
        endpoint: '/health',
      });

      render(<SettingsGatewayTab />);

      const connectBtn = screen.getByTestId('gateway-connect-btn');
      fireEvent.click(connectBtn);

      await waitFor(() => {
        expect(systemService.testConnection).toHaveBeenCalled();
        expect(screen.getByTestId('connection-status-text')).toHaveTextContent('Connected');
      });
    });

    it('shows "Last connected: Never" when no previous connection exists, and updates when connected', async () => {
      useModeStore.setState({
        lastConnectedAt: null,
        appMode: 'offline',
      });

      const { rerender } = render(<SettingsGatewayTab />);

      const lastConnectedEl = screen.getByTestId('last-connected-time');
      expect(lastConnectedEl).toHaveTextContent('Last connected: Never');

      // Update store with a timestamp from 5 minutes ago
      act(() => {
        useModeStore.setState({
          lastConnectedAt: Date.now() - (5 * 60 * 1000 + 10000),
          appMode: 'offline',
        });
      });
      rerender(<SettingsGatewayTab />);
      expect(screen.getByTestId('last-connected-time')).toHaveTextContent('Last connected: 5 minutes ago');

      // Update store to connected
      act(() => {
        useModeStore.setState({
          appMode: 'connected',
        });
      });
      rerender(<SettingsGatewayTab />);
      expect(screen.getByTestId('last-connected-time')).toHaveTextContent('Last connected: Just now');
    });

    it('validates URL format in real-time and displays error when https:// prefix is missing', () => {
      render(<SettingsGatewayTab />);

      const urlInput = screen.getByTestId('gateway-tunnel-url-input');
      fireEvent.change(urlInput, { target: { value: 'http://my-insecure-tunnel.trycloudflare.com' } });

      const errorBanner = screen.getByTestId('gateway-url-error');
      expect(errorBanner).toBeInTheDocument();
      expect(errorBanner).toHaveTextContent(/must begin with https:\/\//i);

      // Connect button should be disabled due to format error
      const connectBtn = screen.getByTestId('gateway-connect-btn');
      expect(connectBtn).toBeDisabled();

      // Click "Apply https://" fix button
      const fixBtn = screen.getByTestId('gateway-url-fix-btn');
      fireEvent.click(fixBtn);

      // Error should be cleared and input updated
      expect(screen.queryByTestId('gateway-url-error')).not.toBeInTheDocument();
      expect(urlInput).toHaveValue('https://my-insecure-tunnel.trycloudflare.com');
      expect(connectBtn).not.toBeDisabled();
    });

    it('displays warning when URL contains trailing slashes or path segments and allows trimming', async () => {
      vi.spyOn(systemService, 'testConnection').mockResolvedValueOnce({
        success: true,
        status: 200,
        latencyMs: 50,
        endpoint: '/health',
      });

      render(<SettingsGatewayTab />);

      const urlInput = screen.getByTestId('gateway-tunnel-url-input');

      // Test trailing slash warning
      fireEvent.change(urlInput, { target: { value: 'https://clean-tunnel.trycloudflare.com/' } });
      const warningBanner = screen.getByTestId('gateway-url-warning');
      expect(warningBanner).toBeInTheDocument();
      expect(warningBanner).toHaveTextContent(/trailing slash/i);

      // Click Trim button
      const trimBtn = screen.getByTestId('gateway-url-trim-btn');
      fireEvent.click(trimBtn);

      expect(screen.queryByTestId('gateway-url-warning')).not.toBeInTheDocument();
      expect(urlInput).toHaveValue('https://clean-tunnel.trycloudflare.com');

      // Test path segment warning
      fireEvent.change(urlInput, { target: { value: 'https://clean-tunnel.trycloudflare.com/api/v1' } });
      expect(screen.getByTestId('gateway-url-warning')).toHaveTextContent(/path segment/i);

      // Connecting automatically sanitizes path segments
      const connectBtn = screen.getByTestId('gateway-connect-btn');
      fireEvent.click(connectBtn);

      await waitFor(() => {
        expect(localStorage.getItem('raise_tunnel_url')).toBe('https://clean-tunnel.trycloudflare.com');
      });
    });

    it('provides a "Copy URL" button that copies the tunnel URL to clipboard with visual feedback', async () => {
      // Mock clipboard
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: {
          writeText: writeTextMock,
        },
      });

      render(<SettingsGatewayTab />);

      const copyBtn = screen.getByTestId('gateway-copy-url-btn');
      expect(copyBtn).toBeInTheDocument();

      const urlInput = screen.getByTestId('gateway-tunnel-url-input');
      fireEvent.change(urlInput, { target: { value: 'https://shared-tunnel.trycloudflare.com' } });

      fireEvent.click(copyBtn);

      await waitFor(() => {
        expect(writeTextMock).toHaveBeenCalledWith('https://shared-tunnel.trycloudflare.com');
        expect(screen.getByText('Copied')).toBeInTheDocument();
      });
    });
  });
});
