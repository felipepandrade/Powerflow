import React from 'react';
import { Sparkles, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';

interface NarrativeCardProps {
  text: string;
  isVerified: boolean;
  discrepancies?: number[];
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const NarrativeCard: React.FC<NarrativeCardProps> = ({
  text,
  isVerified,
  discrepancies = [],
  onRefresh,
  isLoading = false,
}) => {
  return (
    <div className="bg-surface/40 border border-surface2 rounded-lg p-6 relative overflow-hidden backdrop-blur-sm shadow-md mb-8">
      <div className="flex items-center justify-between mb-4 border-b border-surface2 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-accent animate-pulse" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-white">
            Síntese Executiva Gerencial (LLM Insight)
          </h3>
        </div>

        <div className="flex items-center gap-3">
          {isVerified ? (
            <span className="flex items-center gap-1.5 text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded-full font-mono">
              <CheckCircle2 className="w-3.5 h-3.5" /> Verificado Numericamente (0 Alucinações)
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs bg-amber-500/10 text-amber-400 border border-amber-500/30 px-3 py-1 rounded-full font-mono">
              <AlertTriangle className="w-3.5 h-3.5" /> Discrepância Numérica Detectada ({discrepancies.length})
            </span>
          )}

          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="p-1.5 text-muted hover:text-white hover:bg-surface2 rounded-md transition-colors"
              title="Gerar Nova Síntese"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      <p className="text-sm text-text/90 font-light leading-relaxed whitespace-pre-line">
        {text}
      </p>

      {discrepancies.length > 0 && (
        <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded text-xs text-amber-300">
          <strong>Aviso do Guardrail Numérico (RF-I.8):</strong> Os numerais {discrepancies.join(', ')} foram sinalizados para revisão manual pois não constam no conjunto de evidências calculadas.
        </div>
      )}
    </div>
  );
};
