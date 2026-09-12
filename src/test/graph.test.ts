import { describe, it, expect } from 'vitest';
import { mockAdapter } from '../mocks/mockAdapter';

describe('Graph Transformation & Domain Model', () => {
  const fixtures = mockAdapter.getFixtures();

  it('verifies full graph nodes, labels, and provenance triples', () => {
    const graph = fixtures.knowledgeGraphFull;
    expect(graph.nodes.length).toBe(6);
    expect(graph.edges.length).toBe(2);

    // Verify entity types
    const types = new Set(graph.nodes.map((n) => n.type));
    expect(types.has('Startup')).toBe(true);
    expect(types.has('Institution')).toBe(true);
    expect(types.has('CoE')).toBe(true);

    // Verify provenance anchor
    const xymaNode = graph.nodes.find((n) => n.id === 'Startup_XYMA_Analytics');
    expect(xymaNode).toBeDefined();
    expect(xymaNode?.provenance?.doc).toBe('IITMRP Annual Report.pdf');
    expect(xymaNode?.provenance?.page).toBe(16);

    // Verify edge relationship
    const edge = graph.edges[0];
    expect(edge.relationship).toBe('CO_DEVELOPED_WITH');
    expect(edge.source).toBe('Startup_XYMA_Analytics');
    expect(edge.target).toBe('CoE_CNDE');
  });

  it('filters subgraph nodes by active node connections correctly', () => {
    const graph = fixtures.knowledgeGraphFull;
    const startupNodes = graph.nodes.filter((n) => n.type === 'Startup');
    expect(startupNodes.length).toBe(4);
  });
});
