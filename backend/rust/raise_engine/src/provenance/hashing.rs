//! Deterministic provenance hashing and claim fingerprinting.

use sha2::{Digest, Sha256};

/// Generates a deterministic SHA-256 fingerprint for a document page.
pub fn hash_page(doc_id: &str, page: usize, content: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(doc_id.as_bytes());
    hasher.update(page.to_string().as_bytes());
    hasher.update(content.as_bytes());
    format!("{:x}", hasher.finalize())
}

/// Generates a deterministic SHA-256 fingerprint for an extracted claim or proposition.
pub fn claim_fingerprint(claim_text: &str, doc_id: &str, page: usize) -> String {
    let mut hasher = Sha256::new();
    let norm = claim_text.trim().to_lowercase();
    hasher.update(norm.as_bytes());
    hasher.update(doc_id.as_bytes());
    hasher.update(page.to_string().as_bytes());
    format!("clm_{:.16x}", hasher.finalize())
}
