//! Compact Inverted Index and Okapi BM25 Lexical Retrieval Engine.
//! Replaces fragmented Python dict-of-dicts with cache-friendly contiguous arrays.

use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Posting {
    pub doc_id: u32,
    pub term_freq: u16,
}

#[derive(Debug, Clone)]
struct HeapEntry {
    doc_id: u32,
    score: f32,
}

impl PartialEq for HeapEntry {
    fn eq(&self, other: &Self) -> bool {
        self.score == other.score
    }
}

impl Eq for HeapEntry {}

impl PartialOrd for HeapEntry {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        // Min-heap: reverse order
        other.score.partial_cmp(&self.score)
    }
}

impl Ord for HeapEntry {
    fn cmp(&self, other: &Self) -> Ordering {
        self.partial_cmp(other).unwrap_or(Ordering::Equal)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompactInvertedIndex {
    pub vocab: HashMap<String, Vec<Posting>>,
    pub doc_keys: Vec<String>,
    pub doc_lengths: Vec<u32>,
    pub avg_dl: f32,
    pub total_docs: usize,
    pub k1: f32,
    pub b: f32,
}

impl CompactInvertedIndex {
    pub fn new(k1: f32, b: f32) -> Self {
        Self {
            vocab: HashMap::new(),
            doc_keys: Vec::new(),
            doc_lengths: Vec::new(),
            avg_dl: 0.0,
            total_docs: 0,
            k1,
            b,
        }
    }

    /// Ingests a collection of documents (chunk_id, plain_text) into the compact inverted index.
    pub fn build(docs: &[(String, String)], k1: f32, b: f32) -> Self {
        let mut index = Self::new(k1, b);
        index.total_docs = docs.len();
        if index.total_docs == 0 {
            return index;
        }

        index.doc_keys.reserve(docs.len());
        index.doc_lengths.reserve(docs.len());

        let mut total_tokens = 0u64;

        for (u32_id, (doc_id, text)) in docs.iter().enumerate() {
            index.doc_keys.push(doc_id.clone());

            // Tokenize and count term frequencies
            let mut tf_map: HashMap<String, u16> = HashMap::new();
            let mut len = 0u32;

            for token in text.split(|c: char| !c.is_alphanumeric()) {
                let token_clean = token.to_lowercase();
                if token_clean.len() >= 2 {
                    len += 1;
                    let count = tf_map.entry(token_clean).or_insert(0);
                    *count = count.saturating_add(1);
                }
            }

            index.doc_lengths.push(len);
            total_tokens += len as u64;

            for (term, tf) in tf_map {
                index.vocab.entry(term).or_default().push(Posting {
                    doc_id: u32_id as u32,
                    term_freq: tf,
                });
            }
        }

        index.avg_dl = (total_tokens as f32) / (index.total_docs as f32);
        index
    }

    /// Performs Okapi BM25 search using a bounded min-heap, returning top_k results.
    pub fn search(&self, query: &str, top_k: usize) -> Vec<(String, f32)> {
        if self.total_docs == 0 || top_k == 0 {
            return Vec::new();
        }

        // Tokenize query
        let mut query_terms: Vec<String> = Vec::new();
        for token in query.split(|c: char| !c.is_alphanumeric()) {
            let t = token.to_lowercase();
            if t.len() >= 2 && self.vocab.contains_key(&t) {
                query_terms.push(t);
            }
        }

        if query_terms.is_empty() {
            return Vec::new();
        }

        // Accumulate BM25 scores
        let mut doc_scores: HashMap<u32, f32> = HashMap::new();
        let num_docs = self.total_docs as f32;

        for term in &query_terms {
            if let Some(postings) = self.vocab.get(term) {
                let doc_freq = postings.len() as f32;
                // Robertson-Spärck Jones IDF
                let idf = ((num_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0).ln();

                for p in postings {
                    let dl = self.doc_lengths[p.doc_id as usize] as f32;
                    let tf = p.term_freq as f32;

                    let denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / self.avg_dl));
                    let term_score = idf * (tf * (self.k1 + 1.0)) / denom;

                    *doc_scores.entry(p.doc_id).or_insert(0.0) += term_score;
                }
            }
        }

        // Bounded Min-Heap for Top-K extraction (O(N log K))
        let mut heap: BinaryHeap<HeapEntry> = BinaryHeap::with_capacity(top_k + 1);

        for (doc_id, score) in doc_scores {
            if heap.len() < top_k {
                heap.push(HeapEntry { doc_id, score });
            } else if let Some(min_entry) = heap.peek() {
                if score > min_entry.score {
                    heap.pop();
                    heap.push(HeapEntry { doc_id, score });
                }
            }
        }

        // Extract and sort descending
        let mut results = Vec::with_capacity(heap.len());
        while let Some(entry) = heap.pop() {
            let doc_key = self.doc_keys[entry.doc_id as usize].clone();
            results.push((doc_key, entry.score));
        }
        results.reverse();

        results
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bm25_search_scoring() {
        let docs = vec![
            ("doc1".to_string(), "Deep tech research park incubation ecosystem".to_string()),
            ("doc2".to_string(), "XYMA Analytics ultrasonic waveguide sensors for high temperature".to_string()),
            ("doc3".to_string(), "Financial statement audited revenue and expenditure".to_string()),
        ];

        let index = CompactInvertedIndex::build(&docs, 1.2, 0.75);
        let results = index.search("waveguide sensors", 2);

        assert!(!results.is_empty());
        assert_eq!(results[0].0, "doc2");
    }
}
