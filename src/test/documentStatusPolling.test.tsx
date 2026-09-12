import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DocumentStatusResponseSchema, DocumentIngestionPhase } from '../schemas/sources';
import { IngestionProgressRing } from '../components/sources/IngestionProgressRing';
import { sourceService } from '../services/SourceService';
import { mockAdapter } from '../mocks/mockAdapter';
import { setApiMode } from '../app/config';
import { ENDPOINTS } from '../api/endpoints';

describe('Document Ingestion Status & Progress Ring (Priority 1.1 Correctness)', () => {
  beforeEach(() => {
    mockAdapter.resetScenario();
    setApiMode('mock');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('DocumentStatusResponseSchema Contract Validation', () => {
    it('validates canonical backend payload: { phase: "chunking", percent: 62, status: "processing", detail: "..." }', () => {
      const payload = {
        phase: 'chunking',
        percent: 62,
        status: 'processing',
        detail: 'Extracting entity triples',
      };

      const parsed = DocumentStatusResponseSchema.safeParse(payload);
      expect(parsed.success).toBe(true);
      if (parsed.success) {
        expect(parsed.data.phase).toBe('chunking');
        expect(parsed.data.percent).toBe(62);
        expect(parsed.data.status).toBe('processing');
        expect(parsed.data.detail).toBe('Extracting entity triples');
      }
    });

    it('handles optional detail field and defaults percent to 0 if omitted', () => {
      const payload = {
        phase: 'uploading',
      };

      const parsed = DocumentStatusResponseSchema.safeParse(payload);
      expect(parsed.success).toBe(true);
      if (parsed.success) {
        expect(parsed.data.phase).toBe('uploading');
        expect(parsed.data.percent).toBe(0);
        expect(parsed.data.detail).toBeUndefined();
      }
    });

    it('supports PostgreSQL progress_percent column fallback when percent is not present', () => {
      const payload = {
        phase: 'parsing',
        progress_percent: 45,
        status: 'processing',
      };

      const parsed = DocumentStatusResponseSchema.safeParse(payload);
      expect(parsed.success).toBe(true);
      if (parsed.success) {
        expect(parsed.data.phase).toBe('parsing');
        expect(parsed.data.percent).toBe(45);
      }
    });

    it('normalizes uppercase phase from backend (e.g. READY or CHUNKING)', () => {
      const payload = {
        phase: 'READY',
        percent: 100,
        status: 'ready',
      };

      const parsed = DocumentStatusResponseSchema.safeParse(payload);
      expect(parsed.success).toBe(true);
      if (parsed.success) {
        expect(parsed.data.phase).toBe('ready');
      }
    });

    it('rejects invalid phase string', () => {
      const payload = {
        phase: 'invalid_phase_name',
        percent: 50,
      };

      const parsed = DocumentStatusResponseSchema.safeParse(payload);
      expect(parsed.success).toBe(false);
    });
  });

  describe('SourceService & Mock Polling', () => {
    it('verifies DOCUMENT_STATUS endpoint URL generation', () => {
      expect(ENDPOINTS.DOCUMENT_STATUS('doc-123')).toBe('/api/documents/doc-123/status');
      expect(ENDPOINTS.DOCUMENT_STATUS('doc with spaces.pdf')).toBe('/api/documents/doc%20with%20spaces.pdf/status');
    });

    it('fetches document status from sourceService.getDocumentStatus in mock mode', async () => {
      const res = await sourceService.getDocumentStatus('doc-test-1');
      expect(res.error).toBeNull();
      expect(res.status).toBe(200);
      expect(res.data).toBeDefined();
      expect(['uploading', 'parsing', 'chunking', 'embedding', 'ready']).toContain(res.data?.phase);
      expect(typeof res.data?.percent).toBe('number');
      expect(res.data?.percent).toBeGreaterThanOrEqual(0);
      expect(res.data?.percent).toBeLessThanOrEqual(100);
    });
  });

  describe('IngestionProgressRing Visual Behaviour', () => {
    const phases: DocumentIngestionPhase[] = [
      'uploading',
      'parsing',
      'chunking',
      'embedding',
      'ready',
      'error',
    ];

    it.each(phases)('renders ring with exact phase label for %s', (phase) => {
      render(<IngestionProgressRing phase={phase} percent={50} />);

      // Must show the actual phase label, never "Processing..."
      expect(screen.queryByText(/Processing\.\.\./i)).toBeNull();

      // Check for presence of capitalized label
      const expectedLabel = phase.charAt(0).toUpperCase() + phase.slice(1);
      expect(screen.getByText(expectedLabel)).toBeInTheDocument();
    });

    it('renders progressbar with proper ARIA attributes', () => {
      render(<IngestionProgressRing phase="chunking" percent={62} />);

      const progressbar = screen.getByRole('progressbar');
      expect(progressbar).toBeInTheDocument();
      expect(progressbar).toHaveAttribute('aria-valuenow', '62');
      expect(progressbar).toHaveAttribute('aria-valuemin', '0');
      expect(progressbar).toHaveAttribute('aria-valuemax', '100');
      expect(progressbar).toHaveAttribute('aria-label', 'Ingestion Chunking — 62%');
      expect(screen.getByText('62%')).toBeInTheDocument();
    });

    it('renders static checkmark without % in ready phase', () => {
      const { container } = render(<IngestionProgressRing phase="ready" percent={100} />);

      expect(screen.getByText('Ready')).toBeInTheDocument();
      expect(screen.queryByText('100%')).toBeNull();

      // Should render SVG checkmark path
      const checkPath = container.querySelector('path[d="M3 8l3.5 3.5L13 5"]');
      expect(checkPath).toBeInTheDocument();
    });

    it('renders static exclamation without % in error phase', () => {
      const { container } = render(<IngestionProgressRing phase="error" percent={0} />);

      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.queryByText('0%')).toBeNull();

      // Should render SVG exclamation path
      const errorPath = container.querySelector('path[d="M8 3.5v5M8 11.5v1"]');
      expect(errorPath).toBeInTheDocument();
    });
  });
});
