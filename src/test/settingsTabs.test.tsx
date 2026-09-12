import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { SettingsLibraryTab } from '../components/settings/SettingsLibraryTab';
import { SettingsDataControlTab } from '../components/settings/SettingsDataControlTab';
import { sourceService } from '../services/SourceService';
import type { ChatSession } from '../features/raise/RaisePage';

describe('Settings Tabs — Library & Data Controls', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('SettingsLibraryTab', () => {
    const mockLibraryDocs = [
      {
        filename: 'IITMRP Annual Report.pdf',
        pages: 44,
        size_mb: 27.5,
        chunks_count: 88,
        status: 'ready' as const,
      },
      {
        filename: 'Bioinformatics_Gene_Vectors.csv',
        pages: 12,
        size_mb: 4.2,
        chunks_count: 24,
        status: 'ready' as const,
      },
      {
        filename: 'ARE-2016-17.pdf',
        pages: 35,
        size_mb: 18.1,
        chunks_count: 70,
        status: 'ready' as const,
      },
      {
        filename: 'Clinical_Trial_Genomics_Raw.pdf',
        pages: 8,
        size_mb: 1.8,
        chunks_count: 16,
        status: 'processing' as const,
      },
    ];

    beforeEach(() => {
      vi.spyOn(sourceService, 'getDocuments').mockResolvedValue({
        data: { documents: mockLibraryDocs, total_count: mockLibraryDocs.length },
        error: null,
        isMock: false,
        status: 200,
      });
    });

    it('renders clean empty state when backend reports 0 documents', async () => {
      vi.spyOn(sourceService, 'getDocuments').mockResolvedValueOnce({
        data: { documents: [], total_count: 0 },
        error: null,
        isMock: false,
        status: 200,
      });

      render(<SettingsLibraryTab />);

      expect(screen.getByText('Library')).toBeInTheDocument();
      expect(await screen.findByText('Knowledge Base Library is empty')).toBeInTheDocument();
      expect(screen.getByText('0 files')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Upload Document to Library/i })).toBeInTheDocument();
    });

    it('renders uploaded library items populated from backend with size', async () => {
      render(<SettingsLibraryTab />);

      // Verify header count
      expect(screen.getByText('Library')).toBeInTheDocument();
      expect(await screen.findByText('IITMRP Annual Report.pdf')).toBeInTheDocument();
      expect(screen.getByText('27.5 MB')).toBeInTheDocument();
      expect(screen.getByText(/All uploaded knowledge documents/)).toBeInTheDocument();
    });

    it('switches view mode between Icons, Details, and Full details without tooltips or text labels', async () => {
      render(<SettingsLibraryTab />);
      expect(await screen.findByText('IITMRP Annual Report.pdf')).toBeInTheDocument();

      // Switch to Details table view
      const detailsBtn = screen.getByLabelText('Details view');
      expect(detailsBtn.getAttribute('title')).toBeNull();
      fireEvent.click(detailsBtn);
      expect(screen.getByText('Document Name')).toBeInTheDocument();
      expect(screen.getByText('Upload Date & Time')).toBeInTheDocument();

      // Switch to Full details expanded card view
      const fullDetailsBtn = screen.getByLabelText('Full details view');
      expect(fullDetailsBtn.getAttribute('title')).toBeNull();
      fireEvent.click(fullDetailsBtn);
      expect(screen.getAllByText(/pages/).length).toBeGreaterThan(0);
      expect(screen.queryByText(/chunks extracted/)).not.toBeInTheDocument();

      // Switch back to Icons grid view
      const iconsBtn = screen.getByLabelText('Icons view');
      expect(iconsBtn.getAttribute('title')).toBeNull();
      fireEvent.click(iconsBtn);
      expect(screen.queryByText('Document Name')).not.toBeInTheDocument();
    });

    it('filters documents in library by search query', async () => {
      render(<SettingsLibraryTab />);
      expect(await screen.findByText('IITMRP Annual Report.pdf')).toBeInTheDocument();

      const searchInput = screen.getByPlaceholderText('Search documents...');
      fireEvent.change(searchInput, { target: { value: 'Bioinformatics' } });

      expect(screen.getByText('Bioinformatics_Gene_Vectors.csv')).toBeInTheDocument();
      expect(screen.queryByText('IITMRP Annual Report.pdf')).not.toBeInTheDocument();
    });

    it('sorts documents by name, size, and type', async () => {
      render(<SettingsLibraryTab />);
      expect(await screen.findByText('IITMRP Annual Report.pdf')).toBeInTheDocument();

      const sortSelect = screen.getByRole('combobox');
      fireEvent.change(sortSelect, { target: { value: 'name-asc' } });
      expect((sortSelect as HTMLSelectElement).value).toBe('name-asc');

      fireEvent.change(sortSelect, { target: { value: 'size-desc' } });
      expect((sortSelect as HTMLSelectElement).value).toBe('size-desc');

      fireEvent.change(sortSelect, { target: { value: 'type-asc' } });
      expect((sortSelect as HTMLSelectElement).value).toBe('type-asc');
      expect(screen.getByText('Sort by Type')).toBeInTheDocument();
    });

    it('does not display separate "All Files", "PDF", "CSV", "DOCX" filter buttons in the library', async () => {
      render(<SettingsLibraryTab />);
      expect(await screen.findByText('IITMRP Annual Report.pdf')).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /^all files$/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /^pdf$/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /^csv$/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /^docx$/i })).not.toBeInTheDocument();
    });

    it('does not display redundant "Indexed" or "Indexed in Graph" text badges', async () => {
      render(<SettingsLibraryTab />);
      expect(await screen.findByText('IITMRP Annual Report.pdf')).toBeInTheDocument();
      expect(screen.queryByText(/^Indexed$/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Indexed in Graph/i)).not.toBeInTheDocument();
    });

    it('blurs unindexed processing documents with a gentle parsing indicator', async () => {
      render(<SettingsLibraryTab />);
      const unindexedDoc = await screen.findByText('Clinical_Trial_Genomics_Raw.pdf');
      expect(unindexedDoc).toBeInTheDocument();
      expect(screen.getByText('Parsing...')).toBeInTheDocument();

      const card = unindexedDoc.closest('.filter');
      expect(card).not.toBeNull();
      expect(card?.className).toContain('blur-[1.5px]');
      expect(card?.className).toContain('opacity-65');
    });

    it('calls sourceService.deleteDocument and prunes GraphRAG when deleting an item from Library', async () => {
      const deleteSpy = vi.spyOn(sourceService, 'deleteDocument').mockResolvedValueOnce({
        data: {
          status: 'success',
          filename: 'ARE-2016-17.pdf',
          documents: [],
          total_count: 0,
        },
        error: null,
        isMock: false,
        status: 200,
      });

      render(<SettingsLibraryTab />);
      const areDoc = await screen.findByText('ARE-2016-17.pdf');
      expect(areDoc).toBeInTheDocument();

      const areCard = areDoc.closest('div.group');
      const deleteBtn = areCard?.querySelector('button[title*="Delete"]') as HTMLButtonElement;
      expect(deleteBtn).not.toBeNull();

      await act(async () => {
        fireEvent.click(deleteBtn);
      });

      expect(deleteSpy).toHaveBeenCalledWith('ARE-2016-17.pdf');
      deleteSpy.mockRestore();
    });

    it('does not render delete button on unindexed processing items until full circle parsing completes', async () => {
      render(<SettingsLibraryTab />);
      const unindexedDoc = await screen.findByText('Clinical_Trial_Genomics_Raw.pdf');
      const card = unindexedDoc.closest('div.group');
      const deleteBtn = card?.querySelector('button[title*="Delete"]');
      expect(deleteBtn).toBeNull();
    });
  });

  describe('SettingsDataControlTab', () => {
    const mockSessions: ChatSession[] = [
      {
        id: 'sess-1',
        title: 'University Comparison Framework Blueprint',
        timestamp: '10m ago',
        messages: [{ role: 'user', text: 'Compare metrics' }],
      },
      {
        id: 'sess-2',
        title: 'Bioinformatics Gene Vectors',
        timestamp: '1h ago',
        messages: [{ role: 'user', text: 'Inspect genes' }],
      },
    ];

    it('displays the 5 required data control actions', () => {
      render(
        <SettingsDataControlTab
          sessions={mockSessions}
          onSessionsChange={vi.fn()}
          onDeleteAllChats={vi.fn()}
        />
      );

      expect(screen.getByText('Shared links')).toBeInTheDocument();
      expect(screen.getByText('Archive chats')).toBeInTheDocument();
      expect(screen.getByText('Archive all chats')).toBeInTheDocument();
      expect(screen.getByText('Delete all chats')).toBeInTheDocument();
      expect(screen.getAllByText('Export data').length).toBeGreaterThan(0);
    });

    it('opens and closes Delete All Chats confirmation popup on clicking outside the dialog', () => {
      render(
        <SettingsDataControlTab
          sessions={mockSessions}
          onSessionsChange={vi.fn()}
          onDeleteAllChats={vi.fn()}
        />
      );

      // Open Delete All modal
      const deleteAllBtn = screen.getByRole('button', { name: 'Delete all' });
      fireEvent.click(deleteAllBtn);

      // Confirmation popup is displayed
      expect(screen.getByText('Delete all chats?')).toBeInTheDocument();
      expect(screen.getByText(/Are you sure you want to permanently delete all/)).toBeInTheDocument();

      // Clicking dialog itself does NOT close the modal
      const dialog = document.getElementById('deleteAllModalDialog');
      expect(dialog).not.toBeNull();
      fireEvent.click(dialog!);
      expect(screen.getByText('Delete all chats?')).toBeInTheDocument();

      // Clicking outside on the backdrop closes the delete all popup
      const backdrop = document.getElementById('deleteAllModalBackdrop');
      expect(backdrop).not.toBeNull();
      fireEvent.click(backdrop!);

      // Popup is closed
      expect(screen.queryByText('Delete all chats?')).not.toBeInTheDocument();
    });

    it('calls onDeleteAllChats and clears sessions upon confirmation', () => {
      const handleSessionsChange = vi.fn();
      const handleDeleteAllChats = vi.fn();

      render(
        <SettingsDataControlTab
          sessions={mockSessions}
          onSessionsChange={handleSessionsChange}
          onDeleteAllChats={handleDeleteAllChats}
        />
      );

      // Open Delete All modal
      const deleteAllBtn = screen.getByRole('button', { name: 'Delete all' });
      fireEvent.click(deleteAllBtn);

      // Confirm deletion inside modal dialog
      const confirmDeleteBtn = screen.getByRole('button', { name: 'Delete all chats' });
      fireEvent.click(confirmDeleteBtn);

      expect(handleDeleteAllChats).toHaveBeenCalledTimes(1);
      expect(handleSessionsChange).toHaveBeenCalledWith([]);
      expect(screen.queryByText('Delete all chats?')).not.toBeInTheDocument();
    });

    it('opens shared links manage popup and allows copying links', () => {
      render(
        <SettingsDataControlTab
          sessions={mockSessions}
          onSessionsChange={vi.fn()}
          onDeleteAllChats={vi.fn()}
        />
      );

      const manageButtons = screen.getAllByRole('button', { name: /manage/i });
      fireEvent.click(manageButtons[0]); // First manage button is Shared Links

      expect(screen.getByText('Shared Links')).toBeInTheDocument();
      expect(screen.getByText(/Anyone with these links can view/)).toBeInTheDocument();

      // Clicking backdrop closes the shared links popup
      const backdrop = document.getElementById('sharedLinksModalBackdrop');
      expect(backdrop).not.toBeNull();
      fireEvent.click(backdrop!);

      expect(screen.queryByText('Shared Links')).not.toBeInTheDocument();
    });

    it('opens export data popup and allows format selection', () => {
      render(
        <SettingsDataControlTab
          sessions={mockSessions}
          onSessionsChange={vi.fn()}
          onDeleteAllChats={vi.fn()}
        />
      );

      const exportBtn = screen.getByRole('button', { name: 'Export' });
      fireEvent.click(exportBtn);

      const headings = screen.getAllByRole('heading', { name: 'Export data' });
      expect(headings.length).toBe(2);
      expect(screen.getByText('JSON Data')).toBeInTheDocument();
      expect(screen.getByText('Markdown')).toBeInTheDocument();

      // Switch format to Markdown
      fireEvent.click(screen.getByText('Markdown'));
      expect(screen.getByText('Readable text')).toBeInTheDocument();

      // Clicking backdrop closes export modal
      const backdrop = document.getElementById('exportModalBackdrop');
      expect(backdrop).not.toBeNull();
      fireEvent.click(backdrop!);

      expect(screen.queryByText('JSON Data')).not.toBeInTheDocument();
    });
  });
});
