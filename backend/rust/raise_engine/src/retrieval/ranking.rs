//! High-Throughput Candidate Pre-Ranking & Top-K Selection.
//! Avoids inflating 100,000+ Python dict objects by filtering candidates in contiguous Rust memory.

use serde::{Deserialize, Serialize};

#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct CandidateScore {
    pub id: u32,
    pub score: f32,
}

/// Selects the top_k candidate scores in-place using O(N) QuickSelect.
/// Only the top_k elements are sorted descending; the remaining N - K items are left unallocated.
pub fn select_top_k(candidates: &mut [CandidateScore], top_k: usize) -> &[CandidateScore] {
    let n = candidates.len();
    if n <= top_k {
        candidates.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        return candidates;
    }

    // Partition so that top_k highest scores are in candidates[..top_k]
    candidates.select_nth_unstable_by(top_k, |a, b| {
        b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal)
    });

    let top_slice = &mut candidates[..top_k];
    top_slice.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
    top_slice
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_select_top_k_100k() {
        let mut candidates: Vec<CandidateScore> = (0..10_000)
            .map(|i| CandidateScore {
                id: i,
                score: (i as f32) * 0.01,
            })
            .collect();

        let top = select_top_k(&mut candidates, 5);
        assert_eq!(top.len(), 5);
        assert_eq!(top[0].id, 9999);
        assert_eq!(top[1].id, 9998);
    }
}
