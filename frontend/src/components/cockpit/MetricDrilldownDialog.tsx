import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileSearch, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { getMetricDrilldown } from '../../api/client';
import type {
  CapacityDrilldownItem,
  MetricDrilldownItem,
  MetricDrilldownResponse,
  MetricQuery,
  MetricValue,
  ProjectDrilldownItem,
  TaskDrilldownItem,
} from '../../api/client';

interface MetricDrilldownDialogProps {
  metric: MetricValue | null;
  filters: Pick<MetricQuery, 'start_date' | 'end_date' | 'project_id' | 'area_id' | 'priority'>;
  onClose: () => void;
}


const isTaskItem = (item: MetricDrilldownItem): item is TaskDrilldownItem => 'task_id' in item;
const isCapacityItem = (item: MetricDrilldownItem): item is CapacityDrilldownItem => 'starts_at' in item;
const isProjectItem = (item: MetricDrilldownItem): item is ProjectDrilldownItem => 'project_id' in item;

const ProvenanceItems = ({ response }: { response: MetricDrilldownResponse }) => (
  <div className="mt-4 space-y-4">
    {!response.reconciliation.reconciles ? (
      <p className="rounded border border-rose-500/50 bg-rose-500/10 p-4 text-sm text-rose-200" role="alert">
        O backend informou que o drill-down nao reconcilia com o valor exibido. Nao use este indicador em reporte.
      </p>
    ) : null}

    {response.items.length === 0 ? (
      <p className="rounded border border-amber-500/50 bg-amber-500/10 p-4 text-sm text-amber-200" role="status">
        O backend retornou zero itens de proveniencia para este valor.
      </p>
    ) : (
      <ul className="space-y-4">
        {response.items.map((item) => {
          if (isTaskItem(item)) {
            return (
              <li key={item.task_id} className="rounded border border-surface2 bg-surface p-4">
                <div className="flex flex-col justify-between gap-2 sm:flex-row">
                  <h4 className="font-semibold text-white">{item.title || 'Titulo nao retornado'}</h4>
                  <Link to={`/tasks?id=${item.task_id}`} className="text-sm font-semibold text-accent hover:underline">
                    Abrir timeline
                  </Link>
                </div>
                {item.evidence.length === 0 ? (
                  <p className="mt-3 text-sm text-amber-200">Tarefa sem evidencia literal retornada.</p>
                ) : (
                  <ul className="mt-3 space-y-3">
                    {item.evidence.map((evidence) => (
                      <li key={evidence.evidence_id} className="border-l-2 border-accent pl-3">
                        <blockquote className="text-sm text-white">&ldquo;{evidence.quote}&rdquo;</blockquote>
                        <p className="mt-1 text-xs text-muted">
                          Papel {evidence.role} / source item {evidence.source_item_id}
                        </p>
                        <p className="mt-1 text-xs text-muted">Deep link da fonte nao retornado pela API.</p>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          }
          if (isCapacityItem(item)) {
            return (
              <li key={item.source_item_id} className="rounded border border-surface2 bg-surface p-4">
                <h4 className="font-semibold text-white">Evento de calendario normalizado</h4>
                <p className="mt-2 text-sm text-muted">{item.starts_at} ate {item.ends_at}</p>
                <p className="mt-1 text-xs text-muted">Duracao retornada: {item.duration_minutes} minutos / source item {item.source_item_id}</p>
              </li>
            );
          }
          if (isProjectItem(item)) {
            return (
              <li key={item.project_id} className="rounded border border-surface2 bg-surface p-4">
                <h4 className="font-semibold text-white">Projeto {item.project_id}</h4>
                <p className="mt-2 text-sm text-muted">Valor publicado: {item.value ?? 'desconhecido'}</p>
                <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                  {Object.entries(item.components ?? {}).map(([name, value]) => (
                    <div key={name}><dt className="text-xs text-muted">{name}</dt><dd className="text-sm text-white">{value ?? 'desconhecido'}</dd></div>
                  ))}
                </dl>
              </li>
            );
          }
          return null;
        })}
      </ul>
    )}
  </div>
);

export const MetricDrilldownDialog = ({ metric, filters, onClose }: MetricDrilldownDialogProps) => {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  const drilldown = useQuery({
    queryKey: ['metric-drilldown', metric?.metric_id, metric?.period_start, metric?.period_end, filters],
    queryFn: () =>
      getMetricDrilldown(metric!.metric_id, {
        ...filters,
        start_date: metric!.period_start,
        end_date: metric!.period_end,
      }),
    enabled: Boolean(metric),
    retry: false,
  });

  useEffect(() => {
    if (!metric) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !dialogRef.current) return;

      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
      previousFocus?.focus();
    };
  }, [metric, onClose]);

  if (!metric) return null;

  const coveragePct = metric.coverage?.pct;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-3 sm:p-6"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="metric-dialog-title"
        aria-describedby="metric-dialog-description"
        className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-lg border border-surface2 bg-base shadow-2xl"
      >
        <header className="flex items-start justify-between gap-4 border-b border-surface2 p-4 sm:p-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-accent">
              Explicacao e proveniencia
            </p>
            <h2 id="metric-dialog-title" className="mt-1 text-xl font-bold text-white">
              {metric.name || metric.metric_id}
            </h2>
            <p id="metric-dialog-description" className="mt-1 text-sm text-muted">
              Periodo publicado: {metric.period_start} a {metric.period_end}
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="rounded p-2 text-muted hover:bg-surface2 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
            aria-label="Fechar detalhamento"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </header>

        <div className="overflow-y-auto p-4 sm:p-6">
          <section aria-labelledby="calculation-title" className="rounded border border-surface2 bg-surface p-4">
            <h3 id="calculation-title" className="font-semibold text-white">Como este valor foi produzido</h3>
            <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-muted">Formula</dt>
                <dd className="mt-1 break-words text-white">{metric.formula || 'Nao fornecida pelo backend'}</dd>
              </div>
              <div>
                <dt className="text-muted">Numerador</dt>
                <dd className="mt-1 text-white">{metric.numerator ?? 'Nao aplicavel/informado'}</dd>
              </div>
              <div>
                <dt className="text-muted">Denominador</dt>
                <dd className="mt-1 text-white">{metric.denominator ?? 'Nao aplicavel/informado'}</dd>
              </div>
              <div>
                <dt className="text-muted">Cobertura</dt>
                <dd className="mt-1 text-white">
                  {metric.coverage?.level || 'desconhecida'}
                  {coveragePct !== null && coveragePct !== undefined
                    ? ` / ${new Intl.NumberFormat('pt-BR', { style: 'percent' }).format(coveragePct)}`
                    : ''}
                </dd>
              </div>
              <div>
                <dt className="text-muted">Amostra</dt>
                <dd className="mt-1 text-white">{metric.sample_size}</dd>
              </div>
              <div>
                <dt className="text-muted">Origem</dt>
                <dd className="mt-1 text-white">{metric.data_origin || 'nao informada'}</dd>
              </div>
              <div>
                <dt className="text-muted">Fonte do calculo</dt>
                <dd className="mt-1 break-words text-white">{metric.provenance?.source || 'nao informada'}</dd>
              </div>
              <div>
                <dt className="text-muted">Versao</dt>
                <dd className="mt-1 text-white">{metric.metric_version ?? 'nao informada'}</dd>
              </div>
            </dl>
          </section>

          <section aria-labelledby="evidence-title" className="mt-6">
            <div className="flex items-center gap-2">
              <FileSearch className="h-5 w-5 text-accent" aria-hidden="true" />
              <h3 id="evidence-title" className="font-semibold text-white">Tarefas e evidencias literais</h3>
            </div>

            {drilldown.isLoading ? (
              <p className="mt-4 rounded border border-surface2 p-6 text-center text-muted" role="status">
                Carregando proveniencia...
              </p>
            ) : drilldown.isError ? (
              <div className="mt-4 rounded border border-rose-500/50 bg-rose-500/10 p-4 text-sm text-rose-200" role="alert">
                A API nao disponibilizou o drill-down deste indicador. O valor nao deve ser usado em reporte ate que sua proveniencia possa ser auditada.
              </div>
            ) : drilldown.data ? (
              <ProvenanceItems response={drilldown.data} />
            ) : null}
          </section>
        </div>
      </div>
    </div>
  );
};
