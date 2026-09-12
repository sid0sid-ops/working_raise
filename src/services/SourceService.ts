import { apiClient, ApiResponse } from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { getApiBaseUrl } from '../app/config';
import {
  DocumentListResponse,
  DocumentListResponseSchema,
  UploadResponse,
  UploadResponseSchema,
  DeleteDocumentResponse,
  DeleteDocumentResponseSchema,
  DocumentStatusResponse,
  DocumentStatusResponseSchema,
} from '../types';

export class SourceService {
  /**
   * Authoritative list of active confirmed ready documents
   */
  public async getDocuments(signal?: AbortSignal): Promise<ApiResponse<DocumentListResponse>> {
    return apiClient.request<DocumentListResponse>(
      ENDPOINTS.DOCUMENTS,
      DocumentListResponseSchema,
      {
        method: 'GET',
        signal,
      }
    );
  }

  /**
   * Synchronous Document upload (PDF, TXT, DOCX, MD, CSV)
   * Enforces IBM Docling parser at 100% potential for layout & table fidelity
   * Tries POST /api/upload first; falls back to /api/upload-academic-pdfs
   * 120s timeout configured for large files
   */
  public async uploadPdfs(
    files: File[],
    signal?: AbortSignal,
    options?: { parseMode?: 'fast' | 'expert'; parser?: string; sessionId?: string }
  ): Promise<ApiResponse<UploadResponse>> {
    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file);
    }
    if (files.length > 0) {
      formData.append('file', files[0]);
    }
    if (options?.sessionId) {
      formData.append('session_id', options.sessionId);
    }

    // Pass parser and mode parameters based on selected mode
    const mode = options?.parseMode || 'expert';
    const isExpert = mode === 'expert' || options?.parser === 'docling';
    const parser = options?.parser || (isExpert ? 'docling' : 'fast');
    formData.append('parser', parser);
    formData.append('engine', parser);
    formData.append('parse_mode', mode);
    formData.append('mode', mode);
    if (isExpert) {
      formData.append('extract_tables', 'true');
      formData.append('full_potential', 'true');
    }

    // 1. Try standard POST /api/upload with query parameters
    const uploadUrl = isExpert
      ? `${ENDPOINTS.UPLOAD}?parser=docling&mode=expert`
      : ENDPOINTS.UPLOAD;

    const uploadRes = await apiClient.request<any>(
      uploadUrl,
      undefined,
      {
        method: 'POST',
        body: formData,
        signal,
        timeoutMs: 120000,
      }
    );

    if (uploadRes.status === 200 && uploadRes.data) {
      const data = uploadRes.data;
      const parsed: UploadResponse = {
        status: data.status || 'success',
        uploaded_count: data.uploaded_count ?? files.length,
        reports: Array.isArray(data.reports)
          ? data.reports
          : files.map((f) => ({
              filename: f.name,
              pages_processed: 1,
              chunks_extracted: data.total_chunks ?? 1,
              facts_extracted: data.total_entities ?? 0,
              triples_extracted: 0,
            })),
        total_nodes: data.total_nodes ?? data.total_entities ?? 0,
        total_edges: data.total_edges ?? 0,
      };
      return {
        data: parsed,
        error: null,
        isMock: uploadRes.isMock,
        status: 200,
      };
    }

    // 2. Fallback to /api/upload-academic-pdfs with Docling query parameters
    const fallbackUrl = isExpert
      ? `${ENDPOINTS.UPLOAD_ACADEMIC_PDFS}?parser=docling&mode=expert`
      : ENDPOINTS.UPLOAD_ACADEMIC_PDFS;

    return apiClient.request<UploadResponse>(
      fallbackUrl,
      UploadResponseSchema,
      {
        method: 'POST',
        body: formData,
        signal,
        timeoutMs: 120000,
      }
    );
  }

  /**
   * Prunes document from knowledge vault
   * Tries DELETE /api/documents/{id} first; falls back to POST /api/documents/delete
   */
  public async deleteDocument(
    filenameOrId: string,
    signal?: AbortSignal
  ): Promise<ApiResponse<DeleteDocumentResponse>> {
    const cleanId = filenameOrId.trim();

    // 1. Try DELETE /api/documents/{id}
    const deleteRes = await apiClient.request<any>(
      ENDPOINTS.DELETE_DOCUMENT_BY_ID(cleanId),
      undefined,
      {
        method: 'DELETE',
        signal,
      }
    );

    if (deleteRes.status >= 200 && deleteRes.status < 300) {
      return {
        data: {
          status: 'success',
          filename: cleanId,
          documents: [],
          total_count: 0,
        },
        error: null,
        isMock: deleteRes.isMock,
        status: deleteRes.status,
      };
    }

    // If backend explicitly forbade deletion (e.g. 403 Forbidden for protected document), do NOT fall back
    if (deleteRes.status === 403) {
      return deleteRes;
    }

    // 2. Fallback to POST /api/documents/delete
    return apiClient.request<DeleteDocumentResponse>(
      ENDPOINTS.DELETE_DOCUMENT,
      DeleteDocumentResponseSchema,
      {
        method: 'POST',
        body: JSON.stringify({ filename: cleanId, id: cleanId }),
        signal,
      }
    );
  }

  /**
   * Deep-linked PDF URL with page fragment anchor
   */
  public getPdfUrl(filename: string, pageNumber?: number): string {
    const base = getApiBaseUrl();
    const cleanFilename = encodeURIComponent(filename);
    const pageFragment = pageNumber && pageNumber > 0 ? `#page=${pageNumber}` : '';
    return `${base}/api/pdf/${cleanFilename}${pageFragment}`;
  }

  /**
   * Loads default research vault documents
   */
  public async loadVaultDefaults(signal?: AbortSignal): Promise<ApiResponse<any>> {
    return apiClient.request(
      ENDPOINTS.LOAD_VAULT_DEFAULTS,
      undefined,
      {
        method: 'POST',
        signal,
      }
    );
  }

  /**
   * Polls real-time ingestion progress for a document.
   * Backend: GET /api/documents/{id}/status
   * Returns phase, percent, and optional detail string.
   */
  public async getDocumentStatus(
    docId: string,
    signal?: AbortSignal
  ): Promise<ApiResponse<DocumentStatusResponse>> {
    return apiClient.request<DocumentStatusResponse>(
      ENDPOINTS.DOCUMENT_STATUS(docId),
      DocumentStatusResponseSchema,
      {
        method: 'GET',
        signal,
      }
    );
  }

  /**
   * Real-time Document Ingestion Stream: GET /api/documents/{doc_id}/events
   * Emits milestone progress (uploading -> parsing -> chunking -> embedding -> ready)
   * Automatically closes on [DONE] or terminal status.
   */
  public watchDocumentIngestionEvents(
    docId: string,
    onProgress: (status: DocumentStatusResponse) => void,
    onComplete?: () => void,
    onError?: (err: any) => void
  ): () => void {
    const base = getApiBaseUrl();
    const sseUrl = `${base}${ENDPOINTS.DOCUMENT_EVENTS(docId)}`;
    let closed = false;

    if (typeof window !== 'undefined' && 'EventSource' in window) {
      try {
        const es = new EventSource(sseUrl);

        es.onmessage = (event) => {
          if (closed) return;
          if (event.data === '[DONE]') {
            es.close();
            closed = true;
            onProgress({
              phase: 'ready',
              percent: 100,
              status: 'ready',
              detail: 'Document ingestion complete and graph synchronized',
            });
            onComplete?.();
            return;
          }

          try {
            const data = JSON.parse(event.data);
            onProgress({
              phase: data.phase || 'processing',
              percent: typeof data.percent === 'number' ? data.percent : 50,
              status: data.status || (data.percent >= 100 ? 'ready' : 'processing'),
              detail: data.detail || '',
            });
            if (data.status === 'ready' || data.percent >= 100) {
              es.close();
              closed = true;
              onComplete?.();
            }
          } catch {}
        };

        es.onerror = (err) => {
          es.close();
          if (!closed) {
            onError?.(err);
          }
        };

        return () => {
          closed = true;
          es.close();
        };
      } catch (err) {
        onError?.(err);
      }
    }

    return () => {
      closed = true;
    };
  }
}

export const sourceService = new SourceService();
