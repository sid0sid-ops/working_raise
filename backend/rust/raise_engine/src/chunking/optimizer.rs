//! Batch Boundary Optimizer (evaluating all adjacent pairs across candidates).

use super::scoring::evaluate_boundary;
use super::types::{BoundaryDecision, BoundaryExplanation, CandidateUnit, ChunkingConfig};
use crate::graph::builder::{AdjacencyGraph, NodeType};
use crate::graph::community::detect_communities;

/// Builds the temporary graph from candidates, entities, and relationships.
pub fn build_temporary_graph(candidates: &[CandidateUnit]) -> AdjacencyGraph {
    let mut g = AdjacencyGraph::new();

    for cand in candidates {
        let cid = &cand.candidate_id;
        let c_idx = g.add_or_get_node(cid, NodeType::Candidate, Some(cand.heading.clone()), cand.page_start);

        for ent in &cand.entities {
            let e_idx = g.add_or_get_node(&ent.id, NodeType::Entity, ent.name.clone(), cand.page_start);
            g.add_edge(c_idx, e_idx, "MENTIONS");
        }

        for rel in &cand.relationships {
            if rel.source_id != *cid && rel.target_id != *cid {
                let s_idx = g.add_or_get_node(&rel.source_id, NodeType::Entity, None, cand.page_start);
                let t_idx = g.add_or_get_node(&rel.target_id, NodeType::Entity, None, cand.page_start);
                let rtype = rel.relation_type.as_deref().unwrap_or("RELATED_TO");
                g.add_edge(s_idx, t_idx, rtype);
            }
        }
    }

    g
}

/// Evaluates boundaries across all adjacent candidate pairs.
pub fn evaluate_boundaries_batch(
    candidates: &[CandidateUnit],
    config: &ChunkingConfig,
) -> (Vec<BoundaryExplanation>, AdjacencyGraph, std::collections::HashMap<String, String>) {
    if candidates.len() <= 1 {
        return (Vec::new(), AdjacencyGraph::new(), std::collections::HashMap::new());
    }

    let graph = build_temporary_graph(candidates);
    let communities = if !config.ablation_disable_community_continuity {
        detect_communities(&graph, 15)
    } else {
        std::collections::HashMap::new()
    };

    let mut decisions = Vec::with_capacity(candidates.len() - 1);

    for i in 0..candidates.len() - 1 {
        let u_a = &candidates[i];
        let u_b = &candidates[i + 1];

        let explanation = match config.strategy.as_str() {
            "structure_aware" | "hierarchical" => {
                let is_diff_heading = u_a.heading != u_b.heading;
                let dec = if is_diff_heading { BoundaryDecision::Split } else { BoundaryDecision::Merge };
                let score = if is_diff_heading { 0.7 } else { -0.5 };
                BoundaryExplanation {
                    decision: dec,
                    boundary_score: score,
                    confidence: 0.85,
                    reasons: vec!["structure-only heuristic".to_string()],
                    signals: std::collections::HashMap::new(),
                }
            }
            "semantic" => {
                let words_a: std::collections::HashSet<&str> = u_a.plain_text.split_whitespace().collect();
                let words_b: std::collections::HashSet<&str> = u_b.plain_text.split_whitespace().collect();
                let inter = words_a.intersection(&words_b).count() as f32;
                let union = words_a.union(&words_b).count() as f32;
                let jacc = inter / union.max(1.0);
                let dec = if jacc > 0.25 { BoundaryDecision::Merge } else { BoundaryDecision::Split };
                let score = if jacc <= 0.25 { 0.7 } else { -0.5 };
                BoundaryExplanation {
                    decision: dec,
                    boundary_score: score,
                    confidence: 0.80,
                    reasons: vec!["semantic-similarity heuristic".to_string()],
                    signals: std::collections::HashMap::new(),
                }
            }
            _ => {
                // gga_hybrid
                evaluate_boundary(u_a, u_b, Some(&graph), Some(&communities), config)
            }
        };

        decisions.push(explanation);
    }

    (decisions, graph, communities)
}
