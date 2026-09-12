import React from 'react';
import { VerifiedClaim, Citation } from '../../types';
import { Badge } from '../ui/Badge';
import { CitationBadge } from '../citations/CitationBadge';
import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';

export interface VerifiedClaimsTableProps {
  claims: VerifiedClaim[];
  citations?: Citation[];
}

export const VerifiedClaimsTable: React.FC<VerifiedClaimsTableProps> = ({
  claims,
  citations = [],
}) => {
  if (!claims || claims.length === 0) {
    return (
      <div className="p-6 text-center text-slate-500 text-xs">
        No decomposed claims available for this query.
      </div>
    );
  }

  const getStatusBadge = (status: string, isSupported: boolean) => {
    if (status === 'SUPPORTED' || isSupported) {
      return (
        <Badge variant="success" className="gap-1">
          <CheckCircle2 className="w-3 h-3" /> Supported
        </Badge>
      );
    }
    if (status === 'NUMERICAL_MISMATCH') {
      return (
        <Badge variant="danger" className="gap-1">
          <AlertTriangle className="w-3 h-3" /> Number Mismatch
        </Badge>
      );
    }
    if (status === 'ENTITY_MISMATCH') {
      return (
        <Badge variant="warning" className="gap-1">
          <AlertTriangle className="w-3 h-3" /> Entity Mismatch
        </Badge>
      );
    }
    return (
      <Badge variant="danger" className="gap-1">
        <XCircle className="w-3 h-3" /> Unsupported
      </Badge>
    );
  };

  const citationMap = new Map<number, Citation>();
  for (const c of citations) {
    citationMap.set(c.citation_index, c);
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/60">
      <table className="w-full text-left text-xs border-collapse">
        <thead>
          <tr className="border-b border-slate-800 bg-slate-900/80 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
            <th className="py-2.5 px-3 w-16">ID</th>
            <th className="py-2.5 px-3">Decomposed Asserted Claim</th>
            <th className="py-2.5 px-3 w-32">Status</th>
            <th className="py-2.5 px-3 w-36">Numbers (Ext / Match)</th>
            <th className="py-2.5 px-3 w-28">Citations</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/80">
          {claims.map((claim) => (
            <tr key={claim.claim_id} className="hover:bg-slate-900/40 transition-colors">
              <td className="py-3 px-3 font-mono text-slate-400 text-[11px]">
                {claim.claim_id}
              </td>
              <td className="py-3 px-3 text-slate-200 leading-relaxed font-sans">
                {claim.text}
                {claim.notes && claim.notes.length > 0 && (
                  <div className="text-[11px] text-amber-400/90 mt-1 italic">
                    Note: {claim.notes.join(', ')}
                  </div>
                )}
              </td>
              <td className="py-3 px-3 whitespace-nowrap">
                {getStatusBadge(claim.status, claim.is_supported)}
              </td>
              <td className="py-3 px-3 font-mono text-[11px]">
                {claim.extracted_numbers.length > 0 ? (
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-300">{claim.extracted_numbers.join(', ')}</span>
                    <span className="text-slate-600">/</span>
                    <span className="text-emerald-400">{claim.matched_numbers.join(', ') || 'none'}</span>
                  </div>
                ) : (
                  <span className="text-slate-600">—</span>
                )}
              </td>
              <td className="py-3 px-3">
                <div className="flex flex-wrap gap-1">
                  {claim.citations_found.map((cIdx) => (
                    <CitationBadge
                      key={cIdx}
                      index={cIdx}
                      citation={citationMap.get(cIdx)}
                    />
                  ))}
                  {claim.citations_found.length === 0 && (
                    <span className="text-slate-600 text-[10px]">None</span>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
