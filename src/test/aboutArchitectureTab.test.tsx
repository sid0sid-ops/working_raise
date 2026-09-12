import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SettingsAboutTab } from '../components/settings/SettingsAboutTab';
import { RaisePage } from '../features/raise/RaisePage';

describe('Settings About & Architecture Pipeline Routing', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('SettingsAboutTab Component', () => {
    it('renders the dual routing architecture with Fast Mode and Expert Mode cards', () => {
      render(<SettingsAboutTab />);

      // Verify Fast Mode card
      const fastCard = screen.getByTestId('architecture-fast-mode-card');
      expect(fastCard).toBeInTheDocument();
      expect(fastCard).toHaveTextContent(/Fast Mode/i);
      expect(fastCard).toHaveTextContent(/BM25 \+ Vector \(k=4\)/i);
      expect(fastCard).toHaveTextContent(/1-Hop Subgraph/i);
      expect(fastCard).toHaveTextContent(/Speed Optimized/i);

      // Verify Expert Mode card
      const expertCard = screen.getByTestId('architecture-expert-mode-card');
      expect(expertCard).toBeInTheDocument();
      expect(expertCard).toHaveTextContent(/Expert Mode/i);
      expect(expertCard).toHaveTextContent(/Table Chunk Boosting/i);
      expect(expertCard).toHaveTextContent(/2-3 Hop Neo4j Graph/i);
      expect(expertCard).toHaveTextContent(/Cross-Encoder Rerank/i);
      expect(expertCard).toHaveTextContent(/Deep Reasoning/i);
    });

    it('toggles the exact ASCII blueprint diagram', () => {
      render(<SettingsAboutTab />);

      // Initially ASCII view is closed
      const toggleBtn = screen.getByRole('button', { name: /Show ASCII Blueprint/i });
      expect(toggleBtn).toBeInTheDocument();

      // Click to expand ASCII diagram
      fireEvent.click(toggleBtn);
      expect(screen.getByText(/Architectural Pipeline Routing Tree/i)).toBeInTheDocument();
      expect(screen.getAllByText(/FAST MODE/i).length).toBeGreaterThanOrEqual(2);
      expect(screen.getAllByText(/EXPERT MODE/i).length).toBeGreaterThanOrEqual(2);

      // Click to hide
      fireEvent.click(screen.getByRole('button', { name: /Hide ASCII Blueprint/i }));
      expect(screen.queryByText(/Architectural Pipeline Routing Tree/i)).not.toBeInTheDocument();
    });

    it('displays full substrate specifications (ChromaDB, Neo4j, vLLM, IBM Docling)', () => {
      render(<SettingsAboutTab />);

      expect(screen.getByText('ChromaDB')).toBeInTheDocument();
      expect(screen.getByText(/BGE-Large-EN/i)).toBeInTheDocument();
      expect(screen.getByText('Neo4j 5.x')).toBeInTheDocument();
      expect(screen.getByText(/Bolt Protocol • Cypher Traversal/i)).toBeInTheDocument();
      expect(screen.getByText('IBM Docling Engine')).toBeInTheDocument();
    });
  });

  describe('Integration within RaisePage Settings Modal', () => {
    it('allows navigating to About tab and renders the architecture blueprint', () => {
      render(<RaisePage />);

      // Open settings
      const userBtn = screen.queryByTestId('user-gateway-menu-btn');
      if (userBtn) {
        fireEvent.click(userBtn);
        const settingsBtn = screen.getByTestId('rail-settings-btn');
        fireEvent.click(settingsBtn);
      } else {
        const settingsBtn = screen.getByTestId('sidebar-settings-btn');
        fireEvent.click(settingsBtn);
      }

      // Click About tab
      const aboutTabBtn = screen.getByTestId('settings-nav-about-btn');
      fireEvent.click(aboutTabBtn);

      // Verify About tab is active and shows Fast Mode / Expert Mode
      expect(screen.getByTestId('settings-about-tab')).toBeInTheDocument();
      expect(screen.getByTestId('architecture-fast-mode-card')).toBeInTheDocument();
      expect(screen.getByTestId('architecture-expert-mode-card')).toBeInTheDocument();
    });

    it('displays pipeline architecture inside the Help tab as well', () => {
      render(<RaisePage />);

      // Open settings
      const userBtn = screen.queryByTestId('user-gateway-menu-btn');
      if (userBtn) {
        fireEvent.click(userBtn);
        const settingsBtn = screen.getByTestId('rail-settings-btn');
        fireEvent.click(settingsBtn);
      } else {
        const settingsBtn = screen.getByTestId('sidebar-settings-btn');
        fireEvent.click(settingsBtn);
      }

      // Click Help tab
      const helpButtons = screen.getAllByRole('button', { name: /Help/i });
      fireEvent.click(helpButtons[0]);

      // Verify Help tab contains pipeline routing architecture with Fast and Expert mode
      expect(screen.getByText(/Pipeline Routing Architecture/i)).toBeInTheDocument();
      expect(screen.getByText(/Table Chunk Boosting/i)).toBeInTheDocument();
      expect(screen.getByText(/1-Hop Subgraph/i)).toBeInTheDocument();
    });
  });
});
