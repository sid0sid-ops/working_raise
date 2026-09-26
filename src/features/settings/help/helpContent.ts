/**
 * ═══════════════════════════════════════════════════════════════════════════
 * RAISE SETTINGS: HELP CONTENT CONFIGURATION
 * ═══════════════════════════════════════════════════════════════════════════
 * Edit the content in this file to update the Help tab in Settings.
 * You can freely change descriptions, shortcuts, capabilities, and versions here
 * without modifying any component or CSS code.
 */

export interface KeyboardShortcutItem {
  label: string;
  keys: string[];
  separator?: string;
}

export interface KeyCapabilityItem {
  title: string;
  description: string;
}

export interface HelpContentConfig {
  header: {
    title: string;
    description: string;
  };
  shortcuts: {
    sectionTitle: string;
    items: KeyboardShortcutItem[];
  };
  capabilities: {
    sectionTitle: string;
    items: KeyCapabilityItem[];
  };
  architecture: {
    sectionTitle: string;
    linkText: string;
    asciiDiagram: string;
  };
  platform: {
    title: string;
    description: string;
    version: string;
  };
}

export const helpContent: HelpContentConfig = {
  // Top Header section
  header: {
    title: 'Help',
    description: 'Keyboard navigation shortcuts, feature reference, and system information.',
  },

  // Keyboard Shortcuts section
  shortcuts: {
    sectionTitle: 'Keyboard Shortcuts',
    items: [
      {
        label: 'Focus query input',
        keys: ['⌘/Ctrl + K'],
      },
      {
        label: 'Open settings',
        keys: ['⌘/Ctrl + /'],
      },
      {
        label: 'Close modal / drawer',
        keys: ['Esc'],
      },
      {
        label: 'Navigate suggestions',
        keys: ['↑', '↓'],
        separator: '/',
      },
      {
        label: 'Cycle citation cards',
        keys: ['Tab'],
      },
      {
        label: 'Send message',
        keys: ['Enter'],
      },
    ],
  },

  // Key Capabilities section
  capabilities: {
    sectionTitle: 'Key Capabilities',
    items: [
      {
        title: 'Interactive Citations & Evidence',
        description:
          'Click numbered citation chips ([1], [2]) directly inside AI responses to inspect document excerpts and verify exact factual grounding.',
      },
      {
        title: 'Session Scoped Sources Drawer',
        description:
          'Click the document icon in the top right to open the Sources Drawer. It shows only files uploaded to this specific chat session with accurate file sizes.',
      },
    ],
  },

  // Pipeline Routing Architecture preview
  architecture: {
    sectionTitle: 'Pipeline Routing Architecture',
    linkText: 'Full Specifications',
    asciiDiagram: `┌───────────────────┴───────────────────┐
        ▼                                       ▼
 ┌───────────────────────────┐   ┌───────────────────────────┐
 │       FAST MODE           │   │       EXPERT MODE         │
 │  • BM25 + Vector (k=4)    │   │  • Table Chunk Boosting   │
 │  • 1-Hop Subgraph         │   │  • 2-3 Hop Neo4j Graph    │
 │  • Low-Latency (<1.5s)    │   │  • Cross-Encoder Rerank   │
 └───────────────────────────┘   └───────────────────────────┘`,
  },

  // Platform info footer banner
  platform: {
    title: 'Raise RAG Platform',
    description: 'Hybrid Vector + BM25 Retrieval with GraphRAG Routing',
    version: 'v1.4.0',
  },
};

export default helpContent;
