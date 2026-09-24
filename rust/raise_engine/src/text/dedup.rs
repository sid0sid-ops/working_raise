//! Fast text hashing and deduplication primitives.

use sha2::{Digest, Sha256};

/// Computes SHA-256 hash of normalized text for exact deduplication.
pub fn hash_text(text: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(text.as_bytes());
    format!("{:x}", hasher.finalize())
}

/// Computes 64-bit FNV-1a hash for fast in-memory similarity or deduplication tables.
pub fn fnv1a_64(text: &str) -> u64 {
    let mut hash: u64 = 0xcbf29ce484222325;
    for byte in text.bytes() {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

/// Computes 64-bit SimHash of text based on token frequencies for near-duplicate detection.
pub fn simhash_64(tokens: &[&str]) -> u64 {
    let mut v = [0i32; 64];

    for token in tokens {
        let clean = token.trim_matches(|c: char| !c.is_alphanumeric()).to_lowercase();
        if clean.is_empty() {
            continue;
        }
        let h = fnv1a_64(&clean);
        for i in 0..64 {
            let bit = (h >> i) & 1;
            if bit == 1 {
                v[i] += 1;
            } else {
                v[i] -= 1;
            }
        }
    }

    let mut fingerprint: u64 = 0;
    for i in 0..64 {
        if v[i] > 0 {
            fingerprint |= 1 << i;
        }
    }

    fingerprint
}

/// Computes Hamming distance between two 64-bit SimHash fingerprints.
pub fn hamming_distance(a: u64, b: u64) -> u32 {
    (a ^ b).count_ones()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hash_and_simhash() {
        let t1 = "Deep-tech incubation at IIT Madras Research Park ecosystem.";
        let t2 = "Deep tech incubation at IIT Madras Research Park ecosystem!";
        let tokens1: Vec<&str> = t1.split_whitespace().collect();
        let tokens2: Vec<&str> = t2.split_whitespace().collect();

        let s1 = simhash_64(&tokens1);
        let s2 = simhash_64(&tokens2);

        let dist = hamming_distance(s1, s2);
        assert!(dist <= 15, "Hamming distance should be small for near duplicates, got {}", dist);
    }
}
