import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LibraryPickerModal } from '../components/library/LibraryPickerModal';
import { sourceService } from '../services/SourceService';

describe('LibraryPickerModal', () => {
  const mockDocs = [
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
      filename: 'Clinical_Trial_Genomics_Raw.pdf',
      pages: 8,
      size_mb: 1.8,
      chunks_count: 16,
      status: 'processing' as const,
    },
  ];

  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('does not render when isOpen is false', () => {
    render(
      <LibraryPickerModal
        isOpen={false}
        onClose={vi.fn()}
        onSelectDocument={vi.fn()}
        attachedDocNames={[]}
        onOpenUploadFromPC={vi.fn()}
      />
    );
    expect(screen.queryByText(/Select from Knowledge Base Library/i)).not.toBeInTheDocument();
  });

  it('renders clean empty state when backend reports 0 documents', async () => {
    vi.spyOn(sourceService, 'getDocuments').mockResolvedValueOnce({
      data: { documents: [], total_count: 0 },
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

    expect(screen.getByText('Select from Knowledge Base Library')).toBeInTheDocument();
    expect(await screen.findByText('Your Library is currently empty')).toBeInTheDocument();
    expect(
      screen.getByText(/No documents have been indexed into the GraphRAG knowledge base yet/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Upload Document from PC/i })).toBeInTheDocument();
  });

  it('renders modal with search, type filters, and populated documents from backend', async () => {
    vi.spyOn(sourceService, 'getDocuments').mockResolvedValueOnce({
      data: { documents: mockDocs, total_count: mockDocs.length },
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

    expect(screen.getByText('Select from Knowledge Base Library')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search library documents...')).toBeInTheDocument();

    expect(await screen.findByText('IITMRP Annual Report.pdf')).toBeInTheDocument();
    expect(screen.getByText('Bioinformatics_Gene_Vectors.csv')).toBeInTheDocument();
  });

  it('calls onSelectDocument when user clicks Attach on an indexed document', async () => {
    vi.spyOn(sourceService, 'getDocuments').mockResolvedValueOnce({
      data: { documents: mockDocs, total_count: mockDocs.length },
      error: null,
      isMock: false,
      status: 200,
    });

    const onSelectSpy = vi.fn();
    render(
      <LibraryPickerModal
        isOpen={true}
        onClose={vi.fn()}
        onSelectDocument={onSelectSpy}
        attachedDocNames={[]}
        onOpenUploadFromPC={vi.fn()}
      />
    );

    expect(await screen.findByText('IITMRP Annual Report.pdf')).toBeInTheDocument();
    const attachButtons = screen.getAllByRole('button', { name: /Attach/i });
    expect(attachButtons.length).toBeGreaterThan(0);

    fireEvent.click(attachButtons[0]);
    expect(onSelectSpy).toHaveBeenCalledTimes(1);
    expect(onSelectSpy).toHaveBeenCalledWith(expect.objectContaining({ name: expect.any(String) }));
  });

  it('shows Attached badge for documents already present in the active chat session', async () => {
    vi.spyOn(sourceService, 'getDocuments').mockResolvedValueOnce({
      data: { documents: mockDocs, total_count: mockDocs.length },
      error: null,
      isMock: false,
      status: 200,
    });

    render(
      <LibraryPickerModal
        isOpen={true}
        onClose={vi.fn()}
        onSelectDocument={vi.fn()}
        attachedDocNames={['IITMRP Annual Report.pdf']}
        onOpenUploadFromPC={vi.fn()}
      />
    );

    expect(await screen.findByText('Attached')).toBeInTheDocument();
  });

  it('blurs unindexed processing documents with a Parsing... indicator', async () => {
    vi.spyOn(sourceService, 'getDocuments').mockResolvedValueOnce({
      data: { documents: mockDocs, total_count: mockDocs.length },
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

    const processingDoc = await screen.findByText('Clinical_Trial_Genomics_Raw.pdf');
    expect(processingDoc).toBeInTheDocument();

    const card = processingDoc.closest('.filter');
    expect(card).not.toBeNull();
    expect(card?.className).toContain('blur-[1.5px]');
    expect(card?.className).toContain('opacity-60');
  });

  it('calls onOpenUploadFromPC when clicking the browse from PC link', () => {
    const onOpenPCSpy = vi.fn();
    const onCloseSpy = vi.fn();
    render(
      <LibraryPickerModal
        isOpen={true}
        onClose={onCloseSpy}
        onSelectDocument={vi.fn()}
        attachedDocNames={[]}
        onOpenUploadFromPC={onOpenPCSpy}
      />
    );

    const pcLink = screen.getByText(/Need a new file\? Browse from PC/i);
    fireEvent.click(pcLink);

    expect(onCloseSpy).toHaveBeenCalled();
    expect(onOpenPCSpy).toHaveBeenCalled();
  });

  it('calls onClose when clicking Done or Close (X)', () => {
    const onCloseSpy = vi.fn();
    render(
      <LibraryPickerModal
        isOpen={true}
        onClose={onCloseSpy}
        onSelectDocument={vi.fn()}
        attachedDocNames={[]}
        onOpenUploadFromPC={vi.fn()}
      />
    );

    const doneButton = screen.getByRole('button', { name: /Done/i });
    fireEvent.click(doneButton);
    expect(onCloseSpy).toHaveBeenCalledTimes(1);

    const closeX = screen.getByLabelText('Close');
    fireEvent.click(closeX);
    expect(onCloseSpy).toHaveBeenCalledTimes(2);
  });
});
