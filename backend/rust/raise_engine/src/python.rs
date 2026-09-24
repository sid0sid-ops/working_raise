//! PyO3 native Python extension bindings for the RAISE Acceleration Engine.
//! Exposes direct Python bindings using the PyO3 C-API interface.

#[cfg(feature = "python")]
use pyo3::exceptions::PyValueError;
#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
use crate::chunking::assembler::assemble_hierarchy as rust_assemble_hierarchy;
#[cfg(feature = "python")]
use crate::chunking::optimizer::evaluate_boundaries_batch as rust_evaluate_boundaries_batch;
#[cfg(feature = "python")]
use crate::chunking::types::{CandidateUnit, ChunkingConfig};
#[cfg(feature = "python")]
use crate::provenance::claim_fingerprint as rust_claim_fingerprint;
#[cfg(feature = "python")]
use crate::retrieval::bm25::CompactInvertedIndex;
#[cfg(feature = "python")]
use crate::retrieval::ranking::{select_top_k, CandidateScore};
#[cfg(feature = "python")]
use crate::retrieval::rrf::reciprocal_rank_fusion as rust_reciprocal_rank_fusion;
#[cfg(feature = "python")]
use crate::text::clean_document_text;

/// Normalizes Unicode, cleans whitespace, and repairs hyphenated line breaks.
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "clean_text")]
pub fn py_clean_text(text: &str) -> PyResult<String> {
    Ok(clean_document_text(text))
}

/// Evaluates boundary decisions across candidate units using the 8-signal graph formula.
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "evaluate_boundaries")]
pub fn py_evaluate_boundaries(candidates_json: &str, config_json: &str) -> PyResult<String> {
    let candidates: Vec<CandidateUnit> = serde_json::from_str(candidates_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid candidates JSON: {}", e)))?;

    let config: ChunkingConfig = if config_json.trim().is_empty() {
        ChunkingConfig::default()
    } else {
        serde_json::from_str(config_json)
            .map_err(|e| PyValueError::new_err(format!("Invalid config JSON: {}", e)))?
    };

    let (decisions, _graph, communities) = rust_evaluate_boundaries_batch(&candidates, &config);

    #[derive(serde::Serialize)]
    struct Output {
        decisions: Vec<crate::chunking::types::BoundaryExplanation>,
        communities: std::collections::HashMap<String, String>,
    }

    let out = Output {
        decisions,
        communities,
    };

    serde_json::to_string(&out)
        .map_err(|e| PyValueError::new_err(format!("Serialization error: {}", e)))
}

/// Evaluates boundary decisions from a flat buffer of compact numeric features (Pattern 2).
/// Zero JSON parsing, zero string allocations.
/// Each feature row consists of 11 values:
/// [tokens_a, tokens_b, is_table_or_figure, structural_strength, semantic_discontinuity,
///  topic_transition, entity_continuity, relationship_continuity, graph_connectivity,
///  community_continuity, cross_section].
/// Returns: Vec<(u8, f32, f32)> -> (decision_code, boundary_score, confidence).
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "evaluate_boundaries_compact", signature = (features_flat, config_json=None))]
pub fn py_evaluate_boundaries_compact(
    features_flat: Vec<f32>,
    config_json: Option<&str>,
) -> PyResult<Vec<(u8, f32, f32)>> {

    let row_len = 11;
    if features_flat.len() % row_len != 0 {
        return Err(PyValueError::new_err(format!(
            "Input flat buffer length ({}) must be a multiple of {}",
            features_flat.len(),
            row_len
        )));
    }

    let config: ChunkingConfig = match config_json {
        Some(s) if !s.trim().is_empty() => serde_json::from_str(s)
            .map_err(|e| PyValueError::new_err(format!("Invalid config JSON: {}", e)))?,
        _ => ChunkingConfig::default(),
    };

    let num_rows = features_flat.len() / row_len;
    let mut compact_inputs = Vec::with_capacity(num_rows);
    for i in 0..num_rows {
        let base = i * row_len;
        compact_inputs.push(crate::chunking::types::CompactBoundaryFeature {
            tokens_a: features_flat[base] as u32,
            tokens_b: features_flat[base + 1] as u32,
            is_table_or_figure: features_flat[base + 2] > 0.5,
            structural_strength: features_flat[base + 3],
            semantic_discontinuity: features_flat[base + 4],
            topic_transition: features_flat[base + 5],
            entity_continuity: features_flat[base + 6],
            relationship_continuity: features_flat[base + 7],
            graph_connectivity: features_flat[base + 8],
            community_continuity: features_flat[base + 9],
            cross_section: features_flat[base + 10],
        });
    }

    let results = crate::chunking::scoring::evaluate_compact_features(&compact_inputs, &config);
    let output = results
        .into_iter()
        .map(|r| (r.decision, r.boundary_score, r.confidence))
        .collect();

    Ok(output)
}


/// Assembles hierarchical parent chunks and child chunks with provenance.
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "assemble_hierarchy")]
pub fn py_assemble_hierarchy(
    candidates_json: &str,
    decisions_json: &str,
    document_id: &str,
    university: &str,
    filename: &str,
    config_json: &str,
) -> PyResult<String> {
    let candidates: Vec<CandidateUnit> = serde_json::from_str(candidates_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid candidates JSON: {}", e)))?;
    let decisions: Vec<crate::chunking::types::BoundaryExplanation> = serde_json::from_str(decisions_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid decisions JSON: {}", e)))?;
    let config: ChunkingConfig = if config_json.trim().is_empty() {
        ChunkingConfig::default()
    } else {
        serde_json::from_str(config_json)
            .map_err(|e| PyValueError::new_err(format!("Invalid config JSON: {}", e)))?
    };

    let (child_chunks, parent_chunks, propositions) = rust_assemble_hierarchy(
        &candidates,
        &decisions,
        document_id,
        university,
        filename,
        &config,
    );

    #[derive(serde::Serialize)]
    struct Output {
        child_chunks: Vec<crate::chunking::types::AdaptiveChunk>,
        parent_chunks: Vec<crate::chunking::types::AdaptiveChunk>,
        propositions: Vec<crate::chunking::types::Proposition>,
    }

    let out = Output {
        child_chunks,
        parent_chunks,
        propositions,
    };

    serde_json::to_string(&out)
        .map_err(|e| PyValueError::new_err(format!("Serialization error: {}", e)))
}

/// Compact Inverted Index & Okapi BM25 retrieval over documents.
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "bm25_search")]
pub fn py_bm25_search(docs_json: &str, query: &str, top_k: usize, k1: f32, b: f32) -> PyResult<String> {
    let docs: Vec<(String, String)> = serde_json::from_str(docs_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid docs JSON: {}", e)))?;

    let index = CompactInvertedIndex::build(&docs, k1, b);
    let results = index.search(query, top_k);

    serde_json::to_string(&results)
        .map_err(|e| PyValueError::new_err(format!("Serialization error: {}", e)))
}

/// High-throughput candidate pre-ranking via QuickSelect.
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "rank_candidates")]
pub fn py_rank_candidates(candidates_json: &str, top_k: usize) -> PyResult<String> {
    let mut candidates: Vec<CandidateScore> = serde_json::from_str(candidates_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid candidates JSON: {}", e)))?;

    let top = select_top_k(&mut candidates, top_k);

    serde_json::to_string(top)
        .map_err(|e| PyValueError::new_err(format!("Serialization error: {}", e)))
}

/// Reciprocal Rank Fusion across multi-channel results.
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "reciprocal_rank_fusion")]
pub fn py_reciprocal_rank_fusion(channels_json: &str, k: usize) -> PyResult<String> {
    let channels: Vec<Vec<String>> = serde_json::from_str(channels_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid channels JSON: {}", e)))?;

    let results = rust_reciprocal_rank_fusion(&channels, k);

    serde_json::to_string(&results)
        .map_err(|e| PyValueError::new_err(format!("Serialization error: {}", e)))
}

/// Deterministic SHA-256 fingerprint for claims.
#[cfg(feature = "python")]
#[pyfunction]
#[pyo3(name = "claim_fingerprint")]
pub fn py_claim_fingerprint(claim_text: &str, doc_id: &str, page: usize) -> PyResult<String> {
    Ok(rust_claim_fingerprint(claim_text, doc_id, page))
}

/// Native PyO3 Module Initialization
#[cfg(feature = "python")]
#[pymodule]
pub fn raise_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_clean_text, m)?)?;
    m.add_function(wrap_pyfunction!(py_evaluate_boundaries, m)?)?;
    m.add_function(wrap_pyfunction!(py_evaluate_boundaries_compact, m)?)?;
    m.add_function(wrap_pyfunction!(py_assemble_hierarchy, m)?)?;
    m.add_function(wrap_pyfunction!(py_bm25_search, m)?)?;
    m.add_function(wrap_pyfunction!(py_rank_candidates, m)?)?;
    m.add_function(wrap_pyfunction!(py_reciprocal_rank_fusion, m)?)?;
    m.add_function(wrap_pyfunction!(py_claim_fingerprint, m)?)?;
    Ok(())

}
