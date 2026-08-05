import { useQuery } from '@tanstack/react-query';
import { getTasks } from '../api/client';
import { CheckCircle2, Clock } from 'lucide-react';

export const Tasks = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: getTasks,
  });

  const tasks = data?.data || [];

  return (
    <div className="h-full animate-in fade-in duration-500">
      <h2 className="text-4xl font-bold tracking-tight mb-2">Tarefas</h2>
      <p className="text-muted mb-8">Gestão detalhada e estruturada de suas responsabilidades.</p>
      
      {isLoading ? (
        <div className="border border-surface2 p-12 text-center text-muted">Carregando tarefas...</div>
      ) : tasks.length === 0 ? (
        <div className="border border-surface2 p-12 text-center text-muted">
          Nenhuma tarefa encontrada.
        </div>
      ) : (
        <div className="flex flex-col gap-4 border-t border-surface2 pt-6">
          {tasks.map(task => (
            <div key={task.id} className="flex items-center justify-between group py-3 px-4 hover:bg-surface border border-transparent hover:border-surface2 transition-all">
              <div className="flex items-center gap-4">
                <CheckCircle2 className={`w-5 h-5 ${task.status === 'completed' ? 'text-accent' : 'text-surface2'}`} />
                <span className={`text-lg ${task.status === 'completed' ? 'text-muted line-through' : 'text-white'}`}>
                  {task.title}
                </span>
              </div>
              <div className="flex items-center gap-6">
                <span className="text-xs uppercase font-mono tracking-widest text-muted">{task.status}</span>
                {task.due_date && (
                   <span className="flex items-center gap-2 text-sm text-muted">
                     <Clock className="w-4 h-4" /> {task.due_date}
                   </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
