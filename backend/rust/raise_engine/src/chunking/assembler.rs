//! Hierarchical Chunk Assembler (GGAHC Stages 14, 15, 16, 17).
//! Assembles Candidate Units into Child Chunks and Parent Chunks based on Boundary Decisions.

use super::types::{AdaptiveChunk, BoundaryDecision, BoundaryExplanation, CandidateUnit, ChunkingConfig, Proposition};
use std::collections::HashMap;

pub fn assemble_hierarchy(
    candidates: &[CandidateUnit],
    decisions: &[BoundaryExplanation],
    document_id: &str,
    university: &str,
    filename: &str,
    config: &ChunkingConfig,
) -> (Vec<AdaptiveChunk>, Vec<AdaptiveChunk>, Vec<Proposition>) {
    if candidates.is_empty() {
        return (Vec::new(), Vec::new(), Vec::new());
    }

    // 1. Group candidates into parent clusters based on boundary decisions
    let mut parent_clusters: Vec<Vec<usize>> = Vec::new();
    let mut current_cluster: Vec<usize> = vec![0];

    for i in 0..candidates.len().saturating_sub(1) {
        let next_idx = i + 1;
        let u_curr = &candidates[i];
        let u_next = &candidates[next_idx];
        let dec_opt = decisions.get(i);

        // Hard boundary rules:
        // If either unit is a table or figure, isolate it into its own cluster
        let is_special = u_curr.is_table || u_curr.is_figure || u_next.is_table || u_next.is_figure;
        let is_split = dec_opt.map(|d| d.decision == BoundaryDecision::Split).unwrap_or(false);

        if is_special || is_split {
            parent_clusters.push(current_cluster);
            current_cluster = vec![next_idx];
        } else {
            // MERGE or PRESERVE: check parent size constraint
            let current_tokens: usize = current_cluster.iter().map(|&idx| candidates[idx].token_estimate()).sum();
            let next_tokens = u_next.token_estimate();

            if current_tokens + next_tokens > config.max_parent_tokens {
                parent_clusters.push(current_cluster);
                current_cluster = vec![next_idx];
            } else {
                current_cluster.push(next_idx);
            }
        }
    }
    if !current_cluster.is_empty() {
        parent_clusters.push(current_cluster);
    }

    let mut parent_chunks = Vec::new();
    let mut child_chunks = Vec::new();
    let mut all_propositions = Vec::new();

    let mut parent_counter = 0;
    let mut child_counter = 0;
    let mut prop_counter = 0;

    for cluster in parent_clusters {
        parent_counter += 1;
        let p_id = format!("{}_pchk_{:03}", document_id, parent_counter);

        let cluster_units: Vec<&CandidateUnit> = cluster.iter().map(|&idx| &candidates[idx]).collect();
        let first_u = cluster_units[0];
        let last_u = cluster_units[cluster_units.len() - 1];

        let parent_text = cluster_units
            .iter()
            .map(|u| u.plain_text.as_str())
            .collect::<Vec<&str>>()
            .join("\n\n");

        let mut parent_entities = Vec::new();
        let mut parent_relations = Vec::new();
        let mut parent_communities = Vec::new();
        let mut source_block_ids = Vec::new();

        for u in &cluster_units {
            parent_entities.extend(u.entities.clone());
            parent_relations.extend(u.relationships.clone());
            if let Some(comm) = &u.community_id {
                if !parent_communities.contains(comm) {
                    parent_communities.push(comm.clone());
                }
            }
            source_block_ids.extend(u.structural_unit_ids.clone());
        }

        let is_tab = cluster_units.iter().any(|u| u.is_table);
        let is_fig = cluster_units.iter().any(|u| u.is_figure);
        let pages: Vec<usize> = (first_u.page_start..=last_u.page_end).collect();

        let mut p_meta = HashMap::new();
        p_meta.insert("university".to_string(), serde_json::Value::String(university.to_string()));
        p_meta.insert("pdf_filename".to_string(), serde_json::Value::String(filename.to_string()));

        let parent_chunk = AdaptiveChunk {
            chunk_id: p_id.clone(),
            document_id: document_id.to_string(),
            parent_chunk_id: None,
            section_id: first_u.section_id.clone(),
            chunk_level: "parent".to_string(),
            plain_text: parent_text.clone(),
            contextualized_content: parent_text.clone(),
            summary: None,
            heading: first_u.heading.clone(),
            heading_level: 1,
            primary_page: first_u.page_start,
            printed_page: None,
            source_pages: pages.clone(),
            propositions: Vec::new(),
            entities: parent_entities,
            relationships: parent_relations,
            community_ids: parent_communities.clone(),
            source_block_ids,
            previous_chunk_id: None,
            next_chunk_id: None,
            token_estimate: parent_text.split_whitespace().count().max(1),
            boundary_score_before: 0.0,
            boundary_score_after: 0.0,
            boundary_reasons: Vec::new(),
            chunking_strategy: config.strategy.clone(),
            is_table: is_tab,
            is_figure: is_fig,
            tables_count: if is_tab { 1 } else { 0 },
            metadata: p_meta.clone(),
        };

        parent_chunks.push(parent_chunk);

        // 2. Build child chunks from each candidate in cluster
        for &cand_idx in &cluster {
            let u = &candidates[cand_idx];
            child_counter += 1;
            let c_id = format!("{}_chk_{:04}", document_id, child_counter);

            let score_before = if cand_idx > 0 && cand_idx - 1 < decisions.len() {
                decisions[cand_idx - 1].boundary_score
            } else {
                0.0
            };
            let (score_after, reasons) = if cand_idx < decisions.len() {
                (decisions[cand_idx].boundary_score, decisions[cand_idx].reasons.clone())
            } else {
                (0.0, Vec::new())
            };

            // Extract atomic propositions for child chunk
            let mut chunk_props = Vec::new();
            for sent in u.plain_text.split(|c| c == '.' || c == '?' || c == '!') {
                let trimmed = sent.trim();
                if trimmed.len() > 15 {
                    prop_counter += 1;
                    let prop = Proposition {
                        proposition_id: format!("{}_prop_{:04}", document_id, prop_counter),
                        text: trimmed.to_string(),
                        parent_chunk_id: c_id.clone(),
                        document_id: document_id.to_string(),
                        section_id: u.section_id.clone(),
                        page_number: u.page_start,
                        entities: u.entities.iter().map(|e| e.id.clone()).collect(),
                    };
                    chunk_props.push(prop.clone());
                    all_propositions.push(prop);
                }
            }

            let child_chunk = AdaptiveChunk {
                chunk_id: c_id,
                document_id: document_id.to_string(),
                parent_chunk_id: Some(p_id.clone()),
                section_id: u.section_id.clone(),
                chunk_level: "child".to_string(),
                plain_text: u.plain_text.clone(),
                contextualized_content: u.plain_text.clone(),
                summary: None,
                heading: u.heading.clone(),
                heading_level: 2,
                primary_page: u.page_start,
                printed_page: None,
                source_pages: (u.page_start..=u.page_end).collect(),
                propositions: chunk_props,
                entities: u.entities.clone(),
                relationships: u.relationships.clone(),
                community_ids: u.community_id.clone().into_iter().collect(),
                source_block_ids: u.structural_unit_ids.clone(),
                previous_chunk_id: None,
                next_chunk_id: None,
                token_estimate: u.token_estimate(),
                boundary_score_before: score_before,
                boundary_score_after: score_after,
                boundary_reasons: reasons,
                chunking_strategy: config.strategy.clone(),
                is_table: u.is_table,
                is_figure: u.is_figure,
                tables_count: if u.is_table { 1 } else { 0 },
                metadata: p_meta.clone(),
            };

            child_chunks.push(child_chunk);
        }
    }

    // Link previous and next chunk pointers
    let c_len = child_chunks.len();
    for i in 0..c_len {
        let prev = if i > 0 { Some(child_chunks[i - 1].chunk_id.clone()) } else { None };
        let next = if i + 1 < c_len { Some(child_chunks[i + 1].chunk_id.clone()) } else { None };
        child_chunks[i].previous_chunk_id = prev;
        child_chunks[i].next_chunk_id = next;
    }

    (child_chunks, parent_chunks, all_propositions)
}
