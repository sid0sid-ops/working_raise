import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AnswerMarkdown } from '../components/chat/AnswerMarkdown';
import { Citation } from '../types';

describe('AnswerMarkdown Rich Formatting & Visual Layout', () => {
  it('renders numbered lists with styled numeric badges', () => {
    const content = `1. **IIT Madras:** First research park\n2. **IIT Bombay:** Second innovation hub`;
    render(<AnswerMarkdown content={content} />);

    expect(screen.getByText('1')).toBeDefined();
    expect(screen.getByText('2')).toBeDefined();
    expect(screen.getByText(/IIT Madras:/i)).toBeDefined();
    expect(screen.getByText(/IIT Bombay:/i)).toBeDefined();
  });

  it('renders unordered bullet lists and nested sub-bullets', () => {
    const content = `* High-priority findings:\n  * Nested point alpha\n  * Nested point beta\n* Secondary findings`;
    render(<AnswerMarkdown content={content} />);

    expect(screen.getByText(/High-priority findings:/i)).toBeDefined();
    expect(screen.getByText(/Nested point alpha/i)).toBeDefined();
    expect(screen.getByText(/Nested point beta/i)).toBeDefined();
    expect(screen.getByText(/Secondary findings/i)).toBeDefined();
  });

  it('renders headings with correct hierarchy and styling', () => {
    const content = `# Top Level Title\n## Secondary Title\n### Tertiary Title\n#### Micro Title`;
    render(<AnswerMarkdown content={content} />);

    expect(screen.getByText('Top Level Title')).toBeDefined();
    expect(screen.getByText('Secondary Title')).toBeDefined();
    expect(screen.getByText('Tertiary Title')).toBeDefined();
    expect(screen.getByText('Micro Title')).toBeDefined();
  });

  it('renders code blocks with language badge and copy action', () => {
    const writeTextMock = vi.fn();
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    const content = '```typescript\nconst greeting: string = "hello world";\n```';
    render(<AnswerMarkdown content={content} />);

    expect(screen.getByText('typescript')).toBeDefined();
    expect(screen.getByText(/const greeting: string/i)).toBeDefined();

    const copyBtn = screen.getByRole('button', { name: /copy/i });
    fireEvent.click(copyBtn);
    expect(writeTextMock).toHaveBeenCalledWith('const greeting: string = "hello world";');
  });

  it('renders markdown tables with headers and cell rows', () => {
    const content = `| Metric | IIT Madras | IIT Delhi |\n| :--- | :--- | :--- |\n| Incubations | 380+ | 250+ |\n| Patents | 1200+ | 900+ |`;
    render(<AnswerMarkdown content={content} />);

    expect(screen.getByText('Metric')).toBeDefined();
    expect(screen.getByText('IIT Madras')).toBeDefined();
    expect(screen.getByText('Incubations')).toBeDefined();
    expect(screen.getByText('380+')).toBeDefined();
  });

  it('renders blockquotes and callouts cleanly', () => {
    const content = `> This is an excerpt from the research paper.\n\n**Note:** Research parks drive regional innovation.\n\n**Warning:** Incomplete data for 2024.`;
    render(<AnswerMarkdown content={content} />);

    expect(screen.getByText(/This is an excerpt from the research paper/i)).toBeDefined();
    expect(screen.getByText(/Research parks drive regional innovation/i)).toBeDefined();
    expect(screen.getByText(/Incomplete data for 2024/i)).toBeDefined();
  });

  it('renders inline code, bold, and citations inside bold titles', () => {
    const citations: Citation[] = [
      {
        citation_index: 1,
        chunk_id: 'chunk-1',
        document_id: 'doc-1',
        plain_text: 'Research park report',
        primary_page: 5,
        heading: 'Introduction',
        pdf_filename: 'report.pdf',
        university: 'IIT Madras',
        similarity: 0.95,
      },
    ];

    const content = 'The system uses `hybrid_search` to find **XYMA Analytics [1]** sensor data.';
    render(<AnswerMarkdown content={content} citations={citations} showCitations={true} />);

    expect(screen.getByText('hybrid_search')).toBeDefined();
    expect(screen.getByText(/XYMA Analytics/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /\[1\]/i })).toBeDefined();
  });

  it('formats messy RAG response with inline bullets, extracts in-text citations, and shows hover card', () => {
    const rawMessyResponse =
      'Based on the verified excerpts from your uploaded institutional reports:• **Director’s Report (Part 1)** (Annual Report 2024-25 final upload.pdf, Page 8) [1]:  Chief Guest Shri Ajit Dovalji, Kirti Chakra and National Security Advisor• **1. Director’s Report (Part 2)** (Annual Report 2024-25 final upload.pdf, Page 13) [2]:  At the Department of Mechanical Engineering, Rajes Ranjan';

    render(<AnswerMarkdown content={rawMessyResponse} showCitations={true} />);

    // 1. Title and content must be cleanly separated and rendered
    expect(screen.getByText(/Director’s Report \(Part 1\)/i)).toBeDefined();
    expect(screen.getByText(/Chief Guest Shri Ajit Dovalji/i)).toBeDefined();
    expect(screen.getByText(/1\. Director’s Report \(Part 2\)/i)).toBeDefined();
    expect(screen.getByText(/Rajes Ranjan/i)).toBeDefined();

    // 2. The raw messy inlined filenames must be stripped from the body prose
    expect(screen.queryByText(/\(Annual Report 2024-25 final upload\.pdf, Page 8\)/)).toBeNull();
    expect(screen.queryByText(/\(Annual Report 2024-25 final upload\.pdf, Page 13\)/)).toBeNull();

    // 3. Badges [1] and [2] must be rendered
    const badge1 = screen.getByRole('button', { name: /Citation \[1\]/i });
    expect(badge1).toBeDefined();

    // 4. Hovering over badge [1] triggers the rich popover tooltip
    fireEvent.mouseEnter(badge1);
    expect(screen.getByRole('tooltip')).toBeDefined();
    expect(screen.getAllByText(/Annual Report 2024-25 final upload\.pdf/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/p\. 8/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/View PDF/i)).toBeDefined();

    // 5. Leaving badge closes tooltip after delay
    fireEvent.mouseLeave(badge1);
  });
});

