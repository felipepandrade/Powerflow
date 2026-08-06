import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Check, Quote, X } from 'lucide-react';
import { getTriageSignals, triageProposal } from '../api/client';

export const TriageModern = () => {
  const queryClient = useQueryClient();
  const triageQuery = useQuery({ queryKey: ['triage'], queryFn: getTriageSignals });
  const triageMutation = useMutation({
    mutationFn: ({ id, action, taskId }: { id: string; action: 'apply' | 'discard'; taskId?: string }) =>
      triageProposal(id, { action, task_id: taskId }),
    onSuccess: () => Promise.all([
      queryClient.invalidateQueries({ queryKey: ['triage'] }),
      queryClient.invalidateQueries({ queryKey: ['tasks'] }),
    ]),
  });

  const signals = triageQuery.data?.data ?? [];

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Human in the loop</p>
        <h1 className="mt-2 text-3xl font-bold text-white sm:text-4xl">Triagem</h1>
        <p className="mt-2 max-w-3xl text-muted">
          Revise hipotese, evidencia literal e possivel tarefa correlata antes de aplicar uma proposta.
        </p>
      </header>

      <div aria-live="polite" className="mt-5 min-h-6 text-sm">
        {triageMutation.isSuccess ? <p className="text-accent">Decisao registrada; fila e tarefas foram atualizadas.</p> : null}
        {triageMutation.isError ? <p className="text-rose-300" role="alert">A decisao nao foi aplicada. O item permanece na fila.</p> : null}
      </div>

      {triageQuery.isLoading ? (
        <p className="mt-6 rounded border border-surface2 p-12 text-center text-muted" role="status">Carregando sinais...</p>
      ) : triageQuery.isError ? (
        <p className="mt-6 rounded border border-rose-500/50 bg-rose-500/10 p-5 text-rose-200" role="alert">Fila de triagem indisponivel.</p>
      ) : signals.length === 0 ? (
        <p className="mt-6 rounded border border-surface2 p-12 text-center text-muted">Nenhum sinal pendente de triagem.</p>
      ) : (
        <ul className="mt-6 space-y-5">
          {signals.map((item) => (
            <li key={item.id} className="rounded border border-surface2 bg-surface p-5 sm:p-6">
              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                <div>
                  <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-accent">
                    <AlertCircle className="h-4 w-4" aria-hidden="true" />
                    {item.signal_type}
                  </p>
                  <h2 className="mt-2 text-lg font-semibold text-white">{item.payload.task_title || 'Titulo nao retornado'}</h2>
                </div>
                <p className="text-xs text-muted">
                  {item.decision_conf === null
                    ? 'Confianca desconhecida'
                    : `Assessment: ${new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 0 }).format(item.decision_conf)}`}
                </p>
              </div>

              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <section className="rounded border border-surface2 bg-base p-4" aria-label="Proposta extraida">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Proposta extraida</h3>
                  <p className="mt-2 text-sm leading-relaxed text-white">{item.payload.task_description || 'Descricao nao retornada'}</p>
                </section>
                <section className="rounded border border-surface2 bg-base p-4" aria-label="Candidato de correlacao">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Candidato de correlacao</h3>
                  <p className="mt-2 text-sm text-white">{item.payload.candidate_task_title || 'Nenhum candidato retornado'}</p>
                  {item.payload.candidate_task_id ? <p className="mt-1 break-all text-xs text-muted">ID: {item.payload.candidate_task_id}</p> : null}
                </section>
              </div>

              <section className="mt-4 rounded border border-accent/30 bg-accent/5 p-4" aria-label="Evidencia literal">
                <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted">
                  <Quote className="h-4 w-4" aria-hidden="true" /> Evidencia literal
                </h3>
                {item.payload.evidence_quote ? (
                  <blockquote className="mt-2 border-l-2 border-accent pl-3 text-sm text-white">"{item.payload.evidence_quote}"</blockquote>
                ) : (
                  <p className="mt-2 text-sm text-amber-200">A API nao retornou evidencia literal; revise antes de aplicar.</p>
                )}
                {item.payload.source_subject ? <p className="mt-2 text-xs text-muted">Fonte: {item.payload.source_subject}</p> : null}
              </section>

              <div className="mt-5 flex flex-col gap-3 border-t border-surface2 pt-5 sm:flex-row">
                <button
                  type="button"
                  onClick={() => triageMutation.mutate({
                    id: item.id,
                    action: 'apply',
                    taskId: item.payload.candidate_task_id,
                  })}
                  disabled={triageMutation.isPending || !item.payload.evidence_quote}
                  className="btn-primary min-h-11 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Check className="h-4 w-4" aria-hidden="true" /> Aplicar proposta
                </button>
                <button
                  type="button"
                  onClick={() => triageMutation.mutate({ id: item.id, action: 'discard' })}
                  disabled={triageMutation.isPending}
                  className="btn-secondary min-h-11 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50"
                >
                  <X className="h-4 w-4" aria-hidden="true" /> Marcar irrelevante
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
