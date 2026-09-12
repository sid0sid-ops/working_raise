import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InlinePdfViewer } from '../components/citations/InlinePdfViewer';
import { SourcesDrawer } from '../features/raise/components/SourcesDrawer';
import { Citation } from '../types';

describe('Citation Navigation & PDF Deep Linking', () => {
  const sampleCitation: Citation = {
    citation_index: 1,
    chunk_id: 'doc-chunk-42',
    document_id: 'doc-42',
    pdf_filename: 'IITM_Research_Report.pdf',
    primary_page: 8,
    heading: 'Innovation Metrics',
    plain_text: 'Over 380 deep-tech startups were incubated in the research park.',
    university: 'IIT Madras',
    similarity: 0.96,
  };

  it('renders InlinePdfViewer initialized to the cited physical page number', () => {
    render(<InlinePdfViewer citation={sampleCitation} />);

    expect(screen.getByText('IITM_Research_Report.pdf')).toBeInTheDocument();
    expect(screen.getByTestId('active-page-badge')).toHaveTextContent('Page 8');
    expect(screen.getByText(/Over 380 deep-tech startups/i)).toBeInTheDocument();
  });

  it('navigates to next page and previous page in InlinePdfViewer', () => {
    render(<InlinePdfViewer citation={sampleCitation} />);

    const nextBtn = screen.getByTitle('Next Page');
    fireEvent.click(nextBtn);

    expect(screen.getByTestId('active-page-badge')).toHaveTextContent('Page 9');
    expect(screen.getByText(/Cited Page \(8\)/i)).toBeInTheDocument();

    const prevBtn = screen.getByTitle('Previous Page');
    fireEvent.click(prevBtn);
    expect(screen.getByTestId('active-page-badge')).toHaveTextContent('Page 8');
  });

  it('returns to cited page when clicking return button after navigating away', () => {
    render(<InlinePdfViewer citation={sampleCitation} />);

    const nextBtn = screen.getByTitle('Next Page');
    fireEvent.click(nextBtn);
    fireEvent.click(nextBtn);
    expect(screen.getByTestId('active-page-badge')).toHaveTextContent('Page 10');

    const returnBtn = screen.getByText(/Cited Page \(8\)/i);
    fireEvent.click(returnBtn);
    expect(screen.getByTestId('active-page-badge')).toHaveTextContent('Page 8');
  });

  it('renders View PDF button in SourcesDrawer and calls onViewPdf when clicked', () => {
    const onViewPdfMock = vi.fn();
    const sourceDocs = [
      {
        id: 'doc-1',
        name: 'Annual_Report_2023.pdf',
        size: '2.4 MB',
        pages: 24,
        selected: true,
        color: 'indigo' as const,
      },
    ];

    render(
      <SourcesDrawer
        isOpen={true}
        onClose={vi.fn()}
        sourceDocs={sourceDocs}
        activeSourcesCount={1}
        sourceFilter=""
        setSourceFilter={vi.fn()}
        addSourceMenuOpen={null}
        setAddSourceMenuOpen={vi.fn()}
        onBrowseFileClick={vi.fn()}
        onOpenLibraryPicker={vi.fn()}
        isDocReady={() => true}
        onToggleSourceDoc={vi.fn()}
        onDeleteSourceDoc={vi.fn()}
        onViewPdf={onViewPdfMock}
      />
    );

    const viewPdfBtn = screen.getByLabelText(/View Annual_Report_2023\.pdf in PDF Viewer/i);
    expect(viewPdfBtn).toBeInTheDocument();

    fireEvent.click(viewPdfBtn);
    expect(onViewPdfMock).toHaveBeenCalledWith('Annual_Report_2023.pdf', 1);
  });
});
