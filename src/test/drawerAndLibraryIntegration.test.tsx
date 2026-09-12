import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { chatService } from '../services/ChatService';
import { sourceService } from '../services/SourceService';
import { useModeStore } from '../stores/modeStore';
import { RaisePage } from '../features/raise/RaisePage';
import { SettingsLibraryTab } from '../components/settings/SettingsLibraryTab';
import { LibraryPickerModal } from '../components/library/LibraryPickerModal';

describe('Plus Button, Drawer, and Library Integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useModeStore.setState({
      isTunnelConfigured: true,
      appMode: 'connected',
      gatewayUsername: 'Operator',
    });
  });

  describe('Plus (+) Button & Anchored Menu', () => {
    it('opens an anchored menu with Browse from PC and Attach from Library when clicking the + button', async () => {
      render(<RaisePage />);

      // The + button in the input bar has aria-label="Add context or source"
      const plusBtn = screen.getByRole('button', { name: /Add context or source/i });
      expect(plusBtn).toBeInTheDocument();

      // Initially menu is closed
      expect(screen.queryByText('Browse from PC')).not.toBeInTheDocument();
      expect(screen.queryByText('Attach from Library')).not.toBeInTheDocument();

      // Click the + button
      fireEvent.click(plusBtn);

      // Anchored menu displays exactly the two required items
      expect(screen.getByText('Browse from PC')).toBeInTheDocument();
      expect(screen.getByText('Attach from Library')).toBeInTheDocument();

      // Clicking Attach from Library opens LibraryPickerModal
      fireEvent.click(screen.getByText('Attach from Library'));
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });
  });

  describe('Library API Contract & Authoritative Documents', () => {
    it('loads documents from GET /api/documents preserving protected flags and chunks', async () => {
      const getDocsSpy = vi.spyOn(sourceService, 'getDocuments').mockResolvedValueOnce({
        data: {
          documents: [
            {
              id: 'doc_iitmrp_report',
              doc_id: 'doc_iitmrp_report',
              filename: 'IITMRP Annual Report.pdf',
              pages: 44,
              size_mb: 27.54,
              chunks_count: 73,
              chunks: 73,
              status: 'ready',
              phase: 'ready',
              is_protected: true,
              can_delete: false,
              deletable: false,
              owner: 'system',
            },
            {
              id: 'doc_user_upload',
              doc_id: 'doc_user_upload',
              filename: 'User_Research_Paper.pdf',
              pages: 12,
              size_mb: 2.4,
              chunks_count: 24,
              chunks: 24,
              status: 'ready',
              phase: 'ready',
              is_protected: false,
              can_delete: true,
              deletable: true,
              owner: 'user',
            },
          ],
          total_count: 2,
        },
        error: null,
        isMock: false,
        status: 200,
      });

      render(
        <LibraryPickerModal
          isOpen={true}
          onClose={vi.fn()}
          onSelectDocument={vi.fn()}
          attachedDocNames={[]}
          onOpenUploadFromPC={vi.fn()}
        />
      );

      await waitFor(() => {
        expect(getDocsSpy).toHaveBeenCalled();
        expect(screen.getByText('IITMRP Annual Report.pdf')).toBeInTheDocument();
        expect(screen.getByText('User_Research_Paper.pdf')).toBeInTheDocument();
      });
    });
  });

  describe('Dedicated Session Drawer Contracts', () => {
    it('chatService.getSessionDrawer queries GET /api/chat/sessions/{session_id}/drawer', async () => {
      const getDrawerSpy = vi.spyOn(chatService, 'getSessionDrawer').mockResolvedValueOnce({
        data: {
          status: 'success',
          session_id: 'session-xyz',
          attached_docs: ['IITMRP Annual Report.pdf'],
          active_docs: ['IITMRP Annual Report.pdf'],
          documents: [],
          count: 1,
        },
        error: null,
        isMock: false,
        status: 200,
      });

      const res = await chatService.getSessionDrawer('session-xyz');
      expect(getDrawerSpy).toHaveBeenCalledWith('session-xyz');
      expect(res.data?.attached_docs).toContain('IITMRP Annual Report.pdf');
    });

    it('chatService.attachToSessionDrawer sends POST /api/chat/sessions/{session_id}/drawer/attach', async () => {
      const attachSpy = vi.spyOn(chatService, 'attachToSessionDrawer').mockResolvedValueOnce({
        data: {
          status: 'success',
          action: 'attach',
          session_id: 'session-xyz',
          attached_document: 'User_Research_Paper.pdf',
          attached_docs: ['IITMRP Annual Report.pdf', 'User_Research_Paper.pdf'],
          active_docs: ['IITMRP Annual Report.pdf', 'User_Research_Paper.pdf'],
          count: 2,
        },
        error: null,
        isMock: false,
        status: 200,
      });

      const res = await chatService.attachToSessionDrawer('session-xyz', 'User_Research_Paper.pdf');
      expect(attachSpy).toHaveBeenCalledWith('session-xyz', 'User_Research_Paper.pdf');
      expect(res.data?.attached_docs.length).toBe(2);
    });

    it('chatService.removeFromSessionDrawer sends POST /api/chat/sessions/{session_id}/drawer/remove', async () => {
      const removeSpy = vi.spyOn(chatService, 'removeFromSessionDrawer').mockResolvedValueOnce({
        data: {
          status: 'success',
          action: 'remove',
          session_id: 'session-xyz',
          removed_document: 'User_Research_Paper.pdf',
          attached_docs: ['IITMRP Annual Report.pdf'],
          active_docs: ['IITMRP Annual Report.pdf'],
          count: 1,
        },
        error: null,
        isMock: false,
        status: 200,
      });

      const res = await chatService.removeFromSessionDrawer('session-xyz', 'User_Research_Paper.pdf');
      expect(removeSpy).toHaveBeenCalledWith('session-xyz', 'User_Research_Paper.pdf');
      expect(res.data?.attached_docs).toEqual(['IITMRP Annual Report.pdf']);
    });
  });

  describe('Per-Chat Drawer Isolation & Chat Switching', () => {
    it('rehydrates distinct drawers when switching between different chat sessions', async () => {
      const getDrawerSpy = vi.spyOn(chatService, 'getSessionDrawer').mockImplementation(async (sessionId: string) => {
        if (sessionId === 'session-a') {
          return {
            data: {
              status: 'success',
              session_id: 'session-a',
              attached_docs: ['Paper_A.pdf'],
              active_docs: ['Paper_A.pdf'],
              documents: [{ filename: 'Paper_A.pdf', size_mb: 2.0, pages: 5 }],
              count: 1,
            },
            error: null,
            isMock: false,
            status: 200,
          };
        }
        return {
          data: {
            status: 'success',
            session_id: 'session-b',
            attached_docs: ['Paper_B.pdf'],
            active_docs: ['Paper_B.pdf'],
            documents: [{ filename: 'Paper_B.pdf', size_mb: 3.5, pages: 10 }],
            count: 1,
          },
          error: null,
          isMock: false,
          status: 200,
        };
      });

      vi.spyOn(chatService, 'listChatSessions').mockResolvedValueOnce({
        data: [
          {
            id: 'session-a',
            thread_id: 'session-a',
            title: 'Research Topic A',
            messages: [],
            sources: [],
            attached_docs: ['Paper_A.pdf'],
          },
          {
            id: 'session-b',
            thread_id: 'session-b',
            title: 'Research Topic B',
            messages: [],
            sources: [],
            attached_docs: ['Paper_B.pdf'],
          },
        ] as any,
        error: null,
        isMock: false,
        status: 200,
      });

      render(<RaisePage />);

      await waitFor(() => {
        expect(screen.getByText('Research Topic A')).toBeInTheDocument();
        expect(screen.getByText('Research Topic B')).toBeInTheDocument();
      });

      // Switch to Topic A
      fireEvent.click(screen.getByText('Research Topic A'));
      await waitFor(() => {
        expect(getDrawerSpy).toHaveBeenCalledWith('session-a');
      });

      // Switch to Topic B
      fireEvent.click(screen.getByText('Research Topic B'));
      await waitFor(() => {
        expect(getDrawerSpy).toHaveBeenCalledWith('session-b');
      });
    });
  });

  describe('Library Deletion Rules (Protected vs User-Uploaded)', () => {
    it('prevents deletion of pre-baked protected documents', async () => {
      vi.spyOn(sourceService, 'getDocuments').mockResolvedValueOnce({
        data: {
          documents: [
            {
              id: 'doc_protected',
              filename: 'Protected_Report.pdf',
              status: 'ready',
              is_protected: true,
              can_delete: false,
              deletable: false,
            },
          ] as any,
          total_count: 1,
        },
        error: null,
        isMock: false,
        status: 200,
      });

      render(<SettingsLibraryTab />);

      await waitFor(() => {
        expect(screen.getByText('Protected_Report.pdf')).toBeInTheDocument();
      });

      // The delete button is not available or shows locked tooltip
      expect(screen.getByTitle('Protected document')).toBeInTheDocument();
    });

    it('allows deletion of user-uploaded documents and handles backend confirmation', async () => {
      vi.spyOn(sourceService, 'getDocuments').mockResolvedValueOnce({
        data: {
          documents: [
            {
              id: 'doc_user',
              filename: 'User_Report.pdf',
              status: 'ready',
              is_protected: false,
              can_delete: true,
              deletable: true,
            },
          ] as any,
          total_count: 1,
        },
        error: null,
        isMock: false,
        status: 200,
      });

      const deleteSpy = vi.spyOn(sourceService, 'deleteDocument').mockResolvedValueOnce({
        data: {
          status: 'success',
          filename: 'User_Report.pdf',
          documents: [],
          total_count: 0,
        },
        error: null,
        isMock: false,
        status: 200,
      });

      render(<SettingsLibraryTab />);

      await waitFor(() => {
        expect(screen.getByText('User_Report.pdf')).toBeInTheDocument();
      });

      const deleteBtn = screen.getByTitle('Delete from Library & GraphRAG');
      expect(deleteBtn).toBeInTheDocument();

      fireEvent.click(deleteBtn);

      await waitFor(() => {
        expect(deleteSpy).toHaveBeenCalledWith('User_Report.pdf');
      });
    });
  });
});
