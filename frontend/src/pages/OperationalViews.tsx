import { useQuery } from '@tanstack/react-query';
import { Clock, FolderKanban, Users } from 'lucide-react';
import { getProjects, getTasks } from '../api/client';

export const WaitingOnOthers = () => {
  const tasksQuery = useQuery({ queryKey: ['tasks'], queryFn: getTasks });
  const tasks = (tasksQuery.data?.data ?? []).filter((task) => task.status === 'waiting_on_others');

  return (
    <div className="mx-auto max-w-5xl">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Dependencias operacionais</p>
        <h1 className="mt-2 text-3xl font-bold text-white sm:text-4xl">Aguardando terceiros</h1>
        <p className="mt-2 text-muted">Pendencias conhecidas, com ultimo touchpoint quando fornecido pela API.</p>
      </header>
      {tasksQuery.isLoading ? (
        <p className="mt-7 rounded border border-surface2 p-10 text-center text-muted" role="status">Carregando dependencias...</p>
      ) : tasksQuery.isError ? (
        <p className="mt-7 rounded border border-rose-500/50 bg-rose-500/10 p-5 text-rose-200" role="alert">Dependencias indisponiveis.</p>
      ) : tasks.length === 0 ? (
        <p className="mt-7 rounded border border-surface2 p-10 text-center text-muted">Nenhuma tarefa aguardando terceiros foi retornada.</p>
      ) : (
        <ul className="mt-7 space-y-3">
          {tasks.map((task) => (
            <li key={task.id} className="rounded border border-surface2 bg-surface p-5">
              <div className="flex items-start gap-3">
                <Users className="mt-0.5 h-5 w-5 shrink-0 text-accent" aria-hidden="true" />
                <div>
                  <h2 className="font-semibold text-white">{task.title}</h2>
                  <p className="mt-2 text-sm text-muted">Responsavel externo: {task.waiting_on_id || 'nao informado'}</p>
                  <p className="mt-1 flex items-center gap-1 text-xs text-muted">
                    <Clock className="h-4 w-4" aria-hidden="true" />
                    Ultima atividade: {task.last_activity_at || 'desconhecida'}
                  </p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export const ProjectsView = () => {
  const projectsQuery = useQuery({ queryKey: ['projects'], queryFn: getProjects });
  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Portfolio operacional</p>
        <h1 className="mt-2 text-3xl font-bold text-white sm:text-4xl">Projetos</h1>
        <p className="mt-2 text-muted">Estado cadastral e descricao. Saude so aparece no cockpit com envelope analitico.</p>
      </header>
      {projectsQuery.isLoading ? (
        <p className="mt-7 rounded border border-surface2 p-10 text-center text-muted" role="status">Carregando projetos...</p>
      ) : projectsQuery.isError ? (
        <p className="mt-7 rounded border border-rose-500/50 bg-rose-500/10 p-5 text-rose-200" role="alert">Projetos indisponiveis.</p>
      ) : projectsQuery.data?.length === 0 ? (
        <p className="mt-7 rounded border border-surface2 p-10 text-center text-muted">Nenhum projeto cadastrado.</p>
      ) : (
        <ul className="mt-7 grid gap-4 sm:grid-cols-2">
          {projectsQuery.data?.map((project) => (
            <li key={project.id} className="rounded border border-surface2 bg-surface p-5">
              <FolderKanban className="h-6 w-6 text-accent" aria-hidden="true" />
              <p className="mt-3 text-xs uppercase tracking-wider text-muted">{project.status}</p>
              <h2 className="mt-1 font-semibold text-white">{project.name}</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted">{project.description || 'Descricao nao informada'}</p>
              <p className="mt-4 text-xs text-muted">Saude: desconhecida nesta visao operacional</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
