import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { setApiMode } from '../app/config';
import { RaisePage } from '../features/raise/RaisePage';
import { chatService } from '../services/ChatService';
import { useModeStore } from '../stores/modeStore';

describe('Keyboard Navigation & ARIA Accessibility', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    setApiMode('mock');
    useModeStore.setState({ isTunnelConfigured: false, appMode: 'offline' });
  });

  describe('Global Keyboard Shortcuts (Cmd/Ctrl + K, Cmd/Ctrl + /, Esc)', () => {
    it('Cmd/Ctrl + K focuses the query input from anywhere', async () => {
      render(<RaisePage />);

      const queryInput = screen.getByRole('combobox', { name: /Ask a research inquiry/i });
      expect(document.activeElement).not.toBe(queryInput);

      // Simulate Cmd + K from anywhere on window
      fireEvent.keyDown(window, { key: 'k', metaKey: true });
      expect(document.activeElement).toBe(queryInput);

      // Blur and test Ctrl + K (Windows/Linux)
      queryInput.blur();
      expect(document.activeElement).not.toBe(queryInput);

      fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
      expect(document.activeElement).toBe(queryInput);
    });

    it('Cmd/Ctrl + / opens and toggles the Settings modal', async () => {
      render(<RaisePage />);

      // Settings modal should not be open initially
      expect(screen.queryByRole('dialog', { name: /Settings/i })).not.toBeInTheDocument();

      // Trigger Cmd + / to open
      fireEvent.keyDown(window, { key: '/', metaKey: true });
      expect(screen.getByRole('dialog', { name: /Settings/i })).toBeInTheDocument();

      // Trigger Cmd + / again to toggle close
      fireEvent.keyDown(window, { key: '/', metaKey: true });
      expect(screen.queryByRole('dialog', { name: /Settings/i })).not.toBeInTheDocument();
    });

    it('Esc closes any open modal, drawer, and popup', async () => {
      render(<RaisePage />);

      // Open settings modal first
      fireEvent.keyDown(window, { key: '/', metaKey: true });
      expect(screen.getByRole('dialog', { name: /Settings/i })).toBeInTheDocument();

      // Press Esc to dismiss settings modal
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(screen.queryByRole('dialog', { name: /Settings/i })).not.toBeInTheDocument();

      // Open Sources modal via nav button
      const sourcesBtn = document.getElementById('navSourcesBtn');
      expect(sourcesBtn).not.toBeNull();
      fireEvent.click(sourcesBtn!);
      expect(screen.getByRole('dialog', { name: /Source Documents Drawer/i })).toBeInTheDocument();

      // Press Esc to dismiss Sources modal
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(screen.queryByRole('dialog', { name: /Source Documents Drawer/i })).not.toBeInTheDocument();
    });
  });

  describe('Prompt Suggestion List Navigation (↑/↓ and Enter)', () => {
    it('renders clean interface with no suggestions when 0 documents are uploaded', async () => {
      render(<RaisePage />);

      const queryInput = screen.getByRole('combobox', { name: /Ask a research inquiry/i }) as HTMLTextAreaElement;
      fireEvent.focus(queryInput);

      // When 0 documents are uploaded, no suggestions listbox is rendered (clean chat interface)
      expect(screen.queryByRole('listbox', { name: /Prompt Suggestions/i })).not.toBeInTheDocument();
    });

    it('allows navigating suggestions via ArrowDown / ArrowUp and selecting with Enter when documents are attached', async () => {
      useModeStore.setState({ isTunnelConfigured: true, appMode: 'connected' });

      vi.spyOn(chatService, 'listChatSessions').mockResolvedValue({
        data: [
          {
            thread_id: 'session-doc-attached',
            session_id: 'session-doc-attached',
            username: 'Operator',
            title: 'Document Thread',
            messages: [],
            is_saved: false,
            sources: [
              {
                id: 'doc-1',
                name: 'IITMRP Annual Report.pdf',
                size: '12.4 MB',
                pages: 48,
                selected: true,
                color: 'indigo',
                status: 'ready',
              },
            ],
            selectedSourceIds: ['doc-1'],
          },
        ],
        error: null,
        isMock: true,
        status: 200,
      });
      vi.spyOn(chatService, 'getChatHistory').mockResolvedValue({
        data: {
          thread_id: 'session-doc-attached',
          session_id: 'session-doc-attached',
          username: 'Operator',
          title: 'Document Thread',
          messages: [],
          is_saved: false,
        },
        error: null,
        isMock: true,
        status: 200,
      });
      vi.spyOn(chatService, 'getSuggestions').mockResolvedValue({
        data: [
          { query: 'What leadership role does Dr. Shrikumar Suryanarayan hold in the institute?' },
          { query: 'What collaborative research initiatives are driven through Institute Centres?' },
        ],
        error: null,
        isMock: true,
        status: 200,
      });

      render(<RaisePage />);

      await waitFor(() => {
        expect(screen.getByText('Document Thread')).toBeInTheDocument();
      });
      fireEvent.click(screen.getByText('Document Thread'));

      const queryInput = screen.getByRole('combobox', { name: /Ask a research inquiry/i }) as HTMLTextAreaElement;

      // Focus query input: suggestions open because documents are attached
      fireEvent.focus(queryInput);

      await waitFor(() => {
        expect(screen.getByRole('listbox', { name: /Prompt Suggestions/i })).toBeInTheDocument();
      });

      const suggestionsList = screen.getByRole('listbox', { name: /Prompt Suggestions/i });
      expect(suggestionsList).toBeInTheDocument();

      // Navigate down
      fireEvent.keyDown(queryInput, { key: 'ArrowDown' });
      const firstOption = screen.getByTestId('query-suggestion-item-0');
      expect(firstOption).toHaveAttribute('aria-selected', 'true');

      // Navigate down again
      fireEvent.keyDown(queryInput, { key: 'ArrowDown' });
      const secondOption = screen.getByTestId('query-suggestion-item-1');
      expect(secondOption).toHaveAttribute('aria-selected', 'true');
      expect(firstOption).toHaveAttribute('aria-selected', 'false');

      // Press Enter to choose this suggestion
      fireEvent.keyDown(queryInput, { key: 'Enter' });

      // Suggestion dropdown closes and query is filled
      expect(screen.queryByRole('listbox', { name: /Prompt Suggestions/i })).not.toBeInTheDocument();
      expect(queryInput.value).toContain('What collaborative research initiatives');
    });

    it('closes suggestions when Esc is pressed inside textarea', async () => {
      useModeStore.setState({ isTunnelConfigured: true, appMode: 'connected' });

      vi.spyOn(chatService, 'listChatSessions').mockResolvedValue({
        data: [
          {
            thread_id: 'session-doc-attached',
            session_id: 'session-doc-attached',
            username: 'Operator',
            title: 'Document Thread',
            messages: [],
            is_saved: false,
            sources: [
              {
                id: 'doc-1',
                name: 'IITMRP Annual Report.pdf',
                size: '12.4 MB',
                pages: 48,
                selected: true,
                color: 'indigo',
                status: 'ready',
              },
            ],
            selectedSourceIds: ['doc-1'],
          },
        ],
        error: null,
        isMock: true,
        status: 200,
      });
      vi.spyOn(chatService, 'getChatHistory').mockResolvedValue({
        data: {
          thread_id: 'session-doc-attached',
          session_id: 'session-doc-attached',
          username: 'Operator',
          title: 'Document Thread',
          messages: [],
          is_saved: false,
        },
        error: null,
        isMock: true,
        status: 200,
      });
      vi.spyOn(chatService, 'getSuggestions').mockResolvedValue({
        data: [
          { query: 'What leadership role does Dr. Shrikumar Suryanarayan hold in the institute?' },
        ],
        error: null,
        isMock: true,
        status: 200,
      });

      render(<RaisePage />);

      await waitFor(() => {
        expect(screen.getByText('Document Thread')).toBeInTheDocument();
      });
      fireEvent.click(screen.getByText('Document Thread'));

      const queryInput = screen.getByRole('combobox', { name: /Ask a research inquiry/i });
      fireEvent.focus(queryInput);

      await waitFor(() => {
        expect(screen.getByRole('listbox', { name: /Prompt Suggestions/i })).toBeInTheDocument();
      });

      fireEvent.keyDown(queryInput, { key: 'Escape' });
      expect(screen.queryByRole('listbox', { name: /Prompt Suggestions/i })).not.toBeInTheDocument();
    });
  });

  describe('Citation Cards & PDF Evidence Modal Navigation', () => {
    it('renders citation cards as accessible buttons with tabIndex and responds to keyboard Enter/Space', async () => {
      useModeStore.setState({ isTunnelConfigured: true, appMode: 'connected' });

      render(<RaisePage />);

      await waitFor(() => {
        const titleEls = screen.getAllByText(/XYMA/i);
        expect(titleEls.length).toBeGreaterThan(0);
      });
      fireEvent.click(screen.getAllByText(/XYMA/i)[0]);

      // Wait for session messages and citations to render
      await waitFor(() => {
        const citationCards = screen.getAllByTestId('citation-card');
        expect(citationCards.length).toBeGreaterThan(0);
      });

      const citationCards = screen.getAllByTestId('citation-card');
      const firstCard = citationCards[0];

      // Verify tab index and accessibility attributes
      expect(firstCard).toHaveAttribute('tabIndex', '0');
      expect(firstCard).toHaveAttribute('role', 'button');
      expect(firstCard).toHaveAttribute('aria-label');
      expect(firstCard.getAttribute('aria-label')).toMatch(/Citation \[1\]/);

      // Press Enter on the focused citation card to trigger modal
      fireEvent.keyDown(firstCard, { key: 'Enter' });

      await waitFor(() => {
        expect(screen.getByRole('dialog', { name: /Document Evidence/i })).toBeInTheDocument();
      });

      // Press Escape to dismiss the PDF evidence modal
      fireEvent.keyDown(window, { key: 'Escape' });
      await waitFor(() => {
        expect(screen.queryByRole('dialog', { name: /Document Evidence/i })).not.toBeInTheDocument();
      });
    });
  });

  describe('ARIA Attributes on Interactive Elements', () => {
    it('verifies full ARIA combobox pattern on query textarea', async () => {
      useModeStore.setState({ isTunnelConfigured: true, appMode: 'connected' });

      vi.spyOn(chatService, 'listChatSessions').mockResolvedValue({
        data: [
          {
            thread_id: 'session-doc-attached',
            session_id: 'session-doc-attached',
            username: 'Operator',
            title: 'Document Thread',
            messages: [],
            is_saved: false,
            sources: [
              {
                id: 'doc-1',
                name: 'IITMRP Annual Report.pdf',
                size: '12.4 MB',
                pages: 48,
                selected: true,
                color: 'indigo',
                status: 'ready',
              },
            ],
            selectedSourceIds: ['doc-1'],
          },
        ],
        error: null,
        isMock: true,
        status: 200,
      });
      vi.spyOn(chatService, 'getChatHistory').mockResolvedValue({
        data: {
          thread_id: 'session-doc-attached',
          session_id: 'session-doc-attached',
          username: 'Operator',
          title: 'Document Thread',
          messages: [],
          is_saved: false,
        },
        error: null,
        isMock: true,
        status: 200,
      });
      vi.spyOn(chatService, 'getSuggestions').mockResolvedValue({
        data: [
          { query: 'What leadership role does Dr. Shrikumar Suryanarayan hold in the institute?' },
          { query: 'What collaborative research initiatives are driven through Institute Centres?' },
        ],
        error: null,
        isMock: true,
        status: 200,
      });

      render(<RaisePage />);

      await waitFor(() => {
        expect(screen.getByText('Document Thread')).toBeInTheDocument();
      });
      fireEvent.click(screen.getByText('Document Thread'));

      const queryInput = screen.getByRole('combobox', { name: /Ask a research inquiry/i });
      expect(queryInput).toHaveAttribute('aria-autocomplete', 'list');
      expect(queryInput).toHaveAttribute('aria-controls', 'query-suggestions-list');
      expect(queryInput).toHaveAttribute('aria-expanded');

      // Focus to trigger suggestions
      fireEvent.focus(queryInput);
      await waitFor(() => {
        expect(queryInput).toHaveAttribute('aria-expanded', 'true');
      });

      // ArrowDown updates aria-activedescendant
      fireEvent.keyDown(queryInput, { key: 'ArrowDown' });
      expect(queryInput).toHaveAttribute('aria-activedescendant', 'query-suggestion-0');
    });

    it('verifies ARIA dialog roles and modal attributes on search modal', async () => {
      render(<RaisePage />);

      // Open Search Chats modal
      const searchTrigger = screen.getByRole('button', { name: /Search chats/i });
      fireEvent.click(searchTrigger);

      const searchDialog = screen.getByRole('dialog', { name: /Search all chats/i });
      expect(searchDialog).toBeInTheDocument();
      expect(searchDialog).toHaveAttribute('aria-modal', 'true');

      const searchInput = screen.getByRole('combobox', { name: /Search all chats/i });
      expect(searchInput).toHaveAttribute('aria-autocomplete', 'list');
      expect(searchInput).toHaveAttribute('aria-controls', 'search-chats-listbox');

      // Esc closes search modal
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(screen.queryByRole('dialog', { name: /Search all chats/i })).not.toBeInTheDocument();
    });
  });
});
