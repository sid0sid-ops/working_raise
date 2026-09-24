//! Proposition extractor from text.

use super::types::Proposition;

/// Extracts atomic propositions from sentences in a text block with provenance links.
pub fn extract_propositions(
    text: &str,
    parent_chunk_id: &str,
    document_id: &str,
    section_id: &str,
    page_number: usize,
    entities: &[String],
) -> Vec<Proposition> {
    let mut props = Vec::new();
    let mut counter = 0;

    for sent in text.split(|c| c == '.' || c == '?' || c == '!') {
        let trimmed = sent.trim();
        if trimmed.len() > 15 {
            counter += 1;
            props.push(Proposition {
                proposition_id: format!("{}_prop_{:04}", parent_chunk_id, counter),
                text: trimmed.to_string(),
                parent_chunk_id: parent_chunk_id.to_string(),
                document_id: document_id.to_string(),
                section_id: section_id.to_string(),
                page_number,
                entities: entities.to_vec(),
            });
        }
    }

    props
}
