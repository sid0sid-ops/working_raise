import { describe, it, expect } from 'vitest';
import { parseCitations, cleanRagResponseText } from '../utils/citationParser';
import { Citation } from '../types';

describe('Citation Parser Utility', () => {
  const mockCitations: Citation[] = [
    {
      citation_index: 1,
      chunk_id: 'chk_1',
      document_id: 'doc_1',
      pdf_filename: 'Report_A.pdf',
      primary_page: 14,
      heading: 'Introduction',
      plain_text: 'Supporting text for citation 1',
      university: 'IIT Madras',
      similarity: 0.95,
    },
    {
      citation_index: 2,
      chunk_id: 'chk_2',
      document_id: 'doc_1',
      pdf_filename: 'Report_A.pdf',
      primary_page: 18,
      heading: 'Results',
      plain_text: 'Supporting text for citation 2',
      university: 'IIT Madras',
      similarity: 0.88,
    },
  ];

  it('parses text without citations as a single text token', () => {
    const text = 'This is plain text without citations.';
    const tokens = parseCitations(text, mockCitations);
    expect(tokens.length).toBe(1);
    expect(tokens[0].type).toBe('text');
    expect(tokens[0].content).toBe(text);
  });

  it('correctly extracts single citation marker [1] and matches metadata', () => {
    const text = 'XYMA Analytics is a deep-tech startup [1].';
    const tokens = parseCitations(text, mockCitations);

    expect(tokens.length).toBe(3);
    expect(tokens[0].type).toBe('text');
    expect(tokens[0].content).toBe('XYMA Analytics is a deep-tech startup ');

    expect(tokens[1].type).toBe('citation');
    expect(tokens[1].citationIndex).toBe(1);
    expect(tokens[1].citation?.pdf_filename).toBe('Report_A.pdf');
    expect(tokens[1].citation?.primary_page).toBe(14);

    expect(tokens[2].type).toBe('text');
    expect(tokens[2].content).toBe('.');
  });

  it('handles multiple inline citations [1] and [2]', () => {
    const text = 'First claim [1] and second claim [2].';
    const tokens = parseCitations(text, mockCitations);

    const citationTokens = tokens.filter((t) => t.type === 'citation');
    expect(citationTokens.length).toBe(2);
    expect(citationTokens[0].citationIndex).toBe(1);
    expect(citationTokens[1].citationIndex).toBe(2);
  });

  it('gracefully handles citations without matching metadata', () => {
    const text = 'Unmatched claim [99].';
    const tokens = parseCitations(text, mockCitations);

    expect(tokens.length).toBe(3);
    expect(tokens[1].type).toBe('citation');
    expect(tokens[1].citationIndex).toBe(99);
    expect(tokens[1].citation).toBeUndefined();
  });
});

describe('cleanRagResponseText Normalizer', () => {
  it('unpacks verbose parenthetical citations into clean citation tokens and extracts metadata', () => {
    const raw =
      'Based on reports:• **Director’s Report (Part 1)** (Annual Report 2024-25 final upload.pdf, Page 8) [1]:  Chief Guest Shri Ajit Dovalji...• **1. Director’s Report (Part 2)** (Annual Report 2024-25 final upload.pdf, Page 13) [2]:  Rajes Ranjan';

    const result = cleanRagResponseText(raw);

    // Text should have clean linebreaks before bullets
    expect(result.cleanText).toContain('• **Director’s Report (Part 1)** [1]');
    expect(result.cleanText).toContain('• **1. Director’s Report (Part 2)** [2]');

    // Inlined verbose PDF filename should be removed from text prose
    expect(result.cleanText).not.toContain('(Annual Report 2024-25 final upload.pdf, Page 8)');
    expect(result.cleanText).not.toContain('(Annual Report 2024-25 final upload.pdf, Page 13)');

    // Citations metadata should be extracted
    expect(result.citations.length).toBe(2);
    expect(result.citations[0].citation_index).toBe(1);
    expect(result.citations[0].pdf_filename).toBe('Annual Report 2024-25 final upload.pdf');
    expect(result.citations[0].primary_page).toBe(8);

    expect(result.citations[1].citation_index).toBe(2);
    expect(result.citations[1].pdf_filename).toBe('Annual Report 2024-25 final upload.pdf');
    expect(result.citations[1].primary_page).toBe(13);
  });

  it('assigns incrementing citation indices when [N] is omitted by backend', () => {
    const raw =
      '• **1. Director’s Report (Part 3)** (Annual Report 2024-25 final upload.pdf, Page 17) actionable research';
    const result = cleanRagResponseText(raw);

    expect(result.cleanText).toContain('[1]');
    expect(result.cleanText).not.toContain('(Annual Report 2024-25 final upload.pdf, Page 17)');
    expect(result.citations[0].primary_page).toBe(17);
  });

  it('strips non-printable control characters such as backspace \x08', () => {
    const raw = '1. Director’s Report\x08 (Part 3)';
    const result = cleanRagResponseText(raw);
    expect(result.cleanText).toBe('1. Director’s Report (Part 3)');
    expect(result.cleanText).not.toContain('\x08');
  });
});
