import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExportResponseDropdown } from '../components/chat/ExportResponseDropdown';
import * as exportUtils from '../utils/exportFormats';

describe('ExportResponseDropdown Component', () => {
  const mockQuery = 'What are the top deep tech spin-offs?';
  const mockAnswer = '### 1. XYMA Analytics\nSpecialized in sensors.';
  const mockResponse = {
    query: mockQuery,
    grounded_answer: mockAnswer,
    traceability_score: 0.95,
  };

  beforeEach(() => {
    vi.spyOn(exportUtils, 'exportAsMarkdown').mockImplementation(() => {});
    vi.spyOn(exportUtils, 'exportAsPdf').mockImplementation(() => {});
    vi.spyOn(exportUtils, 'exportAsJson').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders trigger button and toggles dropdown on click without print button', () => {
    render(
      <ExportResponseDropdown
        query={mockQuery}
        answerText={mockAnswer}
        response={mockResponse}
      />
    );

    const triggerBtn = screen.getByRole('button', { name: /export response/i });
    expect(triggerBtn).toBeDefined();

    // Menu initially closed
    expect(screen.queryByTestId('export-dropdown-menu')).toBeNull();

    // Click to open
    fireEvent.click(triggerBtn);
    expect(screen.getByTestId('export-dropdown-menu')).toBeDefined();
    expect(screen.getByText('Markdown (.md)')).toBeDefined();
    expect(screen.getByText('PDF Report (.pdf)')).toBeDefined();
    expect(screen.getByText('Developer JSON (.json)')).toBeDefined();

    // Print view / Save as PDF button must NOT be present
    expect(screen.queryByText(/print/i)).toBeNull();
    expect(screen.queryByText(/save as pdf/i)).toBeNull();
  });

  it('calls exportAsMarkdown when Markdown option is selected', () => {
    const onExportSpy = vi.fn();
    render(
      <ExportResponseDropdown
        query={mockQuery}
        answerText={mockAnswer}
        response={mockResponse}
        onExport={onExportSpy}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /export response/i }));
    fireEvent.click(screen.getByText('Markdown (.md)'));

    expect(exportUtils.exportAsMarkdown).toHaveBeenCalledWith(
      mockQuery,
      mockAnswer,
      mockResponse
    );
    expect(onExportSpy).toHaveBeenCalledWith('md');
    // Closes menu after export
    expect(screen.queryByTestId('export-dropdown-menu')).toBeNull();
  });

  it('calls exportAsPdf when PDF option is selected', () => {
    const onExportSpy = vi.fn();
    render(
      <ExportResponseDropdown
        query={mockQuery}
        answerText={mockAnswer}
        response={mockResponse}
        onExport={onExportSpy}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /export response/i }));
    fireEvent.click(screen.getByText('PDF Report (.pdf)'));

    expect(exportUtils.exportAsPdf).toHaveBeenCalledWith(
      mockQuery,
      mockAnswer,
      mockResponse
    );
    expect(onExportSpy).toHaveBeenCalledWith('pdf');
  });

  it('calls exportAsJson when JSON option is selected', () => {
    const onExportSpy = vi.fn();
    render(
      <ExportResponseDropdown
        query={mockQuery}
        answerText={mockAnswer}
        response={mockResponse}
        onExport={onExportSpy}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /export response/i }));
    fireEvent.click(screen.getByText('Developer JSON (.json)'));

    expect(exportUtils.exportAsJson).toHaveBeenCalledWith(
      mockQuery,
      mockAnswer,
      mockResponse
    );
    expect(onExportSpy).toHaveBeenCalledWith('json');
  });

  it('closes dropdown when Escape key is pressed', () => {
    render(
      <ExportResponseDropdown
        query={mockQuery}
        answerText={mockAnswer}
        response={mockResponse}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /export response/i }));
    expect(screen.getByTestId('export-dropdown-menu')).toBeDefined();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByTestId('export-dropdown-menu')).toBeNull();
  });
});
