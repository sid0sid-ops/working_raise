//! Temporary Graph Builder for Candidate Units, Entities, and Relationships.

use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq)]
pub enum NodeType {
    Candidate,
    Entity,
}

#[derive(Debug, Clone)]
pub struct Node {
    pub id: String,
    pub node_type: NodeType,
    pub heading: Option<String>,
    pub page: usize,
}

#[derive(Debug, Clone)]
pub struct Edge {
    pub target: usize,
    pub relation: String,
}

#[derive(Debug, Clone, Default)]
pub struct AdjacencyGraph {
    pub nodes: Vec<Node>,
    pub adj: Vec<Vec<Edge>>,
    pub node_map: HashMap<String, usize>,
}

impl AdjacencyGraph {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_or_get_node(&mut self, id: &str, node_type: NodeType, heading: Option<String>, page: usize) -> usize {
        if let Some(&idx) = self.node_map.get(id) {
            return idx;
        }
        let idx = self.nodes.len();
        self.nodes.push(Node {
            id: id.to_string(),
            node_type,
            heading,
            page,
        });
        self.adj.push(Vec::new());
        self.node_map.insert(id.to_string(), idx);
        idx
    }

    pub fn add_edge(&mut self, from: usize, to: usize, relation: &str) {
        if from >= self.nodes.len() || to >= self.nodes.len() {
            return;
        }
        // Undirected graph for boundary continuity and neighborhood checks
        self.adj[from].push(Edge {
            target: to,
            relation: relation.to_string(),
        });
        self.adj[to].push(Edge {
            target: from,
            relation: relation.to_string(),
        });
    }

    pub fn has_node(&self, id: &str) -> bool {
        self.node_map.contains_key(id)
    }

    pub fn get_node_index(&self, id: &str) -> Option<usize> {
        self.node_map.get(id).copied()
    }

    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }

    pub fn edge_count(&self) -> usize {
        self.adj.iter().map(|e| e.len()).sum::<usize>() / 2
    }
}
