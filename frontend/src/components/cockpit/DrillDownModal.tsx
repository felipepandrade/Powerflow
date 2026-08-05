import React from 'react';
import { X, ExternalLink, Filter } from 'lucide-react';
import type { Task } from '../../api/client';

interface DrillDownModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  metricId?: string;
  tasks?: Task[];
}

export const DrillDownModal: React.FC<DrillDownModalProps> = ({
  isOpen,
  onClose,
  title,
  metricId,
  tasks = [],
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-surface border border-surface2 w-full max-w-4xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-6 border-b border-surface2 flex items-center justify-between bg-base/50">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-accent uppercase mb-1">
              <Filter className="w-3.5 h-3.5" /> Drill-Down de Evidências ({metricId || 'Total'})
            </div>
            <h3 className="text-xl font-bold text-white">{title}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-muted hover:text-white hover:bg-surface2 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          <p className="text-xs text-muted">
            Mostrando <strong>{tasks.length} itens/evidências</strong> auditáveis que compõem este indicador:
          </p>

          {tasks.length === 0 ? (
            <div className="text-center py-12 border border-surface2 border-dashed rounded-lg text-muted text-sm">
              Nenhuma tarefa diretamente vinculada a esta amostra.
            </div>
          ) : (
            <div className="space-y-3">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  className="bg-base border border-surface2 p-4 rounded-lg flex items-center justify-between hover:border-accent/40 transition-colors"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-mono uppercase bg-surface2 px-2 py-0.5 rounded text-white">
                        {task.status}
                      </span>
                      <span className="text-[10px] font-mono text-muted uppercase">
                        Prioridade: {task.priority}
                      </span>
                    </div>
                    <h4 className="text-sm font-medium text-white">{task.title}</h4>
                    {task.description && (
                      <p className="text-xs text-muted line-clamp-1 mt-1">{task.description}</p>
                    )}
                  </div>

                  <a
                    href={`/tasks?id=${task.id}`}
                    className="p-2 text-accent hover:bg-accent/10 rounded-md transition-colors text-xs flex items-center gap-1 font-mono"
                  >
                    Ver Detalhes <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-surface2 bg-base/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-surface2 text-white text-xs font-semibold rounded hover:bg-accent transition-colors"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
};
