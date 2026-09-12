import { describe, it, expect } from 'vitest';
import { QualityGateDecisionSchema, QualityGateReportSchema } from '../schemas/chat';

describe('Quality Gate State Governance', () => {
  it('validates accepted quality gate state', () => {
    const report = {
      evaluator_type: 'RuntimeFaithfulnessQualityGate',
      faithfulness: 0.95,
      answer_relevance: 0.92,
      context_precision: 0.94,
      context_recall: 0.89,
      overall_score: 0.93,
      supported_claims_count: 2,
      total_claims_count: 2,
      numerical_mismatches: 0,
      citation_errors: 0,
      is_acceptable: true,
      rejection_reason: null,
    };

    const parsed = QualityGateReportSchema.safeParse(report);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.faithfulness).toBeGreaterThanOrEqual(0.80);
      expect(parsed.data.numerical_mismatches).toBe(0);
      expect(parsed.data.is_acceptable).toBe(true);
    }
  });

  it('validates unverified / refusal quality gate state', () => {
    const report = {
      evaluator_type: 'LocalHeuristicEvaluator',
      faithfulness: 0.45,
      answer_relevance: 0.40,
      supported_claims_count: 1,
      total_claims_count: 4,
      numerical_mismatches: 2,
      citation_errors: 1,
      is_acceptable: false,
      rejection_reason: 'Faithfulness score 0.45 below threshold 0.80; 2 numerical mismatch(es)',
    };

    const parsed = QualityGateReportSchema.safeParse(report);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.is_acceptable).toBe(false);
      expect(parsed.data.numerical_mismatches).toBe(2);
      expect(parsed.data.rejection_reason).toContain('below threshold');
    }
  });

  it('verifies all 4 distinct quality gate decisions', () => {
    const decisions = ['accept', 'retry', 'unable_to_verify', 'empty_workspace'];
    for (const d of decisions) {
      const parsed = QualityGateDecisionSchema.safeParse(d);
      expect(parsed.success).toBe(true);
    }
  });
});
