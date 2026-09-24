//! Graph traversal algorithms: BFS, shortest path, and reachability.

use super::builder::AdjacencyGraph;
use std::collections::VecDeque;

/// Computes the unweighted shortest path length between two node IDs using BFS.
pub fn shortest_path_length(graph: &AdjacencyGraph, start_id: &str, target_id: &str) -> Option<usize> {
    let start_idx = graph.get_node_index(start_id)?;
    let target_idx = graph.get_node_index(target_id)?;

    if start_idx == target_idx {
        return Some(0);
    }

    let mut visited = vec![false; graph.nodes.len()];
    let mut distances = vec![usize::MAX; graph.nodes.len()];
    let mut queue = VecDeque::new();

    visited[start_idx] = true;
    distances[start_idx] = 0;
    queue.push_back(start_idx);

    while let Some(curr) = queue.pop_front() {
        if curr == target_idx {
            return Some(distances[curr]);
        }

        let next_dist = distances[curr] + 1;
        // Optimization: bounded search if path exceeds 6 hops, stop
        if next_dist > 6 {
            continue;
        }

        for edge in &graph.adj[curr] {
            if !visited[edge.target] {
                visited[edge.target] = true;
                distances[edge.target] = next_dist;
                queue.push_back(edge.target);
            }
        }
    }

    None
}

/// Checks if a path exists between two node IDs.
pub fn has_path(graph: &AdjacencyGraph, start_id: &str, target_id: &str) -> bool {
    shortest_path_length(graph, start_id, target_id).is_some()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::graph::builder::NodeType;

    #[test]
    fn test_shortest_path_candidate_entity_candidate() {
        let mut g = AdjacencyGraph::new();
        let c1 = g.add_or_get_node("cand_1", NodeType::Candidate, None, 1);
        let e1 = g.add_or_get_node("ent_xyma", NodeType::Entity, None, 1);
        let c2 = g.add_or_get_node("cand_2", NodeType::Candidate, None, 2);

        g.add_edge(c1, e1, "MENTIONS");
        g.add_edge(c2, e1, "MENTIONS");

        let dist = shortest_path_length(&g, "cand_1", "cand_2");
        assert_eq!(dist, Some(2));
    }
}
