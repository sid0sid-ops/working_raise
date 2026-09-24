//! Multi-Signal Boundary Scoring Engine (GGAHC Stages 11, 12, 13).
//! Computes:
//!   BoundaryScore(A, B) =
//!       w_sem * SemanticDiscontinuity
//!     + w_struct * StructuralBoundaryStrength
//!     + w_topic * TopicTransition
//!     - w_ent * EntityContinuity
//!     - w_rel * RelationshipContinuity
//!     - w_conn * GraphConnectivity
//!     - w_comm * CommunityContinuity
//!     - w_cross * CrossSectionDependency

use super::types::{BoundaryDecision, BoundaryExplanation, CandidateUnit, ChunkingConfig};
use crate::graph::builder::AdjacencyGraph;
use crate::graph::traversal::shortest_path_length;
use regex::Regex;
use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;

static WORD_TOKEN_RE: OnceLock<Regex> = OnceLock::new();

fn get_word_token_re() -> &'static Regex {
    WORD_TOKEN_RE.get_or_init(|| Regex::new(r"\b[a-zA-Z]{3,}\b").unwrap())
}

fn extract_words(text: &str) -> HashSet<String> {
    let stop_words: HashSet<&'static str> = [
        "the", "and", "for", "with", "this", "that", "from", "are", "were", "been", "have", "has",
    ]
    .into_iter()
    .collect();

    let re = get_word_token_re();
    let mut words = HashSet::new();
    for mat in re.find_iter(text) {
        let w = mat.as_str().to_lowercase();
        if !stop_words.contains(w.as_str()) {
            words.insert(w);
        }
    }
    words
}

/// Evaluates a pair of adjacent candidate information units (A, B) using multi-signal graph analysis.
pub fn evaluate_boundary(
    unit_a: &CandidateUnit,
    unit_b: &CandidateUnit,
    graph: Option<&AdjacencyGraph>,
    node_to_community: Option<&HashMap<String, String>>,
    config: &ChunkingConfig,
) -> BoundaryExplanation {
    // Hard Rule 1: Tables and figures preserve their boundaries
    if unit_a.is_table || unit_b.is_table {
        let mut signals = HashMap::new();
        signals.insert("structural_boundary".to_string(), 1.0);
        return BoundaryExplanation {
            decision: BoundaryDecision::Preserve,
            boundary_score: 0.85,
            confidence: 1.0,
            reasons: vec!["+ preserved table structure as first-class information unit".to_string()],
            signals,
        };
    }

    if unit_a.is_figure || unit_b.is_figure {
        let mut signals = HashMap::new();
        signals.insert("structural_boundary".to_string(), 0.9);
        return BoundaryExplanation {
            decision: BoundaryDecision::Preserve,
            boundary_score: 0.80,
            confidence: 1.0,
            reasons: vec!["+ preserved figure unit with discrete visual/caption context".to_string()],
            signals,
        };
    }

    // Size guardrail: if merging exceeds max parent tokens, force split
    let combined_tokens = unit_a.token_estimate() + unit_b.token_estimate();
    if combined_tokens > config.max_parent_tokens {
        let mut signals = HashMap::new();
        signals.insert("structural_boundary".to_string(), 1.0);
        return BoundaryExplanation {
            decision: BoundaryDecision::Split,
            boundary_score: 1.0,
            confidence: 1.0,
            reasons: vec![format!(
                "+ target parent size exceeded ({} > {} tokens)",
                combined_tokens, config.max_parent_tokens
            )],
            signals,
        };
    }

    // 1. Structural Boundary Strength [0.0 to 1.0]
    let mut structural_strength: f32 = 0.0;
    if unit_a.heading != unit_b.heading {
        structural_strength = 0.85;
    } else if unit_a.page_end != unit_b.page_start {
        structural_strength = 0.35;
    }

    // 2. Semantic Discontinuity & Topic Transition [0.0 to 1.0]
    let words_a = extract_words(&unit_a.plain_text);
    let words_b = extract_words(&unit_b.plain_text);

    let (semantic_discontinuity, sem_avail) = if words_a.len() >= 3 && words_b.len() >= 3 {
        let intersection_len = words_a.intersection(&words_b).count() as f32;
        let union_len = words_a.union(&words_b).count() as f32;
        let jaccard = intersection_len / union_len.max(1.0);
        ((1.0 - (jaccard * 3.0)).max(0.0), true)
    } else {
        (0.0, false)
    };

    let (topic_transition, topic_avail) = if unit_a.heading != unit_b.heading {
        (0.70, true)
    } else if sem_avail && semantic_discontinuity > 0.75 {
        (0.60, true)
    } else if sem_avail {
        (0.0, true)
    } else {
        (0.0, false)
    };

    // 3. Entity Continuity [0.0 to 1.0]
    let ent_ids_a: HashSet<&str> = unit_a.entities.iter().map(|e| e.id.as_str()).collect();
    let ent_ids_b: HashSet<&str> = unit_b.entities.iter().map(|e| e.id.as_str()).collect();
    let shared_ents: HashSet<&str> = ent_ids_a.intersection(&ent_ids_b).copied().collect();
    let all_ents: HashSet<&str> = ent_ids_a.union(&ent_ids_b).copied().collect();

    let names_a: HashSet<String> = unit_a
        .entities
        .iter()
        .filter_map(|e| e.name.as_ref())
        .filter(|n| n.len() > 3)
        .map(|n| n.to_lowercase())
        .collect();
    let names_b: HashSet<String> = unit_b
        .entities
        .iter()
        .filter_map(|e| e.name.as_ref())
        .filter(|n| n.len() > 3)
        .map(|n| n.to_lowercase())
        .collect();

    let (entity_continuity, ent_avail) = if config.ablation_disable_entity_continuity {
        (0.0, false)
    } else if all_ents.is_empty() && names_a.is_empty() && names_b.is_empty() {
        (0.0, false)
    } else {
        let mut ec = if !all_ents.is_empty() {
            (shared_ents.len() as f32) / (all_ents.len() as f32)
        } else {
            0.0
        };
        if !names_a.is_empty() && !names_b.is_empty() && names_a.intersection(&names_b).next().is_some() {
            ec = ec.max(0.75);
        }
        (ec, true)
    };

    // 4. Relationship Continuity [0.0 to 1.0]
    let rel_targets_a: HashSet<&str> = unit_a.relationships.iter().map(|r| r.target_id.as_str()).collect();
    let rel_targets_b: HashSet<&str> = unit_b.relationships.iter().map(|r| r.target_id.as_str()).collect();
    let shared_rel_targets = rel_targets_a.intersection(&rel_targets_b).next().is_some();
    let cross_rel = ent_ids_a.intersection(&rel_targets_b).next().is_some()
        || ent_ids_b.intersection(&rel_targets_a).next().is_some();

    let (relationship_continuity, rel_avail) = if config.ablation_disable_relationship_continuity {
        (0.0, false)
    } else if shared_rel_targets || cross_rel {
        (0.85, true)
    } else if !shared_ents.is_empty() {
        (0.50, true)
    } else if !rel_targets_a.is_empty() || !rel_targets_b.is_empty() {
        (0.0, true)
    } else {
        (0.0, false)
    };

    // 5. Graph Connectivity & Shortest Path in Temporary Graph
    let (graph_connectivity, conn_avail) = if let Some(g) = graph {
        if g.has_node(&unit_a.candidate_id) && g.has_node(&unit_b.candidate_id) {
            if let Some(dist) = shortest_path_length(g, &unit_a.candidate_id, &unit_b.candidate_id) {
                let val = if dist == 2 {
                    1.0
                } else if dist <= 4 {
                    0.6
                } else {
                    0.2
                };
                (val, true)
            } else {
                (0.0, true)
            }
        } else if !shared_ents.is_empty() {
            (0.75, true)
        } else {
            (0.0, false)
        }
    } else if !shared_ents.is_empty() {
        (0.75, true)
    } else {
        (0.0, false)
    };

    // 6. Community Continuity [0.0 to 1.0]
    let (community_continuity, comm_avail) = if config.ablation_disable_community_continuity {
        (0.0, false)
    } else if let Some(node_map) = node_to_community {
        let comm_a = node_map.get(&unit_a.candidate_id);
        let comm_b = node_map.get(&unit_b.candidate_id);
        if let (Some(ca), Some(cb)) = (comm_a, comm_b) {
            ((if ca == cb { 1.0 } else { 0.0 }), true)
        } else {
            (0.0, false)
        }
    } else {
        (0.0, false)
    };

    // 7. Cross-Section Dependencies
    let (cross_section, cross_avail) = if unit_a.section_id != unit_b.section_id {
        if !shared_ents.is_empty() || cross_rel {
            (0.9, true)
        } else {
            (0.0, true)
        }
    } else {
        (0.0, true)
    };

    // Weight Renormalization
    let signals_weights = [
        (config.weight_semantic_discontinuity, semantic_discontinuity, sem_avail, 1.0f32),
        (config.weight_structural_boundary, structural_strength, true, 1.0f32),
        (config.weight_topic_transition, topic_transition, topic_avail, 1.0f32),
        (config.weight_entity_continuity, entity_continuity, ent_avail, -1.0f32),
        (config.weight_relationship_continuity, relationship_continuity, rel_avail, -1.0f32),
        (config.weight_graph_connectivity, graph_connectivity, conn_avail, -1.0f32),
        (config.weight_community_continuity, community_continuity, comm_avail, -1.0f32),
        (config.weight_cross_section, cross_section, cross_avail, -1.0f32),
    ];

    let total_configured_weight: f32 = signals_weights.iter().map(|(w, _, _, _)| *w).sum();
    let active_configured_weight: f32 = signals_weights
        .iter()
        .filter(|(_, _, avail, _)| *avail)
        .map(|(w, _, _, _)| *w)
        .sum();

    let score = if active_configured_weight > 0.0 {
        let scale_factor = total_configured_weight / active_configured_weight;
        signals_weights
            .iter()
            .filter(|(_, _, avail, _)| *avail)
            .map(|(w, val, _, sign)| *w * scale_factor * *sign * *val)
            .sum()
    } else {
        0.0
    };

    let available_weight_ratio = if total_configured_weight > 0.0 {
        active_configured_weight / total_configured_weight
    } else {
        1.0
    };

    let mut signals = HashMap::new();
    signals.insert("semantic_discontinuity".to_string(), semantic_discontinuity);
    signals.insert("structural_strength".to_string(), structural_strength);
    signals.insert("structural_boundary".to_string(), structural_strength);
    signals.insert("topic_transition".to_string(), topic_transition);
    signals.insert("entity_continuity".to_string(), entity_continuity);
    signals.insert("relationship_continuity".to_string(), relationship_continuity);
    signals.insert("graph_connectivity".to_string(), graph_connectivity);
    signals.insert("community_continuity".to_string(), community_continuity);
    signals.insert("cross_section".to_string(), cross_section);

    let mut reasons = Vec::new();
    let (decision, margin) = if score >= config.split_threshold {
        let m = score - config.split_threshold;
        if structural_strength > 0.5 {
            reasons.push("+ strong structural boundary".to_string());
        }
        if topic_transition > 0.5 {
            reasons.push("+ strong topic transition".to_string());
        }
        if ent_avail && entity_continuity < 0.2 {
            reasons.push("+ low entity overlap".to_string());
        }
        if rel_avail && relationship_continuity < 0.2 {
            reasons.push("+ low relationship continuity".to_string());
        }
        if comm_avail && community_continuity == 0.0 {
            reasons.push("+ different graph communities".to_string());
        }
        (BoundaryDecision::Split, m)
    } else if score <= config.merge_threshold {
        let m = config.merge_threshold - score;
        if entity_continuity > 0.4 {
            reasons.push("- high entity continuity".to_string());
        }
        if relationship_continuity > 0.4 {
            reasons.push("- shared relationship / event".to_string());
        }
        if graph_connectivity > 0.5 {
            reasons.push("- strong graph connectivity".to_string());
        }
        if community_continuity > 0.5 {
            reasons.push("- same graph community".to_string());
        }
        if sem_avail && semantic_discontinuity < 0.35 {
            reasons.push("- strong semantic similarity".to_string());
        }
        (BoundaryDecision::Merge, m)
    } else {
        reasons.push("= balanced signals; preserve candidate unit boundary".to_string());
        (BoundaryDecision::Preserve, 0.0)
    };

    let agreement = (0.50 + 0.50 * margin).min(1.0);
    let confidence = (available_weight_ratio * agreement).clamp(0.20, 0.99);

    BoundaryExplanation {
        decision,
        boundary_score: score,
        confidence,
        reasons,
        signals,
    }
}

/// Evaluates an array of compact boundary features with zero string or JSON allocations (Pattern 2).
pub fn evaluate_compact_features(
    features: &[super::types::CompactBoundaryFeature],
    config: &ChunkingConfig,
) -> Vec<super::types::CompactBoundaryResult> {
    let mut results = Vec::with_capacity(features.len());
    for f in features {
        if f.is_table_or_figure {
            results.push(super::types::CompactBoundaryResult {
                decision: 2, // Preserve
                boundary_score: 0.85,
                confidence: 0.95,
            });
            continue;
        }

        let combined_tokens = f.tokens_a + f.tokens_b;
        if combined_tokens as usize > config.max_parent_tokens {
            results.push(super::types::CompactBoundaryResult {

                decision: 1, // Split
                boundary_score: 1.0,
                confidence: 0.92,
            });
            continue;
        }

        let score = config.weight_semantic_discontinuity * f.semantic_discontinuity
            + config.weight_structural_boundary * f.structural_strength
            + config.weight_topic_transition * f.topic_transition
            - config.weight_entity_continuity * f.entity_continuity
            - config.weight_relationship_continuity * f.relationship_continuity
            - config.weight_graph_connectivity * f.graph_connectivity
            - config.weight_community_continuity * f.community_continuity
            - config.weight_cross_section * f.cross_section;

        let (decision, confidence) = if score >= config.split_threshold {
            (1, (0.60 + (score - config.split_threshold).abs() * 0.4).min(0.98))
        } else if score <= config.merge_threshold {
            (0, (0.60 + (config.merge_threshold - score).abs() * 0.4).min(0.98))
        } else {
            (2, 0.75)
        };

        results.push(super::types::CompactBoundaryResult {
            decision,
            boundary_score: score,
            confidence,
        });
    }
    results
}

