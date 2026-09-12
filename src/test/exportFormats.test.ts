import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  copyMarkdownToClipboard,
  formatMarkdownReport,
  formatDeveloperJson,
  generatePdfBlob,
  generateReportHtml,
  exportAsMarkdown,
  exportAsJson,
  exportAsPdf,
  slugify,
  generateExportFilename,
} from '../utils/exportFormats';
import { SubgraphQueryResponse } from '../types';

const MOCK_RESPONSE: Partial<SubgraphQueryResponse> = {
  query: 'What deep-tech startups originate from IIT Madras research?',
  grounded_answer:
    '### 1. XYMA Analytics\n* **Faculty:** Founded under Prof. Krishnan Balasubramanian [1].\n* **Product:** Ultrasonic waveguide sensors [1].\n\n### 2. Mindgrove Technologies\n* **Faculty:** Mentored by Dept of Computer Science [2].',
  traceability_score: 0.94,
  quality_gate_decision: 'accept',
  execution_time: 1.85,
  latency_sec: 1.85,
  routing_strategy: 'vector_hybrid',
  query_type: 'factual',
  selected_tools: ['chromadb', 'neo4j'],
  citations: [
    {
      citation_index: 1,
      chunk_id: 'chk_xyma_16',
      document_id: 'doc_1',
      pdf_filename: 'IITMRP Annual Report.pdf',
      primary_page: 44,
      heading: 'Deep Tech Startups',
      plain_text: 'XYMA Analytics specializes in high-temperature ultrasonic waveguide sensors.',
      university: 'IIT Madras',
      similarity: 0.892,
    },
    {
      citation_index: 2,
      chunk_id: 'chk_mindgrove_03',
      document_id: 'doc_2',
      pdf_filename: 'Incubation Portfolio.pdf',
      primary_page: 12,
      heading: 'Semiconductors',
      plain_text: 'Mindgrove Technologies develops Shakti RISC-V based IoT system-on-chip.',
      university: 'IIT Madras',
      similarity: 0.841,
    },
  ],
  verified_claims: [
    {
      claim_id: 'CLM_001',
      text: 'XYMA Analytics was founded by Prof. Krishnan Balasubramanian',
      is_supported: true,
      status: 'SUPPORTED',
      extracted_numbers: [],
      matched_numbers: [],
      citations_found: [1],
      notes: [],
    },
  ],
  subgraph: {
    nodes: [
      { id: 'xyma', name: 'XYMA Analytics', label: 'Company', type: 'Company', provenance: {} },
      { id: 'iitm', name: 'IIT Madras', label: 'University', type: 'University', provenance: {} },
    ],
    edges: [
      { source: 'xyma', target: 'iitm', relationship: 'ORIGINATED_FROM', provenance: {} },
    ],
  },
};

describe('Export Formats Utility', () => {
  describe('slugify & filename generation', () => {
    it('creates sanitized slugs from queries', () => {
      expect(slugify('What is XYMA Analytics?!')).toBe('what-is-xyma-analytics');
      expect(slugify('   ')).toBe('research-response');
    });

    it('generates filename with current date and proper extension', () => {
      const fnMd = generateExportFilename('What is XYMA?', 'md');
      expect(fnMd).toMatch(/^raise-report-what-is-xyma-\d{4}-\d{2}-\d{2}\.md$/);

      const fnJson = generateExportFilename('What is XYMA?', 'json', 'raise-response');
      expect(fnJson).toMatch(/^raise-response-what-is-xyma-\d{4}-\d{2}-\d{2}\.json$/);

      const fnPdf = generateExportFilename('What is XYMA?', 'pdf');
      expect(fnPdf).toMatch(/^raise-report-what-is-xyma-\d{4}-\d{2}-\d{2}\.pdf$/);
    });
  });

  describe('copyMarkdownToClipboard', () => {
    const originalClipboard = navigator.clipboard;

    afterEach(() => {
      Object.defineProperty(navigator, 'clipboard', {
        value: originalClipboard,
        configurable: true,
      });
    });

    it('copies markdown text preserving headers, bullets, bolding, and citations via navigator.clipboard', async () => {
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: writeTextMock },
        configurable: true,
      });

      const markdownSample = '### Title\n* **Bold text** with [1] citation\n```json\n{"k":"v"}\n```';
      const success = await copyMarkdownToClipboard(markdownSample);

      expect(success).toBe(true);
      expect(writeTextMock).toHaveBeenCalledWith(markdownSample);
    });

    it('falls back to document.execCommand when navigator.clipboard is unavailable', async () => {
      Object.defineProperty(navigator, 'clipboard', {
        value: undefined,
        configurable: true,
      });

      const execCommandMock = vi.fn().mockReturnValue(true);
      document.execCommand = execCommandMock;

      const markdownSample = '# Header\n- Bullet 1\n- Bullet 2';
      const success = await copyMarkdownToClipboard(markdownSample);

      expect(success).toBe(true);
      expect(execCommandMock).toHaveBeenCalledWith('copy');
    });

    it('returns false on empty string', async () => {
      const success = await copyMarkdownToClipboard('');
      expect(success).toBe(false);
    });
  });

  describe('formatMarkdownReport', () => {
    it('generates a complete Markdown report with metadata, inquiry, grounded answer, and citations', () => {
      const md = formatMarkdownReport(
        MOCK_RESPONSE.query!,
        MOCK_RESPONSE.grounded_answer!,
        MOCK_RESPONSE
      );

      // Header
      expect(md).toContain('# RAISE Research Intelligence Report');
      expect(md).toContain('**Quality Gate:** `ACCEPT`');
      expect(md).toContain('**Traceability Score:** `0.94`');
      expect(md).toContain('**Latency:** `1.85s`');

      // Inquiry
      expect(md).toContain('## Research Inquiry');
      expect(md).toContain('> What deep-tech startups originate from IIT Madras research?');

      // Synthesis
      expect(md).toContain('## Grounded Synthesis & Findings');
      expect(md).toContain('### 1. XYMA Analytics');
      expect(md).toContain('Prof. Krishnan Balasubramanian');

      // Citations
      expect(md).toContain('## References & Grounded Citations');
      expect(md).toContain('### [1] IITMRP Annual Report.pdf (Page 44, IIT Madras)');
      expect(md).toContain('`chk_xyma_16`');
      expect(md).toContain('`0.892`');

      // Verified Claims
      expect(md).toContain('## Verified Claims & Fact Checks');
      expect(md).toContain('[x] **CLM_001:** XYMA Analytics was founded by Prof. Krishnan Balasubramanian');

      // Subgraph
      expect(md).toContain('## Subgraph Entity Context');
      expect(md).toContain('Identified **2 entities** and **1 relationships**');
    });
  });

  describe('formatDeveloperJson', () => {
    it('produces structured developer JSON with complete telemetry and raw response', () => {
      const json = formatDeveloperJson(
        MOCK_RESPONSE.query!,
        MOCK_RESPONSE.grounded_answer!,
        MOCK_RESPONSE
      );

      expect(json.export_version).toBe('1.0.0');
      expect(json.platform).toBe('RAISE Research Intelligence Platform');
      expect(json.query).toBe(MOCK_RESPONSE.query);
      expect(json.grounded_answer).toBe(MOCK_RESPONSE.grounded_answer);

      const meta = json.metadata as any;
      expect(meta.traceability_score).toBe(0.94);
      expect(meta.quality_gate_decision).toBe('accept');
      expect(meta.execution_time_seconds).toBe(1.85);

      expect(Array.isArray(json.citations)).toBe(true);
      expect((json.citations as any[]).length).toBe(2);

      expect(Array.isArray(json.verified_claims)).toBe(true);
      expect((json.subgraph as any).nodes.length).toBe(2);
    });
  });

  describe('generatePdfBlob', () => {
    async function readBlob(blob: Blob): Promise<string> {
      if (typeof blob.text === 'function') {
        return await blob.text();
      }
      return new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(reader.error);
        reader.readAsText(blob);
      });
    }

    it('generates a valid PDF 1.4 binary Blob with proper PDF headers and structure', async () => {
      const blob = generatePdfBlob(
        MOCK_RESPONSE.query!,
        MOCK_RESPONSE.grounded_answer!,
        MOCK_RESPONSE
      );

      expect(blob).toBeInstanceOf(Blob);
      expect(blob.type).toBe('application/pdf');
      expect(blob.size).toBeGreaterThan(500);

      const text = await readBlob(blob);

      // Verify PDF 1.4 standard magic bytes and structures
      expect(text.startsWith('%PDF-1.4')).toBe(true);
      expect(text).toContain('/Type /Catalog');
      expect(text).toContain('/Type /Pages');
      expect(text).toContain('/Type /Page');
      expect(text).toContain('/BaseFont /Helvetica');
      expect(text).toContain('/BaseFont /Helvetica-Bold');
      expect(text).toContain('RAISE RESEARCH INTELLIGENCE REPORT');
      expect(text).toContain('startxref');
      expect(text.trim().endsWith('%%EOF')).toBe(true);
    });

    it('handles long responses across multiple pages cleanly', async () => {
      const longAnswer = Array.from(
        { length: 40 },
        (_, i) => `Paragraph ${i + 1}: Detailed findings regarding institutional deployment, telemetry analytics, and verification against research papers.`
      ).join('\n\n');

      const blob = generatePdfBlob('Extensive Research Analysis', longAnswer, MOCK_RESPONSE);
      const text = await readBlob(blob);

      expect(text).toContain('/Count');
      expect(text.trim().endsWith('%%EOF')).toBe(true);
    });
  });

  describe('generateReportHtml', () => {
    it('produces formatted HTML with print styles, inquiry box, and citations', () => {
      const html = generateReportHtml(
        MOCK_RESPONSE.query!,
        MOCK_RESPONSE.grounded_answer!,
        MOCK_RESPONSE
      );

      expect(html).toContain('<!DOCTYPE html>');
      expect(html).toContain('@page');
      expect(html).toContain('@media print');
      expect(html).toContain('RAISE RESEARCH INTELLIGENCE REPORT');
      expect(html).toContain('What deep-tech startups originate from IIT Madras research?');
      expect(html).toContain('Quality Gate:');
      expect(html).toContain('Traceability Score:');
      expect(html).toContain('IITMRP Annual Report.pdf');
    });
  });

  describe('download functions trigger DOM anchor click', () => {
    let originalCreateObjectURL: typeof URL.createObjectURL;
    let originalRevokeObjectURL: typeof URL.revokeObjectURL;

    beforeEach(() => {
      originalCreateObjectURL = URL.createObjectURL;
      originalRevokeObjectURL = URL.revokeObjectURL;
      URL.createObjectURL = vi.fn().mockReturnValue('blob:http://localhost:3000/mock-uuid');
      URL.revokeObjectURL = vi.fn();
    });

    afterEach(() => {
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
    });

    it('exportAsMarkdown triggers file download with .md extension', () => {
      const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      exportAsMarkdown(MOCK_RESPONSE.query!, MOCK_RESPONSE.grounded_answer!, MOCK_RESPONSE);
      expect(clickSpy).toHaveBeenCalled();
      clickSpy.mockRestore();
    });

    it('exportAsJson triggers file download with .json extension', () => {
      const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      exportAsJson(MOCK_RESPONSE.query!, MOCK_RESPONSE.grounded_answer!, MOCK_RESPONSE);
      expect(clickSpy).toHaveBeenCalled();
      clickSpy.mockRestore();
    });

    it('exportAsPdf triggers file download with .pdf extension', () => {
      const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      exportAsPdf(MOCK_RESPONSE.query!, MOCK_RESPONSE.grounded_answer!, MOCK_RESPONSE);
      expect(clickSpy).toHaveBeenCalled();
      clickSpy.mockRestore();
    });
  });
});
