//! C-ABI and JSON Foreign Function Interface (FFI) for Python integration.
//! Allows zero-cost interoperability via Python ctypes, cffi, or native shared libraries.

use std::ffi::{CStr, CString};
use std::os::raw::c_char;

use crate::chunking::assembler::assemble_hierarchy;
use crate::chunking::optimizer::evaluate_boundaries_batch;
use crate::chunking::types::{CandidateUnit, ChunkingConfig};
use crate::retrieval::bm25::CompactInvertedIndex;
use crate::retrieval::ranking::{select_top_k, CandidateScore};
use crate::retrieval::rrf::reciprocal_rank_fusion;
use crate::text::clean_document_text;

fn c_str_to_str<'a>(ptr: *const c_char) -> Option<&'a str> {
    if ptr.is_null() {
        return None;
    }
    unsafe { CStr::from_ptr(ptr).to_str().ok() }
}

fn to_c_string(s: String) -> *mut c_char {
    match CString::new(s) {
        Ok(c_str) => c_str.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Frees a C-string allocated by Rust.
#[no_mangle]
pub extern "C" fn raise_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe {
            let _ = CString::from_raw(ptr);
        }
    }
}

/// Evaluates chunk boundaries across a batch of candidates in Rust.
#[no_mangle]
pub extern "C" fn raise_evaluate_boundaries(json_in: *const c_char) -> *mut c_char {
    let input_str = match c_str_to_str(json_in) {
        Some(s) => s,
        None => return std::ptr::null_mut(),
    };

    #[derive(serde::Deserialize)]
    struct Input {
        candidates: Vec<CandidateUnit>,
        #[serde(default)]
        config: ChunkingConfig,
    }

    #[derive(serde::Serialize)]
    struct Output {
        decisions: Vec<crate::chunking::types::BoundaryExplanation>,
        communities: std::collections::HashMap<String, String>,
    }

    let parsed: Input = match serde_json::from_str(input_str) {
        Ok(data) => data,
        Err(e) => {
            return to_c_string(format!("{{\"error\": \"JSON parse error: {}\"}}", e));
        }
    };

    let (decisions, _graph, communities) = evaluate_boundaries_batch(&parsed.candidates, &parsed.config);
    let out = Output {
        decisions,
        communities,
    };

    match serde_json::to_string(&out) {
        Ok(json_out) => to_c_string(json_out),
        Err(e) => to_c_string(format!("{{\"error\": \"JSON serialize error: {}\"}}", e)),
    }
}

/// Assembles hierarchical parent chunks and child chunks in Rust.
#[no_mangle]
pub extern "C" fn raise_assemble_hierarchy(json_in: *const c_char) -> *mut c_char {
    let input_str = match c_str_to_str(json_in) {
        Some(s) => s,
        None => return std::ptr::null_mut(),
    };

    #[derive(serde::Deserialize)]
    struct Input {
        candidates: Vec<CandidateUnit>,
        decisions: Vec<crate::chunking::types::BoundaryExplanation>,
        document_id: String,
        university: String,
        filename: String,
        #[serde(default)]
        config: ChunkingConfig,
    }

    #[derive(serde::Serialize)]
    struct Output {
        child_chunks: Vec<crate::chunking::types::AdaptiveChunk>,
        parent_chunks: Vec<crate::chunking::types::AdaptiveChunk>,
        propositions: Vec<crate::chunking::types::Proposition>,
    }

    let parsed: Input = match serde_json::from_str(input_str) {
        Ok(data) => data,
        Err(e) => return to_c_string(format!("{{\"error\": \"{}\"}}", e)),
    };

    let (child_chunks, parent_chunks, propositions) = assemble_hierarchy(
        &parsed.candidates,
        &parsed.decisions,
        &parsed.document_id,
        &parsed.university,
        &parsed.filename,
        &parsed.config,
    );

    let out = Output {
        child_chunks,
        parent_chunks,
        propositions,
    };

    match serde_json::to_string(&out) {
        Ok(s) => to_c_string(s),
        Err(e) => to_c_string(format!("{{\"error\": \"{}\"}}", e)),
    }
}

/// Executes Reciprocal Rank Fusion across multiple ranked candidate channels.
#[no_mangle]
pub extern "C" fn raise_reciprocal_rank_fusion(json_in: *const c_char) -> *mut c_char {
    let input_str = match c_str_to_str(json_in) {
        Some(s) => s,
        None => return std::ptr::null_mut(),
    };

    #[derive(serde::Deserialize)]
    struct Input {
        ranked_channels: Vec<Vec<String>>,
        #[serde(default = "default_rrf_k")]
        k: usize,
    }
    fn default_rrf_k() -> usize { 60 }

    #[derive(serde::Serialize)]
    struct Output {
        results: Vec<crate::retrieval::rrf::RrfResult>,
    }

    let parsed: Input = match serde_json::from_str(input_str) {
        Ok(d) => d,
        Err(e) => return to_c_string(format!("{{\"error\": \"{}\"}}", e)),
    };

    let results = reciprocal_rank_fusion(&parsed.ranked_channels, parsed.k);
    let out = Output { results };

    match serde_json::to_string(&out) {
        Ok(s) => to_c_string(s),
        Err(e) => to_c_string(format!("{{\"error\": \"{}\"}}", e)),
    }
}

/// Performs BM25 search over an in-memory collection of documents.
#[no_mangle]
pub extern "C" fn raise_bm25_search(json_in: *const c_char) -> *mut c_char {
    let input_str = match c_str_to_str(json_in) {
        Some(s) => s,
        None => return std::ptr::null_mut(),
    };

    #[derive(serde::Deserialize)]
    struct Input {
        docs: Vec<(String, String)>,
        query: String,
        top_k: usize,
        #[serde(default = "default_k1")]
        k1: f32,
        #[serde(default = "default_b")]
        b: f32,
    }
    fn default_k1() -> f32 { 1.2 }
    fn default_b() -> f32 { 0.75 }

    #[derive(serde::Serialize)]
    struct Output {
        results: Vec<(String, f32)>,
    }

    let parsed: Input = match serde_json::from_str(input_str) {
        Ok(d) => d,
        Err(e) => return to_c_string(format!("{{\"error\": \"{}\"}}", e)),
    };

    let index = CompactInvertedIndex::build(&parsed.docs, parsed.k1, parsed.b);
    let results = index.search(&parsed.query, parsed.top_k);
    let out = Output { results };

    match serde_json::to_string(&out) {
        Ok(s) => to_c_string(s),
        Err(e) => to_c_string(format!("{{\"error\": \"{}\"}}", e)),
    }
}

/// Pre-ranks candidate scores using O(N) QuickSelect Top-K.
#[no_mangle]
pub extern "C" fn raise_rank_candidates(json_in: *const c_char) -> *mut c_char {
    let input_str = match c_str_to_str(json_in) {
        Some(s) => s,
        None => return std::ptr::null_mut(),
    };

    #[derive(serde::Deserialize)]
    struct Input {
        candidates: Vec<CandidateScore>,
        top_k: usize,
    }

    #[derive(serde::Serialize)]
    struct Output {
        results: Vec<CandidateScore>,
    }

    let mut parsed: Input = match serde_json::from_str(input_str) {
        Ok(d) => d,
        Err(e) => return to_c_string(format!("{{\"error\": \"{}\"}}", e)),
    };

    let top = select_top_k(&mut parsed.candidates, parsed.top_k);
    let out = Output { results: top.to_vec() };

    match serde_json::to_string(&out) {
        Ok(s) => to_c_string(s),
        Err(e) => to_c_string(format!("{{\"error\": \"{}\"}}", e)),
    }
}

/// Cleans and normalizes text using the Rust text pipeline.
#[no_mangle]
pub extern "C" fn raise_normalize_text(json_in: *const c_char) -> *mut c_char {
    let input_str = match c_str_to_str(json_in) {
        Some(s) => s,
        None => return std::ptr::null_mut(),
    };

    #[derive(serde::Deserialize)]
    struct Input {
        text: String,
    }

    #[derive(serde::Serialize)]
    struct Output {
        cleaned_text: String,
    }

    let parsed: Input = match serde_json::from_str(input_str) {
        Ok(d) => d,
        Err(e) => return to_c_string(format!("{{\"error\": \"{}\"}}", e)),
    };

    let cleaned_text = clean_document_text(&parsed.text);
    let out = Output { cleaned_text };

    match serde_json::to_string(&out) {
        Ok(s) => to_c_string(s),
        Err(e) => to_c_string(format!("{{\"error\": \"{}\"}}", e)),
    }
}
