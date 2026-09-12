import { describe, it, expect } from 'vitest';
import { SubgraphQueryResponseSchema } from '../schemas/chat';
import { DocumentListResponseSchema, UploadResponseSchema, DeleteDocumentResponseSchema } from '../schemas/sources';
import { FullGraphResponseSchema } from '../schemas/graph';
import { HardwareTelemetrySchema, Neo4jStatusSchema } from '../schemas/system';
import { mockAdapter } from '../mocks/mockAdapter';

describe('Zod Schema Verification against Production Fixtures', () => {
  const fixtures = mockAdapter.getFixtures();

  it('validates Fixture 1: graphrag_success_xyma', () => {
    const parsed = SubgraphQueryResponseSchema.safeParse(fixtures.graphragSuccess);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.grounded_answer).toContain('XYMA Analytics');
      expect(parsed.data.citations.length).toBe(3);
      expect(parsed.data.verified_claims.length).toBe(2);
      expect(parsed.data.quality_gate_decision).toBe('accept');
    }
  });

  it('validates Fixture 2: empty_workspace response', () => {
    const parsed = SubgraphQueryResponseSchema.safeParse(fixtures.emptyWorkspace);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.quality_gate_decision).toBe('empty_workspace');
      expect(parsed.data.grounded_answer).toContain('Please upload an academic PDF');
    }
  });

  it('validates Fixture 3: unable_to_verify refusal response', () => {
    const parsed = SubgraphQueryResponseSchema.safeParse(fixtures.unableToVerify);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.quality_gate_decision).toBe('unable_to_verify');
      expect(parsed.data.quality_gate_report?.faithfulness).toBe(0.45);
      expect(parsed.data.quality_gate_report?.is_acceptable).toBe(false);
    }
  });

  it('validates Fixture 4: documents_list payload', () => {
    const parsed = DocumentListResponseSchema.safeParse(fixtures.documentsList);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.total_count).toBe(4);
      expect(parsed.data.documents[0].filename).toBe('IITMRP Annual Report.pdf');
    }
  });

  it('validates Fixture 5: upload_success payload', () => {
    const parsed = UploadResponseSchema.safeParse(fixtures.uploadSuccess);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.uploaded_count).toBe(1);
      expect(parsed.data.total_nodes).toBe(45);
    }
  });

  it('validates Fixture 6: delete_success payload', () => {
    const parsed = DeleteDocumentResponseSchema.safeParse(fixtures.deleteSuccess);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.status).toBe('success');
      expect(parsed.data.total_count).toBe(1);
    }
  });

  it('validates Fixture 7: system_telemetry and neo4j status', () => {
    const telemParsed = HardwareTelemetrySchema.safeParse(fixtures.systemTelemetry.telemetry);
    expect(telemParsed.success).toBe(true);
    if (telemParsed.success) {
      expect(telemParsed.data.gpu_model).toContain('RTX 3090');
    }

    const neo4jParsed = Neo4jStatusSchema.safeParse(fixtures.systemTelemetry.neo4j);
    expect(neo4jParsed.success).toBe(true);
    if (neo4jParsed.success) {
      expect(neo4jParsed.data.connected).toBe(true);
      expect(neo4jParsed.data.total_nodes).toBe(16);
    }
  });

  it('validates Fixture 15: full knowledge graph payload', () => {
    const parsed = FullGraphResponseSchema.safeParse(fixtures.knowledgeGraphFull);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.nodes.length).toBe(6);
      expect(parsed.data.edges.length).toBe(2);
    }
  });
});
