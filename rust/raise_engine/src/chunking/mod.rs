pub mod assembler;
pub mod optimizer;
pub mod proposition;
pub mod scoring;
pub mod types;

pub use assembler::assemble_hierarchy;
pub use optimizer::{build_temporary_graph, evaluate_boundaries_batch};
pub use proposition::extract_propositions;
pub use scoring::evaluate_boundary;
pub use types::{
    AdaptiveChunk, BoundaryDecision, BoundaryExplanation, CandidateUnit, ChunkingConfig, EntityRef,
    Proposition, RelationshipRef,
};
