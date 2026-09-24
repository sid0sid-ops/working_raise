//! Repeated header and footer detection across multi-page documents.

use std::collections::HashMap;

/// Identifies recurring headers/footers across a list of page texts and removes them.
pub fn remove_repeated_headers_footers(pages: &[String], min_frequency_ratio: f32) -> Vec<String> {
    if pages.is_empty() {
        return Vec::new();
    }
    if pages.len() == 1 {
        return pages.to_vec();
    }

    let mut line_counts: HashMap<String, usize> = HashMap::new();
    let total_pages = pages.len();

    // Check first 3 lines (headers) and last 3 lines (footers) of each page
    for page in pages {
        let lines: Vec<&str> = page.lines().map(|l| l.trim()).filter(|l| !l.is_empty()).collect();
        let n = lines.len();
        if n == 0 {
            continue;
        }

        let header_candidates = &lines[..3.min(n)];
        let footer_candidates = &lines[n.saturating_sub(3)..];

        for h in header_candidates {
            if h.len() <= 120 {
                *line_counts.entry(h.to_string()).or_insert(0) += 1;
            }
        }
        for f in footer_candidates {
            if f.len() <= 120 {
                *line_counts.entry(f.to_string()).or_insert(0) += 1;
            }
        }
    }

    let threshold = ((total_pages as f32) * min_frequency_ratio).max(2.0) as usize;
    let boilerplate: std::collections::HashSet<String> = line_counts
        .into_iter()
        .filter(|(_, count)| *count >= threshold)
        .map(|(line, _)| line)
        .collect();

    pages
        .iter()
        .map(|page| {
            let filtered: Vec<&str> = page
                .lines()
                .filter(|line| !boilerplate.contains(line.trim()))
                .collect();
            filtered.join("\n")
        })
        .collect()
}
