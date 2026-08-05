import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTriageSignals, triageProposal } from '../api/client';
import { Check, X, AlertCircle } from 'lucide-react';

export const Triage = () => {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['triage'],
    queryFn: getTriageSignals,
  });

  const triageMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) => triageProposal(id, { action }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['triage'] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] }); // Re-fetch tasks since triage can create them
    },
  });

  const signals = data?.data || [];

  return (
    <div className="h-full animate-in fade-in duration-500">
      <h2 className="text-4xl font-bold tracking-tight mb-2">Triagem</h2>
      <p className="text-muted mb-8">Processamento de sinais entrantes (e-mails, mensagens, notas).</p>
      
      {isLoading ? (
        <div className="border border-surface2 p-12 text-center text-muted">Carregando sinais...</div>
      ) : signals.length === 0 ? (
        <div className="border border-surface2 p-12 text-center text-muted">
          Nenhum novo sinal pendente de triagem. A IA já processou tudo.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {signals.map((item) => (
            <div key={item.id} className="border border-surface2 bg-base p-6">
              <div className="flex items-center gap-3 mb-4">
                <AlertCircle className="w-5 h-5 text-accent" />
                <span className="text-sm font-mono text-muted uppercase">{(item.payload as any)?.task_title || "Decisão da IA"}</span>
              </div>
              <p className="text-white mb-6 text-lg">{(item.payload as any)?.task_description || "A IA identificou um possível compromisso."}</p>
              
              <div className="flex items-center gap-4 border-t border-surface2 pt-4">
                <button
                  onClick={() => triageMutation.mutate({ id: item.id, action: 'apply' })}
                  disabled={triageMutation.isPending}
                  className="flex items-center gap-2 text-sm bg-accent text-base px-4 py-2 hover:opacity-90 transition-opacity"
                >
                  <Check className="w-4 h-4" /> Aprovar
                </button>
                <button
                  onClick={() => triageMutation.mutate({ id: item.id, action: 'discard' })}
                  disabled={triageMutation.isPending}
                  className="flex items-center gap-2 text-sm border border-surface2 text-muted px-4 py-2 hover:bg-surface transition-colors"
                >
                  <X className="w-4 h-4" /> Descartar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
