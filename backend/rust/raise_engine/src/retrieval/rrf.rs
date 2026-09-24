//! Reciprocal Rank Fusion (RRF) over multiple ranked channel results.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RrfResult {
    pub id: String,
    pub rrf_score: f32,
    pub rrf_rank: usize,
}

/// Computes Reciprocal Rank Fusion across multiple ranked candidate lists.
/// Formula: RRF(d) = sum(1.0 / (k + rank))
pub fn reciprocal_rank_fusion(ranked_channels: &[Vec<String>], k: usize) -> Vec<RrfResult> {
    let mut scores: HashMap<String, f32> = HashMap::new();

    for channel in ranked_channels {
        for (rank_0, doc_id) in channel.iter().enumerate() {
            let rank = (rank_0 + 1) as f32;
            let weight = 1.0 / ((k as f32) + rank);
            *scores.entry(doc_id.clone()).or_insert(0.0) += weight;
        }
    }

    let mut entries: Vec<(String, f32)> = scores.into_iter().collect();
    entries.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

    entries
        .into_iter()
        .enumerate()
        .map(|(i, (id, score))| RrfResult {
            id,
            rrf_score: (score * 1_000_000.0).round() / 1_000_000.0,
            rrf_rank: i + 1,
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rrf_multi_channel() {
        let dense = vec!["doc_a".to_string(), "doc_b".to_string(), "doc_c".to_string()];
        let sparse = vec!["doc_b".to_string(), "doc_a".to_string(), "doc_d".to_string()];

        let fused = reciprocal_rank_fusion(&[dense, sparse], 60);
        assert_eq!(fused.len(), 4);
        // doc_a and doc_b have equal aggregate score: 1/61 + 1/62
        assert!(fused[0].id == "doc_a" || fused[0].id == "doc_b");
        assert!(fused[1].id == "doc_a" || fused[1].id == "doc_b");
        assert_eq!(fused[0].rrf_rank, 1);
        assert_eq!(fused[1].rrf_rank, 2);
    }
}
