import { Activity, Clock, CheckCircle2, AlertCircle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTasks, getTriageSignals, manageTask } from '../api/client';

export const Dashboard = () => {
  const queryClient = useQueryClient();

  // Queries
  const { data: tasksData, isLoading: isLoadingTasks } = useQuery({
    queryKey: ['tasks'],
    queryFn: getTasks,
  });

  const { data: triageData, isLoading: isLoadingTriage } = useQuery({
    queryKey: ['triage'],
    queryFn: getTriageSignals,
  });

  // Mutations
  const completeTaskMutation = useMutation({
    mutationFn: (taskId: string) => manageTask(taskId, { status: 'completed' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Derived state
  const tasks = tasksData?.data || [];
  const triageSignals = triageData?.data || [];
  
  const inProgressTasks = tasks.filter(t => t.status === 'inbox' || t.status === 'in_progress');
  const completedTasks = tasks.filter(t => t.status === 'completed').slice(0, 3); // Ultimas completadas
  const triageCount = triageSignals.length;

  return (
    <div className="h-full flex flex-col xl:flex-row gap-12 animate-in fade-in duration-700">
      
      {/* Coluna Principal (Maior) - Assimetria de Layout */}
      <div className="flex-[2] flex flex-col">
        <header className="mb-12">
          <h2 className="text-6xl font-bold tracking-tighter mb-4">Hoje.</h2>
          <p className="text-xl text-muted font-light max-w-lg">
            Você tem <span className="text-accent font-medium">{triageCount} decisões críticas</span> aguardando e 4 horas de foco ininterrupto disponíveis.
          </p>
        </header>

        {/* Prioridades Absolutas (Triagem) */}
        <section className="flex-1">
          <div className="flex items-center justify-between border-b border-surface2 pb-4 mb-6">
            <h3 className="text-sm font-bold uppercase tracking-widest text-muted">Ação Imediata Necessária</h3>
            <span className="text-xs text-accent">Fila de Triagem</span>
          </div>
          
          <div className="space-y-4">
            {isLoadingTriage && <div className="text-muted text-sm">Analisando sinais...</div>}
            {!isLoadingTriage && triageSignals.length === 0 && (
              <div className="text-muted text-sm border border-surface2 border-dashed p-6 text-center">
                Caixa limpa. Nenhuma prioridade emergencial detectada.
              </div>
            )}
            {triageSignals.slice(0, 3).map((item) => (
              <div key={item.id} className="group relative border border-surface2 bg-base p-6 hover:bg-surface transition-colors duration-300">
                <div className="absolute top-0 left-0 bottom-0 w-1 bg-surface2 group-hover:bg-accent transition-colors duration-300"></div>
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <AlertCircle className="w-4 h-4 text-accent" />
                      <span className="text-xs font-mono text-muted uppercase">{(item.payload as any)?.task_title || "Sinal Processado"}</span>
                    </div>
                    <h4 className="text-lg font-medium text-white mb-2 leading-tight">{(item.payload as any)?.task_description || "Decisão Pendente"}</h4>
                    <p className="text-sm text-muted">Confiança da IA: {(item.decision_conf || 0) * 100}%</p>
                  </div>
                  <button className="text-xs text-white bg-surface2 px-3 py-1 hover:bg-accent hover:text-white transition-colors duration-200">
                    Resolver →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Coluna Secundária (Menor) */}
      <div className="flex-[1] border-l border-surface2 pl-12 flex flex-col gap-12">
        {/* Capacidade */}
        <section>
          <h3 className="text-sm font-bold uppercase tracking-widest text-muted mb-6">Capacidade</h3>
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full border border-accent flex items-center justify-center text-accent">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <div className="text-3xl font-light">4h 30m</div>
                <div className="text-xs uppercase text-muted tracking-wide mt-1">Tempo Livre (Estimado)</div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full border border-surface2 flex items-center justify-center text-muted">
                <Activity className="w-5 h-5" />
              </div>
              <div>
                <div className="text-3xl font-light">85%</div>
                <div className="text-xs uppercase text-muted tracking-wide mt-1">Nível de Energia (IA)</div>
              </div>
            </div>
          </div>
        </section>

        {/* Resumo Rápido */}
        <section>
          <h3 className="text-sm font-bold uppercase tracking-widest text-muted mb-6">Em Andamento</h3>
          <ul className="space-y-4">
            {isLoadingTasks ? (
              <li className="text-sm text-muted">Carregando tarefas...</li>
            ) : (
              <>
                {completedTasks.map(t => (
                  <li key={t.id} className="flex gap-3 text-sm items-center">
                    <CheckCircle2 className="w-5 h-5 text-surface2 flex-shrink-0" />
                    <span className="text-muted line-through truncate">{t.title}</span>
                  </li>
                ))}
                {inProgressTasks.map(t => (
                  <li key={t.id} className="flex gap-3 text-sm items-center group">
                    <button 
                      onClick={() => completeTaskMutation.mutate(t.id)}
                      disabled={completeTaskMutation.isPending}
                      className="w-5 h-5 rounded-sm border border-surface2 flex-shrink-0 hover:border-accent hover:bg-accent/20 transition-colors"
                      title="Marcar como concluída"
                    />
                    <span className="text-white truncate" title={t.title}>{t.title}</span>
                  </li>
                ))}
                {inProgressTasks.length === 0 && (
                   <li className="text-sm text-muted">Nenhuma tarefa ativa.</li>
                )}
              </>
            )}
          </ul>
        </section>
      </div>

    </div>
  );
};
