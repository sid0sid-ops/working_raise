//! Retrieval candidate deduplication and neighborhood selection.

use std::collections::HashSet;

/// Deduplicates candidate IDs preserving their original ranking order.
pub fn deduplicate_candidate_ids(ids: &[String]) -> Vec<String> {
    let mut seen = HashSet::new();
    let mut deduped = Vec::new();

    for id in ids {
        if seen.insert(id.clone()) {
            deduped.push(id.clone());
        }
    }

    deduped
}
