import React from 'react';
import { QualityGateDecision, QualityGateReport } from '../../types';
import { Badge } from '../ui/Badge';
import { formatScore } from '../../utils/formatters';
import { ShieldCheck, ShieldAlert, ShieldX, HelpCircle } from 'lucide-react';

export interface QualityGateBadgeProps {
  decision: QualityGateDecision;
  report?: QualityGateReport;
  traceabilityScore?: number;
  className?: string;
}

export const QualityGateBadge: React.FC<QualityGateBadgeProps> = ({
  decision,
  report,
  traceabilityScore,
  className,
}) => {
  const getDecisionBadge = () => {
    switch (decision) {
      case 'accept':
        return (
          <Badge variant="success" className="gap-1.5 py-1 px-2.5 text-xs font-semibold">
            <ShieldCheck className="w-4 h-4" /> Quality Gate: Accepted
          </Badge>
        );
      case 'unable_to_verify':
        return (
          <Badge variant="danger" className="gap-1.5 py-1 px-2.5 text-xs font-semibold">
            <ShieldAlert className="w-4 h-4" /> Unverified / Safe Refusal
          </Badge>
        );
      case 'empty_workspace':
        return (
          <Badge variant="warning" className="gap-1.5 py-1 px-2.5 text-xs font-semibold">
            <ShieldX className="w-4 h-4" /> Empty Workspace
          </Badge>
        );
      case 'retry':
        return (
          <Badge variant="warning" className="gap-1.5 py-1 px-2.5 text-xs font-semibold">
            <HelpCircle className="w-4 h-4" /> Auto-Correction Retry
          </Badge>
        );
      default:
        return (
          <Badge variant="default" className="gap-1.5 py-1 px-2.5 text-xs font-semibold">
            Quality Gate: {decision}
          </Badge>
        );
    }
  };

  return (
    <div className={`flex flex-wrap items-center gap-3 ${className || ''}`}>
      {getDecisionBadge()}

      {report && (
        <div className="flex items-center gap-3 text-xs text-slate-400 bg-slate-900/90 px-3 py-1 rounded-md border border-slate-800">
          <div>
            <span className="text-slate-500">Faithfulness: </span>
            <span
              className={`font-semibold font-mono ${
                report.faithfulness >= 0.8 ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {formatScore(report.faithfulness)}
            </span>
          </div>

          <span className="text-slate-700">|</span>

          <div>
            <span className="text-slate-500">Numerical Errors: </span>
            <span
              className={`font-semibold font-mono ${
                report.numerical_mismatches === 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {report.numerical_mismatches}
            </span>
          </div>

          <span className="text-slate-700">|</span>

          <div>
            <span className="text-slate-500">Claims: </span>
            <span className="font-mono text-slate-200">
              {report.supported_claims_count}/{report.total_claims_count}
            </span>
          </div>

          {report.overall_score !== undefined && (
            <>
              <span className="text-slate-700">|</span>
              <div>
                <span className="text-slate-500">Overall: </span>
                <span className="font-semibold font-mono text-sky-400">
                  {formatScore(report.overall_score)}
                </span>
              </div>
            </>
          )}
        </div>
      )}

      {!report && traceabilityScore !== undefined && (
        <div className="text-xs text-slate-400 bg-slate-900 px-2.5 py-1 rounded border border-slate-800">
          <span className="text-slate-500">Traceability: </span>
          <span className="font-semibold font-mono text-emerald-400">
            {formatScore(traceabilityScore)}
          </span>
        </div>
      )}
    </div>
  );
};
