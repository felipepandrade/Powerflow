import React from 'react';
import { ShieldCheck } from 'lucide-react';

export const EthicsBanner: React.FC = () => {
  return (
    <div className="bg-surface/80 border border-accent/30 rounded-lg p-4 mb-8 flex items-center gap-4 text-xs text-muted backdrop-blur-sm shadow-sm">
      <div className="p-2 rounded-md bg-accent/10 text-accent flex-shrink-0">
        <ShieldCheck className="w-5 h-5" />
      </div>
      <div>
        <span className="font-semibold text-white uppercase tracking-wider block mb-0.5">
          Governança Ética do Cockpit Gerencial (Seção 8 do PRD)
        </span>
        <p className="font-light leading-relaxed">
          Este painel é um instrumento de <strong>diagnóstico do sistema de trabalho</strong> para tomada de decisão estratégica e melhoria de processos. É estritamente proibido o seu uso para avaliação de desempenho individual, ranking de pessoas ou monitoramento de presença. K-Anonimato (mínimo K=3) é garantido por sistema.
        </p>
      </div>
    </div>
  );
};
