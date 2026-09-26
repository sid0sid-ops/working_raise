import { type ApiResponse, apiClient } from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import {
  type FullGraphResponse,
  FullGraphResponseSchema,
  type SubgraphData,
  SubgraphDataSchema,
} from '../types';

export class GraphService {
  /**
   * Retrieves the full knowledge graph
   */
  public async getFullGraph(signal?: AbortSignal): Promise<ApiResponse<FullGraphResponse>> {
    return apiClient.request<FullGraphResponse>(ENDPOINTS.GRAPH, FullGraphResponseSchema, {
      method: 'GET',
      signal,
    });
  }

  /**
   * Retrieves k-hop subgraph around a designated node ID
   */
  public async getSubgraph(
    nodeId: string,
    signal?: AbortSignal
  ): Promise<ApiResponse<SubgraphData>> {
    return apiClient.request<SubgraphData>(ENDPOINTS.SUBGRAPH(nodeId), SubgraphDataSchema, {
      method: 'GET',
      signal,
    });
  }
}

export const graphService = new GraphService();
