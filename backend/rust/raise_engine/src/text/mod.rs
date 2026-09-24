pub mod dedup;
pub mod headers;
pub mod hyphenation;
pub mod normalize;
pub mod whitespace;

pub use dedup::{fnv1a_64, hamming_distance, hash_text, simhash_64};
pub use headers::remove_repeated_headers_footers;
pub use hyphenation::repair_hyphenation;
pub use normalize::normalize_text;
pub use whitespace::cleanup_whitespace;

/// Full composite text cleanup pipeline:
/// Unicode normalization -> whitespace consolidation -> hyphen repair
pub fn clean_document_text(raw: &str) -> String {
    let s = normalize_text(raw);
    let s = repair_hyphenation(&s);
    cleanup_whitespace(&s)
}
