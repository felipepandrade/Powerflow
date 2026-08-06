import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, Clock, Inbox } from 'lucide-react';
import { Link } from 'react-router-dom';
import { getDailyCapacity, getTasks, getTriageSignals, manageTask } from '../api/client';

const formatMinutes = (minutes: number): string => {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder === 0 ? `${hours} h` : `${hours} h ${remainder} min`;
};

export const Today = () => {
  const queryClient = useQueryClient();
  const tasksQuery = useQuery({ queryKey: ['tasks'], queryFn: getTasks });
  const triageQuery = useQuery({ queryKey: ['triage'], queryFn: getTriageSignals });
  const capacityQuery = useQuery({ queryKey: ['daily-capacity'], queryFn: getDailyCapacity });
  const completeTask = useMutation({
    mutationFn: (taskId: string) => manageTask(taskId, { status: 'done' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
  });

  const tasks = tasksQuery.data?.data ?? [];
  const triage = triageQuery.data?.data ?? [];
  const activeTasks = tasks.filter((task) => task.status === 'open' || task.status === 'in_progress');
  const recentlyDone = tasks.filter((task) => task.status === 'done').slice(0, 3);
  const capacity = capacityQuery.data;

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-8 sm:mb-12">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Foco operacional</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight text-white sm:text-5xl">Hoje</h1>
        <p className="mt-3 max-w-2xl text-lg text-muted">
          {triageQuery.isSuccess
            ? `${triage.length} ${triage.length === 1 ? 'item aguarda' : 'itens aguardam'} triagem.`
            : 'A fila de triagem ainda nao pode ser carregada.'}
        </p>
      </header>

      {tasksQuery.isError || triageQuery.isError ? (
        <p className="mb-6 rounded border border-rose-500/50 bg-rose-500/10 p-4 text-sm text-rose-200" role="alert">
          Parte dos dados operacionais esta indisponivel. Nenhum total substituto foi exibido.
        </p>
      ) : null}
      {completeTask.isError ? (
        <p className="mb-6 rounded border border-rose-500/50 bg-rose-500/10 p-4 text-sm text-rose-200" role="alert">
          A tarefa nao foi concluida. O status anterior foi preservado.
        </p>
      ) : null}

      <div className="grid gap-8 xl:grid-cols-[2fr_1fr]">
        <section aria-labelledby="triage-heading">
          <div className="mb-4 flex items-center justify-between border-b border-surface2 pb-3">
            <h2 id="triage-heading" className="font-semibold text-white">Triagem prioritaria</h2>
            <Link to="/triage" className="text-sm font-semibold text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent">
              Ver fila completa
            </Link>
          </div>

          {triageQuery.isLoading ? (
            <p className="rounded border border-surface2 p-8 text-center text-muted" role="status">Carregando triagem...</p>
          ) : triage.length === 0 ? (
            <p className="rounded border border-surface2 p-8 text-center text-muted">Nenhum item pendente de triagem.</p>
          ) : (
            <ul className="space-y-3">
              {triage.slice(0, 3).map((item) => (
                <li key={item.id} className="rounded border border-surface2 bg-surface p-5">
                  <div className="flex gap-3">
                    <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-accent" aria-hidden="true" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs uppercase tracking-wider text-muted">{item.signal_type}</p>
                      <h3 className="mt-1 font-semibold text-white">{item.payload.task_title || 'Titulo nao informado'}</h3>
                      <p className="mt-2 text-sm text-muted">{item.payload.task_description || 'Descricao nao informada'}</p>
                      <p className="mt-3 text-xs text-muted">
                        {item.decision_conf === null
                          ? 'Confianca do assessment nao informada'
                          : `Confianca do assessment: ${new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 0 }).format(item.decision_conf)}`}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="space-y-8">
          <section aria-labelledby="capacity-heading">
            <h2 id="capacity-heading" className="mb-4 font-semibold text-white">Capacidade de hoje</h2>
            <div className="rounded border border-surface2 bg-surface p-5">
              <Clock className="h-6 w-6 text-muted" aria-hidden="true" />
              {capacityQuery.isLoading ? (
                <p className="mt-3 text-sm text-muted" role="status">Carregando capacidade...</p>
              ) : capacityQuery.isError || !capacity || capacity.state === 'unknown' ? (
                <>
                  <p className="mt-3 font-semibold text-white">Desconhecida</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted">
                    O snapshot diario ainda nao foi publicado. Nenhuma capacidade foi estimada.
                  </p>
                </>
              ) : (
                <dl className="mt-3 space-y-2 text-sm">
                  <div className="flex justify-between gap-3">
                    <dt className="text-muted">Jornada configurada</dt>
                    <dd className="font-medium text-white">{capacity.available_minutes === null ? 'Desconhecida' : formatMinutes(capacity.available_minutes)}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-muted">Reunioes consideradas</dt>
                    <dd className="font-medium text-white">{capacity.meeting_minutes === null ? 'Desconhecidas' : formatMinutes(capacity.meeting_minutes)}</dd>
                  </div>
                  <div className="flex justify-between gap-3">
                    <dt className="text-muted">Eventos</dt>
                    <dd className="font-medium text-white">{capacity.meeting_count ?? 'Desconhecido'}</dd>
                  </div>
                </dl>
              )}
              <p className="mt-3 text-xs text-muted">Fonte: daily_calendar_snapshots</p>
            </div>
          </section>

          <section aria-labelledby="tasks-heading">
            <div className="mb-4 flex items-center justify-between">
              <h2 id="tasks-heading" className="font-semibold text-white">Em andamento</h2>
              <Link to="/tasks" className="text-sm text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent">Todas</Link>
            </div>
            {tasksQuery.isLoading ? (
              <p className="text-sm text-muted" role="status">Carregando tarefas...</p>
            ) : activeTasks.length === 0 ? (
              <p className="rounded border border-surface2 p-4 text-sm text-muted">Nenhuma tarefa em execucao.</p>
            ) : (
              <ul className="space-y-3">
                {activeTasks.map((task) => (
                  <li key={task.id} className="flex items-start gap-3">
                    <button
                      type="button"
                      onClick={() => completeTask.mutate(task.id)}
                      disabled={completeTask.isPending}
                      className="mt-0.5 h-6 w-6 shrink-0 rounded border border-surface2 hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50"
                      aria-label={`Marcar "${task.title}" como concluida`}
                    />
                    <span className="min-w-0 text-sm text-white">{task.title}</span>
                  </li>
                ))}
              </ul>
            )}

            {recentlyDone.length > 0 ? (
              <>
                <h3 className="mb-3 mt-7 text-xs font-semibold uppercase tracking-wider text-muted">Concluidas retornadas pela API</h3>
                <ul className="space-y-2">
                  {recentlyDone.map((task) => (
                    <li key={task.id} className="flex items-center gap-2 text-sm text-muted">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
                      <span className="line-through">{task.title}</span>
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </section>
        </aside>
      </div>

      <div className="mt-10 rounded border border-surface2 p-4 text-sm text-muted">
        <Inbox className="mr-2 inline h-4 w-4" aria-hidden="true" />
        Itens em <code>inbox</code> precisam ser abertos antes de uma transicao para <code>done</code>.
      </div>
    </div>
  );
};