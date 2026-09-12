import { apiClient, ApiResponse } from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { SearchResponse, SearchResponseSchema } from '../types';

export class SearchService {
  /**
   * Dense semantic vector search across ChromaDB chunks
   */
  public async search(
    query: string,
    limit: number = 5,
    signal?: AbortSignal
  ): Promise<ApiResponse<SearchResponse>> {
    return apiClient.request<SearchResponse>(
      ENDPOINTS.SEARCH,
      SearchResponseSchema,
      {
        method: 'POST',
        body: JSON.stringify({ query, limit }),
        signal,
      }
    );
  }
}

export const searchService = new SearchService();
