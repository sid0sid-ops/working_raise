/**
 * ═══════════════════════════════════════════════════════════════════════════
 * RAISE SETTINGS: ABOUT & ARCHITECTURE CONTENT CONFIGURATION
 * ═══════════════════════════════════════════════════════════════════════════
 * Edit the content in this file to update the About tab in Settings.
 * You can freely change version numbers, descriptions, mode cards, bullet points,
 * and system substrate specs here without modifying any component or CSS code.
 */

export interface ModeFeatureItem {
  title: string;
  description: string;
}

export interface ArchitectureModeCard {
  testId: string;
  title: string;
  badge: string;
  badgeType: 'amber' | 'emerald';
  description: string;
  features: ModeFeatureItem[];
}

export interface SubstrateSpecItem {
  label: string;
  value: string;
  detail: string;
}

export interface AboutContentConfig {
  header: {
    title: string;
    version: string;
    description: string;
    showAsciiText: string;
    hideAsciiText: string;
  };
  asciiBlueprint: {
    sectionTitle: string;
    diagram: string;
  };
  routerNode: {
    category: string;
    title: string;
  };
  modes: {
    fastMode: ArchitectureModeCard;
    expertMode: ArchitectureModeCard;
  };
  substrateSpecs: {
    sectionTitle: string;
    items: SubstrateSpecItem[];
  };
}

export const aboutContent: AboutContentConfig = {
  // Main title, version badge, and intro text
  header: {
    title: 'About Raise GraphRAG',
    version: 'v1.4.0',
    description:
      'Hybrid Vector + BM25 retrieval with multi-hop Neo4j GraphRAG routing and real-time citation verification.',
    showAsciiText: 'Show ASCII Blueprint',
    hideAsciiText: 'Hide ASCII Blueprint',
  },

  // Expandable ASCII architectural pipeline diagram
  asciiBlueprint: {
    sectionTitle: 'Architectural Pipeline Routing Tree',
    diagram: `                      ┌─────────────────────────────────────────┐
                      │    LangGraph Intent Router & Intake     │
                      └────────────────────┬────────────────────┘
                                           │
                       ┌───────────────────┴───────────────────┐
                       ▼                                       ▼
        ┌───────────────────────────┐   ┌───────────────────────────┐
        │         FAST MODE         │   │        EXPERT MODE        │
        │  • BM25 + Vector (k=4)    │   │  • Table Chunk Boosting   │
        │  • 1-Hop Subgraph         │   │  • 2-3 Hop Neo4j Graph    │
        │  • Low-Latency Synthesis  │   │  • Cross-Encoder Rerank   │
        │  • Streaming Sub-1.5s     │   │  • Multi-Hop Claim Critic │
        └───────────────────────────┘   └───────────────────────────┘`,
  },

  // Central Router node above the dual mode tree
  routerNode: {
    category: 'Query Intake & Intent Router',
    title: 'LangGraph State Machine',
  },

  // Dual Routing Mode specifications
  modes: {
    // 1. FAST MODE
    fastMode: {
      testId: 'architecture-fast-mode-card',
      title: 'Fast Mode',
      badge: 'Speed Optimized',
      badgeType: 'amber',
      description:
        'Rapid direct retrieval for conversational inquiries, simple factual questions, and low-latency interaction.',
      features: [
        {
          title: 'BM25 + Vector (k=4)',
          description: 'Dense ChromaDB semantic embeddings fused with lexical BM25 token matching.',
        },
        {
          title: '1-Hop Subgraph',
          description: 'Immediate entity relations from local Neo4j graph without deep recursion.',
        },
        {
          title: 'Sub-1.5s Stream',
          description: 'Direct token streaming synthesis for instant answers.',
        },
      ],
    },

    // 2. EXPERT MODE
    expertMode: {
      testId: 'architecture-expert-mode-card',
      title: 'Expert Mode',
      badge: 'Deep Reasoning',
      badgeType: 'emerald',
      description:
        'Exhaustive graph traversal, structured table prioritization, and cross-encoder reranking for complex research.',
      features: [
        {
          title: 'Table Chunk Boosting',
          description:
            'Priority scoring for structured IBM Docling tables, CSV matrices, and financial disclosures.',
        },
        {
          title: '2-3 Hop Neo4j Graph',
          description:
            'Deep multi-step relational exploration across interconnected entity clusters.',
        },
        {
          title: 'Cross-Encoder Rerank',
          description: 'BGE/Cohere re-scoring to eliminate noisy context before LLM generation.',
        },
      ],
    },
  },

  // System Substrate Specifications grid
  substrateSpecs: {
    sectionTitle: 'System Substrate Specifications',
    items: [
      {
        label: 'Vector Database',
        value: 'ChromaDB',
        detail: 'BGE-Large-EN (1024-dim dense)',
      },
      {
        label: 'Knowledge Graph',
        value: 'Neo4j 5.x',
        detail: 'Bolt Protocol • Cypher Traversal',
      },
      {
        label: 'Inference Engine',
        value: 'Transformer LLM Substrate',
        detail: 'Grounded Synthesis & Streaming Tokens',
      },
      {
        label: 'Document Ingestion',
        value: 'IBM Docling Engine',
        detail: 'Synchronous Multi-Modal Chunking',
      },
    ],
  },
};

export default aboutContent;
