import React from 'react';
import { GraphNode } from '../../types';
import { Modal } from '../ui/Modal';
import { Badge } from '../ui/Badge';
import { Layers, FileText } from 'lucide-react';

export interface NodeDetailsModalProps {
  node: GraphNode | null;
  onClose: () => void;
}

export const NodeDetailsModal: React.FC<NodeDetailsModalProps> = ({ node, onClose }) => {
  if (!node) return null;

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={node.name}
      subtitle={`Knowledge Graph Entity (${node.type})`}
      maxWidth="md"
    >
      <div className="space-y-4 text-xs">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-bold">Node ID</span>
            <span className="font-mono text-slate-300">{node.id}</span>
          </div>
          <Badge variant="info">{node.type}</Badge>
        </div>

        {/* Provenance Properties */}
        {node.provenance && Object.keys(node.provenance).length > 0 && (
          <div>
            <h4 className="text-slate-300 font-semibold mb-2 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-sky-400" /> Provenance & Properties
            </h4>
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 space-y-2 font-mono text-[11px]">
              {Object.entries(node.provenance).map(([key, value]) => (
                <div key={key} className="flex items-start justify-between gap-4">
                  <span className="text-slate-500 shrink-0 capitalize">
                    {key.replace(/_/g, ' ')}:
                  </span>
                  <span className="text-slate-200 text-right font-sans">
                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Hint */}
        <div className="p-3 bg-slate-900/60 rounded border border-slate-800 text-slate-400 text-[11px] flex items-center gap-2">
          <FileText className="w-4 h-4 text-sky-400 shrink-0" />
          <span>
            Entities in this graph were extracted directly from audited institutional reports using Neo4j property graph mapping.
          </span>
        </div>
      </div>
    </Modal>
  );
};
