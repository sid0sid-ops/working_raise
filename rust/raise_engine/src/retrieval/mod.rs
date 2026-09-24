pub mod bm25;
pub mod dedup;
pub mod ranking;
pub mod rrf;
pub mod similarity;

pub use bm25::{CompactInvertedIndex, Posting};
pub use dedup::deduplicate_candidate_ids;
pub use ranking::{select_top_k, CandidateScore};
pub use rrf::{reciprocal_rank_fusion, RrfResult};
pub use similarity::{cosine_similarity, dot_product};
