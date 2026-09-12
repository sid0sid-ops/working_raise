import { Citation } from '../types';

export interface CitationToken {
  type: 'text' | 'citation';
  content: string;
  citationIndex?: number;
  citation?: Citation;
}

/**
 * Parses markdown text containing bracketed citation markers like [1], [2]
 * and matches them against the provided citations array.
 */
export function parseCitations(
  text: string,
  citations: Citation[] = []
): CitationToken[] {
  if (!text) return [];

  // Create lookup map by citation_index
  const citationMap = new Map<number, Citation>();
  for (const c of citations) {
    citationMap.set(c.citation_index, c);
  }

  const tokens: CitationToken[] = [];
  // Regex to match [1], [2], etc.
  const citationRegex = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = citationRegex.exec(text)) !== null) {
    const matchStart = match.index;
    const matchEnd = citationRegex.lastIndex;

    // Push preceding text segment if non-empty
    if (matchStart > lastIndex) {
      tokens.push({
        type: 'text',
        content: text.substring(lastIndex, matchStart),
      });
    }

    const citationIndex = parseInt(match[1], 10);
    const matchedCitation = citationMap.get(citationIndex);

    tokens.push({
      type: 'citation',
      content: match[0],
      citationIndex,
      citation: matchedCitation,
    });

    lastIndex = matchEnd;
  }

  // Push any remaining text segment
  if (lastIndex < text.length) {
    tokens.push({
      type: 'text',
      content: text.substring(lastIndex),
    });
  }

  return tokens;
}

export interface CleanRagResponseResult {
  cleanText: string;
  citations: Citation[];
}

/**
 * Robust cleaner and normalizer for RAG responses.
 * 1. Strips non-printable control characters (\x00-\x08\x0B\x0C\x0E-\x1F\x7F) like backspaces from OCR/PDF extraction.
 * 2. Unpacks verbose in-text citations like `(Annual Report.pdf, Page 8) [1]:` into clean `[1]` citation markers.
 * 3. Enriches and synchronizes the citations array with filenames and page numbers discovered in text.
 * 4. Ensures proper line breaks and paragraphs around bullet lists (•) and numbered items.
 * 5. Structures list items with distinct headings and readable indented excerpt blocks.
 */
export function cleanRagResponseText(
  rawText: string,
  initialCitations: Citation[] = []
): CleanRagResponseResult {
  if (!rawText) return { cleanText: '', citations: [] };

  // 1. Strip non-printable control characters (except \t, \n, \r)
  let text = rawText.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');

  // Strip literal escaped control character sequences (e.g. \x08, \u0008)
  text = text.replace(/\\x0[0-8bBcCeEfF]|\\x1[0-9a-fA-F]|\\x7[fF]|\\u000[0-8bBcCeEfF]|\\u001[0-9a-fA-F]/g, '');

  // 2. Normalize newlines
  text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  // 3. Collect existing citations
  const citMap = new Map<number, Citation>();
  let maxIndex = 0;
  for (const c of initialCitations) {
    if (typeof c.citation_index === 'number') {
      citMap.set(c.citation_index, { ...c });
      if (c.citation_index > maxIndex) maxIndex = c.citation_index;
    }
  }

  let nextAllocIndex = maxIndex + 1;

  // 4. Extract and clean verbose parenthetical in-text citations
  const verboseCitationRegex = /(?:\((?:[^()\n]*?\.(?:pdf|docx?|txt|md|xlsx?)[^()\n]*?,\s*(?:page|p\.?)\s*(\d+)[^()\n]*?|(?:page|p\.?)\s*(\d+)[^()\n]*?,\s*[^()\n]*?\.(?:pdf|docx?|txt|md|xlsx?)[^()\n]*?)\)\s*(?:\[(\d+)\])?|\[(\d+)\]\s*\((?:[^()\n]*?\.(?:pdf|docx?|txt|md|xlsx?)[^()\n]*?,\s*(?:page|p\.?)\s*(\d+)[^()\n]*?|(?:page|p\.?)\s*(\d+)[^()\n]*?,\s*[^()\n]*?\.(?:pdf|docx?|txt|md|xlsx?)[^()\n]*?)\)|\((?:[^()\n]*?\.(?:pdf|docx?|txt|md|xlsx?)[^()\n]*?)\)\s*\[(\d+)\]|\((?:page|p\.?)\s*(\d+)[^()\n]*?\)\s*\[(\d+)\]|\(([^()\n]+?\.(?:pdf|docx?|txt|md|xlsx?)\s*,\s*(?:page|p\.?)\s*(\d+)[^()\n]*?)\))/gi;

  text = text.replace(verboseCitationRegex, (fullMatch) => {
    const numMatch = fullMatch.match(/\[(\d+)\]/);
    const fileMatch = fullMatch.match(/([a-zA-Z0-9_\- .]+\.(?:pdf|docx?|txt|md|xlsx?))/i);
    const pageMatch = fullMatch.match(/(?:page|p\.?)\s*(\d+)/i);

    const explicitIdx = numMatch ? parseInt(numMatch[1], 10) : null;
    const idx = explicitIdx || nextAllocIndex++;
    if (idx >= nextAllocIndex) nextAllocIndex = idx + 1;

    const filename = fileMatch ? fileMatch[1].trim() : '';
    const page = pageMatch ? parseInt(pageMatch[1], 10) : 1;

    if (!citMap.has(idx)) {
      citMap.set(idx, {
        citation_index: idx,
        pdf_filename: filename,
        primary_page: page,
        chunk_id: `extracted-${idx}`,
        document_id: filename || `doc-${idx}`,
        heading: '',
        plain_text: '',
        university: 'IIT Madras',
        similarity: 1.0,
      });
    } else {
      const existing = citMap.get(idx)!;
      if (filename && !existing.pdf_filename) existing.pdf_filename = filename;
      if (page && (!existing.primary_page || existing.primary_page <= 1)) existing.primary_page = page;
    }

    return ` [${idx}] `;
  });

  // Normalize spacing around citation brackets: " [1] :" -> " [1]:"
  text = text.replace(/[ \t]+(\[\d+\])/g, ' $1');
  text = text.replace(/(\[\d+\])\s*:/g, '$1:');

  // Separate bullets onto distinct lines (including glued bullets without space)
  text = text.replace(/([^\n])\s*•\s*/g, '$1\n\n• ');
  text = text.replace(/\s*•\s*/g, '\n\n• ').trim();

  // Support standard Markdown hyphens (- ) and asterisks (* ) as well
  text = text.replace(/([^\n])\n(- \*\*)/g, '$1\n\n$2');
  text = text.replace(/([^\n])\n(-\s+)/g, '$1\n\n$2');
  text = text.replace(/([^\n])\n(\*\s+)/g, '$1\n\n$2');
  text = text.replace(/([^\n])\s*-\s+\*\*/g, '$1\n\n- **');

  // Clean title + citation + colon followed by space(s) into clean indented layout
  text = text.replace(/([•\-])\s*(\*\*[^*]+\*\*)\s*(\[\d+\])?\s*[:—–-]?\s+/g, (_, bullet, title, cit) => {
    return `${bullet} ${title}${cit ? ` ${cit}` : ''}\n  `;
  });

  // Separate numbered lists that were inline (e.g., "Intro: 1. **Title**")
  text = text.replace(/([.:;!?])\s+(\d+\.)\s+\*\*/g, '$1\n\n$2 **');
  text = text.replace(/([^\n])\n(\d+\.\s+\*\*)/g, '$1\n\n$2');

  // Strip trailing whitespace per line and collapse 3+ consecutive linebreaks to 2
  text = text.replace(/[ \t]+$/gm, '');
  text = text.replace(/\n{3,}/g, '\n\n');

  return { cleanText: text, citations: Array.from(citMap.values()) };
}

