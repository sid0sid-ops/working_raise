//! Community detection using Label Propagation Algorithm (LPA) and Connected Components.

use super::builder::AdjacencyGraph;
use std::collections::HashMap;

/// Finds connected components in the graph and assigns comp_01, comp_02...
pub fn connected_components(graph: &AdjacencyGraph) -> HashMap<String, String> {
    let mut node_to_comp = HashMap::new();
    let n = graph.nodes.len();
    if n == 0 {
        return node_to_comp;
    }

    let mut visited = vec![false; n];
    let mut comp_idx = 1;

    for i in 0..n {
        if !visited[i] {
            let comp_label = format!("comp_{:02}", comp_idx);
            comp_idx += 1;

            let mut stack = vec![i];
            visited[i] = true;

            while let Some(curr) = stack.pop() {
                node_to_comp.insert(graph.nodes[curr].id.clone(), comp_label.clone());

                for edge in &graph.adj[curr] {
                    if !visited[edge.target] {
                        visited[edge.target] = true;
                        stack.push(edge.target);
                    }
                }
            }
        }
    }

    node_to_comp
}

/// Detects communities using the deterministic Label Propagation Algorithm (LPA).
pub fn detect_communities(graph: &AdjacencyGraph, max_iters: usize) -> HashMap<String, String> {
    let n = graph.nodes.len();
    if n == 0 {
        return HashMap::new();
    }

    // Initialize each node with its own label
    let mut labels: Vec<usize> = (0..n).collect();

    for _ in 0..max_iters {
        let mut changed = false;

        for i in 0..n {
            if graph.adj[i].is_empty() {
                continue;
            }

            // Count frequency of neighbor labels
            let mut freq: HashMap<usize, usize> = HashMap::new();
            for edge in &graph.adj[i] {
                *freq.entry(labels[edge.target]).or_insert(0) += 1;
            }

            // Pick most frequent label (tie-break with smallest label index)
            let mut best_label = labels[i];
            let mut max_count = 0;

            for (lbl, count) in freq {
                if count > max_count || (count == max_count && lbl < best_label) {
                    max_count = count;
                    best_label = lbl;
                }
            }

            if best_label != labels[i] {
                labels[i] = best_label;
                changed = true;
            }
        }

        if !changed {
            break;
        }
    }

    // Map unique label IDs to formatted strings comm_01, comm_02...
    let mut label_map: HashMap<usize, String> = HashMap::new();
    let mut comm_idx = 1;
    let mut result = HashMap::new();

    for i in 0..n {
        let raw_label = labels[i];
        let comm_label = label_map.entry(raw_label).or_insert_with(|| {
            let s = format!("comm_{:02}", comm_idx);
            comm_idx += 1;
            s
        });
        result.insert(graph.nodes[i].id.clone(), comm_label.clone());
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::graph::builder::NodeType;

    #[test]
    fn test_community_detection_triangle() {
        let mut g = AdjacencyGraph::new();
        let n1 = g.add_or_get_node("a", NodeType::Candidate, None, 1);
        let n2 = g.add_or_get_node("b", NodeType::Candidate, None, 1);
        let n3 = g.add_or_get_node("c", NodeType::Entity, None, 1);

        g.add_edge(n1, n2, "SIM");
        g.add_edge(n2, n3, "MENTIONS");
        g.add_edge(n3, n1, "MENTIONS");

        let comms = detect_communities(&g, 10);
        assert_eq!(comms.get("a"), comms.get("b"));
        assert_eq!(comms.get("b"), comms.get("c"));
    }
}
