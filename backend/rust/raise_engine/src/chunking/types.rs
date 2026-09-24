//! Data models and schemas for Graph-Guided Adaptive Hierarchical Chunking (GGAHC).

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum BoundaryDecision {
    Merge,
    Split,
    Preserve,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoundaryExplanation {
    pub decision: BoundaryDecision,
    pub boundary_score: f32,
    pub confidence: f32,
    pub reasons: Vec<String>,
    pub signals: HashMap<String, f32>,
}

/// Compact numeric representation of boundary features across the FFI boundary.
/// Eliminates string, dictionary, and JSON serialization overhead (Pattern 2).
#[repr(C)]
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct CompactBoundaryFeature {
    pub tokens_a: u32,
    pub tokens_b: u32,
    pub is_table_or_figure: bool,
    pub structural_strength: f32,
    pub semantic_discontinuity: f32,
    pub topic_transition: f32,
    pub entity_continuity: f32,
    pub relationship_continuity: f32,
    pub graph_connectivity: f32,
    pub community_continuity: f32,
    pub cross_section: f32,
}

/// Compact decision output (decision code: 0=MERGE, 1=SPLIT, 2=PRESERVE).
#[repr(C)]
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct CompactBoundaryResult {
    pub decision: u8,
    pub boundary_score: f32,
    pub confidence: f32,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntityRef {
    pub id: String,
    pub name: Option<String>,
    pub label: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RelationshipRef {
    pub source_id: String,
    pub target_id: String,
    pub relation_type: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CandidateUnit {
    pub candidate_id: String,
    pub document_id: String,
    pub section_id: String,
    pub heading: String,
    pub page_start: usize,
    pub page_end: usize,
    pub plain_text: String,
    #[serde(default)]
    pub structural_unit_ids: Vec<String>,
    #[serde(default)]
    pub entities: Vec<EntityRef>,
    #[serde(default)]
    pub relationships: Vec<RelationshipRef>,
    pub community_id: Option<String>,
    #[serde(default)]
    pub is_table: bool,
    #[serde(default)]
    pub is_figure: bool,
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl CandidateUnit {
    pub fn token_estimate(&self) -> usize {
        self.plain_text.split_whitespace().count().max(1)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChunkingConfig {
    #[serde(default = "default_strategy")]
    pub strategy: String,

    #[serde(default = "default_min_child_tokens")]
    pub min_child_tokens: usize,
    #[serde(default = "default_target_child_tokens")]
    pub target_child_tokens: usize,
    #[serde(default = "default_max_child_tokens")]
    pub max_child_tokens: usize,

    #[serde(default = "default_min_parent_tokens")]
    pub min_parent_tokens: usize,
    #[serde(default = "default_target_parent_tokens")]
    pub target_parent_tokens: usize,
    #[serde(default = "default_max_parent_tokens")]
    pub max_parent_tokens: usize,

    // Boundary Score Weights
    #[serde(default = "default_w_sem")]
    pub weight_semantic_discontinuity: f32,
    #[serde(default = "default_w_struct")]
    pub weight_structural_boundary: f32,
    #[serde(default = "default_w_topic")]
    pub weight_topic_transition: f32,
    #[serde(default = "default_w_ent")]
    pub weight_entity_continuity: f32,
    #[serde(default = "default_w_rel")]
    pub weight_relationship_continuity: f32,
    #[serde(default = "default_w_conn")]
    pub weight_graph_connectivity: f32,
    #[serde(default = "default_w_comm")]
    pub weight_community_continuity: f32,
    #[serde(default = "default_w_cross")]
    pub weight_cross_section: f32,

    #[serde(default = "default_split_threshold")]
    pub split_threshold: f32,
    #[serde(default = "default_merge_threshold")]
    pub merge_threshold: f32,

    // Ablation Flags
    #[serde(default)]
    pub ablation_disable_entity_continuity: bool,
    #[serde(default)]
    pub ablation_disable_relationship_continuity: bool,
    #[serde(default)]
    pub ablation_disable_community_continuity: bool,
}

fn default_strategy() -> String { "gga_hybrid".to_string() }
fn default_min_child_tokens() -> usize { 100 }
fn default_target_child_tokens() -> usize { 250 }
fn default_max_child_tokens() -> usize { 400 }
fn default_min_parent_tokens() -> usize { 450 }
fn default_target_parent_tokens() -> usize { 800 }
fn default_max_parent_tokens() -> usize { 1400 }

fn default_w_sem() -> f32 { 1.0 }
fn default_w_struct() -> f32 { 1.2 }
fn default_w_topic() -> f32 { 1.0 }
fn default_w_ent() -> f32 { 1.4 }
fn default_w_rel() -> f32 { 1.5 }
fn default_w_conn() -> f32 { 1.2 }
fn default_w_comm() -> f32 { 1.1 }
fn default_w_cross() -> f32 { 0.8 }

fn default_split_threshold() -> f32 { 0.60 }
fn default_merge_threshold() -> f32 { -0.20 }

impl Default for ChunkingConfig {
    fn default() -> Self {
        Self {
            strategy: default_strategy(),
            min_child_tokens: default_min_child_tokens(),
            target_child_tokens: default_target_child_tokens(),
            max_child_tokens: default_max_child_tokens(),
            min_parent_tokens: default_min_parent_tokens(),
            target_parent_tokens: default_target_parent_tokens(),
            max_parent_tokens: default_max_parent_tokens(),
            weight_semantic_discontinuity: default_w_sem(),
            weight_structural_boundary: default_w_struct(),
            weight_topic_transition: default_w_topic(),
            weight_entity_continuity: default_w_ent(),
            weight_relationship_continuity: default_w_rel(),
            weight_graph_connectivity: default_w_conn(),
            weight_community_continuity: default_w_comm(),
            weight_cross_section: default_w_cross(),
            split_threshold: default_split_threshold(),
            merge_threshold: default_merge_threshold(),
            ablation_disable_entity_continuity: false,
            ablation_disable_relationship_continuity: false,
            ablation_disable_community_continuity: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Proposition {
    pub proposition_id: String,
    pub text: String,
    pub parent_chunk_id: String,
    pub document_id: String,
    pub section_id: String,
    pub page_number: usize,
    #[serde(default)]
    pub entities: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdaptiveChunk {
    pub chunk_id: String,
    pub document_id: String,
    pub parent_chunk_id: Option<String>,
    pub section_id: String,
    pub chunk_level: String,
    pub plain_text: String,
    pub contextualized_content: String,
    pub summary: Option<String>,
    pub heading: String,
    pub heading_level: usize,
    pub primary_page: usize,
    pub printed_page: Option<String>,
    pub source_pages: Vec<usize>,
    pub propositions: Vec<Proposition>,
    pub entities: Vec<EntityRef>,
    pub relationships: Vec<RelationshipRef>,
    pub community_ids: Vec<String>,
    pub source_block_ids: Vec<String>,
    pub previous_chunk_id: Option<String>,
    pub next_chunk_id: Option<String>,
    pub token_estimate: usize,
    pub boundary_score_before: f32,
    pub boundary_score_after: f32,
    pub boundary_reasons: Vec<String>,
    pub chunking_strategy: String,
    pub is_table: bool,
    pub is_figure: bool,
    pub tables_count: usize,
    pub metadata: HashMap<String, serde_json::Value>,
}
