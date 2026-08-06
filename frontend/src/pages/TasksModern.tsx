import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, Clock, FileClock, Search, X } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { getTasks, getTaskTimeline } from '../api/client';
import type { TaskStatus } from '../api/client';

const statusLabels: Record<TaskStatus, string> = {
  inbox: 'Caixa de entrada',
  open: 'Aberta',
  in_progress: 'Em andamento',
  waiting_on_others: 'Aguardando terceiros',
  blocked: 'Bloqueada',
  done: 'Concluida',
  cancelled: 'Cancelada',
};

const formatDate = (value: string): string => {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
};

export const TasksModern = () => {
  const [params, setParams] = useSearchParams();
  const selectedId = params.get('id') || '';
  const status = params.get('status') || '';
  const query = params.get('q') || '';

  const tasksQuery = useQuery({ queryKey: ['tasks'], queryFn: getTasks });
  const timelineQuery = useQuery({
    queryKey: ['task-timeline', selectedId],
    queryFn: () => getTaskTimeline(selectedId),
    enabled: Boolean(selectedId),
    retry: false,
  });

  const updateParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const normalizedQuery = query.trim().toLocaleLowerCase('pt-BR');
  const tasks = (tasksQuery.data?.data ?? []).filter((task) => {
    if (status && task.status !== status) return false;
    if (!normalizedQuery) return true;
    return task.title.toLocaleLowerCase('pt-BR').includes(normalizedQuery)
      || task.description?.toLocaleLowerCase('pt-BR').includes(normalizedQuery);
  });

  return (
    <div className="mx-auto max-w-7xl">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Responsabilidades</p>
        <h1 className="mt-2 text-3xl font-bold text-white sm:text-4xl">Tarefas</h1>
        <p className="mt-2 text-muted">Estados e prazos retornados pela API, com timeline auditavel por tarefa.</p>
      </header>

      <form className="mt-7 grid gap-4 rounded border border-surface2 bg-surface p-4 sm:grid-cols-[1fr_15rem]" aria-label="Filtrar tarefas">
        <div>
          <label htmlFor="task-search" className="text-xs font-semibold uppercase tracking-wider text-muted">Buscar</label>
          <div className="relative mt-2">
            <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted" aria-hidden="true" />
            <input
              id="task-search"
              type="search"
              value={query}
              onChange={(event) => updateParam('q', event.target.value)}
              placeholder="Titulo ou descricao"
              className="input-field min-h-11 rounded pl-10"
            />
          </div>
        </div>
        <div>
          <label htmlFor="task-status" className="text-xs font-semibold uppercase tracking-wider text-muted">Status</label>
          <select id="task-status" value={status} onChange={(event) => updateParam('status', event.target.value)} className="input-field mt-2 min-h-11 rounded">
            <option value="">Todos os retornados</option>
            {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
      </form>

      <div className="mt-7 grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <section aria-labelledby="task-list-title">
          <div className="mb-3 flex items-center justify-between">
            <h2 id="task-list-title" className="font-semibold text-white">Resultado</h2>
            <span className="text-sm text-muted">
              {tasksQuery.isSuccess ? `${tasks.length} de ${tasksQuery.data.count}` : 'Contagem desconhecida'}
            </span>
          </div>

          {tasksQuery.isLoading ? (
            <p className="rounded border border-surface2 p-10 text-center text-muted" role="status">Carregando tarefas...</p>
          ) : tasksQuery.isError ? (
            <p className="rounded border border-rose-500/50 bg-rose-500/10 p-5 text-rose-200" role="alert">Tarefas indisponiveis.</p>
          ) : tasks.length === 0 ? (
            <p className="rounded border border-surface2 p-10 text-center text-muted">Nenhuma tarefa corresponde aos filtros.</p>
          ) : (
            <ul className="space-y-3">
              {tasks.map((task) => (
                <li key={task.id}>
                  <button
                    type="button"
                    onClick={() => updateParam('id', task.id)}
                    aria-pressed={selectedId === task.id}
                    className="flex min-h-20 w-full flex-col justify-between gap-3 rounded border border-surface2 bg-surface p-4 text-left hover:border-accent/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent sm:flex-row sm:items-center"
                  >
                    <div className="min-w-0">
                      <p className="text-xs uppercase tracking-wider text-muted">{statusLabels[task.status]}</p>
                      <p className={`mt-1 font-semibold ${task.status === 'done' ? 'text-muted line-through' : 'text-white'}`}>{task.title}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-4 text-xs text-muted">
                      <span>Prioridade {task.priority}</span>
                      {task.due_date ? <span className="flex items-center gap-1"><Clock className="h-4 w-4" aria-hidden="true" />{task.due_date}</span> : <span>Sem prazo</span>}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="rounded border border-surface2 bg-surface p-5 xl:sticky xl:top-6 xl:max-h-[calc(100vh-3rem)] xl:overflow-y-auto" aria-labelledby="timeline-title">
          {!selectedId ? (
            <div className="py-10 text-center text-muted">
              <FileClock className="mx-auto h-8 w-8" aria-hidden="true" />
              <h2 id="timeline-title" className="mt-3 font-semibold text-white">Timeline da tarefa</h2>
              <p className="mt-2 text-sm">Selecione uma tarefa para ver o historico retornado pela API.</p>
            </div>
          ) : (
            <>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-accent">Auditoria operacional</p>
                  <h2 id="timeline-title" className="mt-1 font-semibold text-white">{timelineQuery.data?.title || 'Timeline da tarefa'}</h2>
                </div>
                <button type="button" onClick={() => updateParam('id', '')} className="rounded p-2 text-muted hover:bg-surface2 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent" aria-label="Fechar timeline">
                  <X className="h-5 w-5" aria-hidden="true" />
                </button>
              </div>

              {timelineQuery.isLoading ? (
                <p className="mt-5 text-sm text-muted" role="status">Carregando timeline...</p>
              ) : timelineQuery.isError ? (
                <p className="mt-5 rounded border border-rose-500/50 bg-rose-500/10 p-3 text-sm text-rose-200" role="alert">Timeline indisponivel para esta tarefa.</p>
              ) : timelineQuery.data?.timeline.length === 0 ? (
                <p className="mt-5 text-sm text-muted">Nenhum evento auditavel retornado.</p>
              ) : (
                <ol className="mt-5 space-y-5 border-l border-surface2 pl-5">
                  {timelineQuery.data?.timeline.map((item) => (
                    <li key={item.id} className="relative">
                      <span className="absolute -left-[1.45rem] top-1 h-2 w-2 rounded-full bg-accent" aria-hidden="true" />
                      <p className="text-xs text-muted">{formatDate(item.timestamp)}</p>
                      {item.type === 'status_change' ? (
                        <p className="mt-1 text-sm text-white">
                          {item.from_status ? statusLabels[item.from_status] : 'Sem estado anterior'} / {item.to_status ? statusLabels[item.to_status] : 'Estado nao informado'}
                          {item.actor ? <span className="block text-xs text-muted">Ator: {item.actor}</span> : null}
                        </p>
                      ) : (
                        <p className="mt-1 text-sm text-white">{item.content || 'Atualizacao sem conteudo retornado'}</p>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </>
          )}
        </aside>
      </div>

      <p className="mt-8 flex items-center gap-2 text-xs text-muted">
        <CheckCircle2 className="h-4 w-4 text-accent" aria-hidden="true" />
        O status terminal correto do dominio e <code>done</code>.
      </p>
    </div>
  );
};
