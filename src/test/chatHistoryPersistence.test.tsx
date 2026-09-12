import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { chatService } from '../services/ChatService';
import { apiClient } from '../api/client';
import { setApiMode } from '../app/config';
import { generateUUID, truncateSessionTitle, formatSessionDate } from '../utils/uuid';
import { RaisePage } from '../features/raise/RaisePage';
import { mockAdapter } from '../mocks/mockAdapter';

import { useModeStore } from '../stores/modeStore';

describe('Chat History Persistence (Cross-Session)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    mockAdapter.resetScenario();
    setApiMode('mock');
    useModeStore.setState({ isTunnelConfigured: false, appMode: 'offline' });
  });

  describe('UUID & String Utilities', () => {
    it('generates a valid RFC4122 v4 UUID string', () => {
      const uuid1 = generateUUID();
      const uuid2 = generateUUID();

      expect(uuid1).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
      expect(uuid2).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
      expect(uuid1).not.toBe(uuid2);
    });

    it('truncates first question cleanly for session title with ellipsis', () => {
      const shortQ = 'Who is XYMA?';
      expect(truncateSessionTitle(shortQ, 40)).toBe('Who is XYMA?');

      const longQ = 'Identify the specific IIT Madras faculty members, research centers, and product lines associated with the startups XYMA Analytics';
      const truncated = truncateSessionTitle(longQ, 35);
      expect(truncated.length).toBeLessThanOrEqual(38);
      expect(truncated.endsWith('...')).toBe(true);
    });

    it('formats timestamps into user-friendly sidebar dates', () => {
      expect(formatSessionDate('Just now')).toBe('Just now');
      expect(formatSessionDate('Today, 2:15 PM')).toBe('Today, 2:15 PM');

      const now = new Date();
      expect(formatSessionDate(now.toISOString())).toBe('Just now');

      const yesterday = new Date(now);
      yesterday.setDate(now.getDate() - 1);
      yesterday.setHours(14, 30, 0, 0);
      expect(formatSessionDate(yesterday.toISOString())).toContain('Yesterday');
    });
  });

  describe('ChatService History & Persistence API Calls', () => {
    it('chatService.getChatHistory queries GET /api/chat/history?session_id={thread_id}', async () => {
      const requestSpy = vi.spyOn(apiClient, 'request');
      const testSessionId = 'session-xyma-faculty';

      const res = await chatService.getChatHistory(testSessionId);

      expect(requestSpy).toHaveBeenCalledWith(
        `/api/chat/history?session_id=${encodeURIComponent(testSessionId)}`,
        undefined,
        expect.objectContaining({ method: 'GET' })
      );
      expect(res.status).toBe(200);
      expect(res.data?.session_id || res.data?.thread_id).toBe(testSessionId);
      expect(Array.isArray(res.data?.messages)).toBe(true);
    });

    it('chatService.persistChatSession sends POST /api/chat/history with (session_id, username) key', async () => {
      const requestSpy = vi.spyOn(apiClient, 'request');
      const threadId = generateUUID();
      const payload = {
        thread_id: threadId,
        session_id: threadId,
        username: 'Dr. Researcher',
        title: 'Deep-Tech Waveguide Sensors',
        messages: [
          { role: 'user' as const, text: 'What are the sensor specs?' },
          { role: 'assistant' as const, text: 'The waveguide sensor operates up to 1400°C.' },
        ],
        is_saved: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      const res = await chatService.persistChatSession(payload);

      expect(requestSpy).toHaveBeenCalledWith(
        '/api/chat/history',
        undefined,
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(payload),
        })
      );
      expect(res.status).toBe(200);
      expect(res.data?.thread_id).toBe(threadId);

      // Verify immediate retrieval works via mock roundtrip
      const historyRes = await chatService.getChatHistory(threadId);
      expect(historyRes.data?.messages).toHaveLength(2);
      expect(historyRes.data?.messages[0].text).toBe('What are the sensor specs?');
    });

    it('chatService.listChatSessions retrieves all saved user sessions', async () => {
      const requestSpy = vi.spyOn(apiClient, 'request');
      const username = 'Dr. Researcher';

      const res = await chatService.listChatSessions(username);

      expect(requestSpy).toHaveBeenCalledWith(
        `/api/chat/sessions?username=${encodeURIComponent(username)}`,
        undefined,
        expect.objectContaining({ method: 'GET' })
      );
      expect(res.status).toBe(200);
      expect(Array.isArray(res.data)).toBe(true);
    });

    it('chatService.renameChatSession sends updated title to backend', async () => {
      const requestSpy = vi.spyOn(apiClient, 'request');
      const testId = generateUUID();

      await chatService.renameChatSession(testId, 'Renamed Sensor Thread', 'Operator');

      expect(requestSpy).toHaveBeenCalledWith(
        '/api/chat/history',
        undefined,
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('"title":"Renamed Sensor Thread"'),
        })
      );
    });

    it('chatService.deleteChatSession sends DELETE /api/chat/history?session_id={thread_id}', async () => {
      const requestSpy = vi.spyOn(apiClient, 'request');
      const testId = generateUUID();

      await chatService.deleteChatSession(testId);

      expect(requestSpy).toHaveBeenCalledWith(
        `/api/chat/history?session_id=${encodeURIComponent(testId)}`,
        undefined,
        expect.objectContaining({ method: 'DELETE' })
      );
    });
    it('chatService.clearChat sends POST /api/chat/clear with empty body to purge all chat history', async () => {
      const requestSpy = vi.spyOn(apiClient, 'request');

      await chatService.clearChat();

      expect(requestSpy).toHaveBeenCalledWith(
        '/api/chat/clear',
        undefined,
        expect.objectContaining({
          method: 'POST',
          body: '{}',
        })
      );
    });
  });

  describe('RaisePage Sidebar & Cross-Session UI Flow', () => {
    beforeEach(() => {
      useModeStore.setState({ isTunnelConfigured: true, appMode: 'connected' });
    });

    it('restores previous messages from GET /api/chat/history?session_id={thread_id} when selecting a session', async () => {
      const getHistorySpy = vi.spyOn(chatService, 'getChatHistory');

      render(<RaisePage />);

      // Wait for sessions to load from backend
      await waitFor(() => {
        const titleEls = screen.getAllByText(/XYMA/i);
        expect(titleEls.length).toBeGreaterThan(0);
      });

      // Select session from sidebar
      const sessionEl = screen.getAllByText(/XYMA/i)[0];
      fireEvent.click(sessionEl);

      // Verify that getChatHistory was triggered for the saved session
      await waitFor(() => {
        expect(getHistorySpy).toHaveBeenCalledWith('session-xyma-faculty');
      });

      // Verify previous messages are restored to UI
      await waitFor(() => {
        expect(
          screen.getAllByText((content) => content.includes('Which faculty member co-founded XYMA Analytics'))[0]
        ).toBeInTheDocument();
      });
    });

    it('renders conversation threads sidebar with truncated title and date', async () => {
      render(<RaisePage />);

      // Sidebar should display past sessions with title + date
      await waitFor(() => {
        const titleEls = screen.getAllByText(/XYMA/i);
        expect(titleEls.length).toBeGreaterThan(0);
      });

      // Confirm date/timestamp exists in sidebar
      expect(screen.getAllByText(/Today|Yesterday|Recent/i).length).toBeGreaterThan(0);
    });

    it('"New Chat" button creates a brand new thread_id UUID and resets conversation', async () => {
      render(<RaisePage />);

      await waitFor(() => {
        const titleEls = screen.getAllByText(/XYMA/i);
        expect(titleEls.length).toBeGreaterThan(0);
      });

      // Select session first so we have an active conversation
      const sessionEl = screen.getAllByText(/XYMA/i)[0];
      fireEvent.click(sessionEl);

      await waitFor(() => {
        expect(
          screen.getAllByText((content) => content.includes('Which faculty member co-founded XYMA Analytics'))[0]
        ).toBeInTheDocument();
      });

      const newChatBtn = screen.getAllByLabelText(/New chat/i)[0];
      fireEvent.click(newChatBtn);

      // Verify conversation is reset and no chat data is stored in localStorage
      expect(screen.queryByText(/Which faculty member co-founded XYMA Analytics/)).not.toBeInTheDocument();
      expect(localStorage.getItem('raise_current_session_id')).toBeNull();
      expect(localStorage.getItem('raise_chat_sessions')).toBeNull();
    });

    it('displays Recents header with sessions count without cluttering with a trash icon', async () => {
      render(<RaisePage />);

      // Open drawer menu so Recents section is visible
      const toggleBtn = screen.getByLabelText(/Expand menu/i);
      fireEvent.click(toggleBtn);

      // Wait for sidebar sessions to load
      await waitFor(() => {
        expect(screen.getByText('Recents')).toBeInTheDocument();
      }, { timeout: 4000 });

      // Ensure trash icon button is not present in the Recents header
      expect(screen.queryByLabelText(/^Delete all chats$/i)).not.toBeInTheDocument();
    });
  });
});
