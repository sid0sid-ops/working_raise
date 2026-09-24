//! RAISE Performance Acceleration Engine (raise_engine)
//! High-speed native core for Graph-Guided Adaptive Hierarchical Chunking (GGAHC),
//! lexical retrieval (BM25), graph analytics, candidate pre-ranking, and text normalization.

pub mod chunking;
pub mod ffi;
pub mod graph;
pub mod provenance;
pub mod python;
pub mod retrieval;
pub mod text;

pub use chunking::*;
pub use ffi::*;
pub use graph::*;
pub use provenance::*;
#[cfg(feature = "python")]
pub use python::*;
pub use retrieval::{bm25, ranking, rrf, similarity};
pub use text::{clean_document_text, headers, hyphenation, normalize, whitespace};
