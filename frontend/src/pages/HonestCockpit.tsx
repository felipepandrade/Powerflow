import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, BarChart3, CalendarClock, Clock, Layers, Play, Sparkles } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import {
  buildSnapshots,
  computeMetrics,
  generateInsight,
  getMetrics,
  getProjects,
} from '../api/client';
import type { MetricQuery, MetricValue } from '../api/client';
import { MetricCard } from '../components/cockpit/MetricCard';
import { MetricDrilldownDialog } from '../components/cockpit/MetricDrilldownDialog';

type View = 'overview' | 'flow' | 'capacity' | 'portfolio';

const views: Array<{ id: View; label: string }> = [
  { id: 'overview', label: 'Visao executiva' },
  { id: 'flow', label: 'Demanda e fluxo' },
  { id: 'capacity', label: 'Agenda e capacidade' },
  { id: 'portfolio', label: 'Portfolio e marcos' },
];

const metricDefinitions = {
  overview: [
    ['flow.net_flow', 'Fluxo liquido', 'Estou entregando mais trabalho do que entra?', BarChart3],
    ['flow.wip', 'Trabalho em progresso', 'Quantas demandas permanecem ativas no periodo?', Activity],
    ['flow.aging_wip_p85', 'Idade do WIP (p85)', 'Onde o trabalho aberto esta envelhecendo?', Clock],
    ['capacity.meeting_ratio', 'Tempo em reunioes', 'Quanto da jornada configurada foi ocupado por reunioes?', CalendarClock],
    ['project.health_score', 'Saude do portfolio', 'Quais projetos exigem intervencao?', Layers],
  ],
  flow: [
    ['flow.throughput', 'Throughput', 'Quantas tarefas foram concluidas no periodo?', BarChart3],
    ['flow.net_flow', 'Fluxo liquido', 'O saldo entre entradas e saidas esta sustentavel?', Activity],
    ['flow.wip', 'Trabalho em progresso', 'Qual e o estoque de trabalho ativo?', Layers],
    ['flow.aging_wip_p85', 'Idade do WIP (p85)', 'Quanto envelhecem as demandas abertas?', Clock],
    ['flow.lead_time_p50', 'Lead time (p50)', 'Qual e o tempo mediano de conclusao?', Clock],
    ['flow.lead_time_p85', 'Lead time (p85)', 'Em quanto tempo 85% das demandas sao concluidas?', Clock],
  ],
  capacity: [
    ['capacity.meeting_hours', 'Horas em reuniao', 'Quanto tempo util foi comprometido por reunioes?', CalendarClock],
    ['capacity.meeting_ratio', 'Percentual em reunioes', 'Qual parcela da jornada configurada foi ocupada?', Activity],
    ['capacity.context_switches', 'Trocas de contexto', 'Quao fragmentada esta a agenda conhecida?', Layers],
  ],
  portfolio: [
    ['project.health_score', 'Saude dos projetos', 'Qual e a saude calculada da carteira e sua decomposicao?', Activity],
  ],
} satisfies Record<View, Array<readonly [string, string, string, typeof Activity]>>;

const isView = (value: string | null): value is View =>
  value === 'overview' || value === 'flow' || value === 'capacity' || value === 'portfolio';

export const HonestCockpit = () => {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedMetric, setSelectedMetric] = useState<MetricValue | null>(null);
  const requestedView = searchParams.get('view');
  const view: View = isView(requestedView) ? requestedView : 'overview';
  const startDate = searchParams.get('start_date') || '';
  const endDate = searchParams.get('end_date') || '';
  const projectId = searchParams.get('project_id') || '';

  const filters: MetricQuery = useMemo(
    () => ({
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      project_id: projectId || undefined,
    }),
    [endDate, projectId, startDate],
  );

  const metricsQuery = useQuery({
    queryKey: ['metrics', filters],
    queryFn: () => getMetrics(filters),
  });
  const projectsQuery = useQuery({ queryKey: ['projects'], queryFn: getProjects });

  const computeMutation = useMutation({
    mutationFn: async () => {
      await buildSnapshots(endDate || undefined);
      return computeMetrics(startDate || undefined, endDate || undefined);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['metrics'] }),
  });
  const insightMutation = useMutation({ mutationFn: () => generateInsight('cockpit') });

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next, { replace: true });
  };

  const metricById = (metricId: string): MetricValue | undefined =>
    metricsQuery.data?.find((metric) => metric.metric_id === metricId);

  const invalidPeriod = Boolean(startDate && endDate && startDate > endDate);
  const currentDefinitions = metricDefinitions[view];

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-16">
      <header className="flex flex-col justify-between gap-4 border-b border-surface2 pb-6 lg:flex-row lg:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Diagnostico gerencial</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-white sm:text-4xl">Cockpit Powerflow</h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted">
            Visao do fluxo de trabalho que passa por esta gerencia. Nao constitui avaliacao de desempenho individual.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            onClick={() => computeMutation.mutate()}
            disabled={invalidPeriod || computeMutation.isPending}
            className="btn-secondary min-h-11 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-50"
          >
            <Play className="h-4 w-4" aria-hidden="true" />
            {computeMutation.isPending ? 'Recalculando...' : 'Recalcular periodo'}
          </button>
          <button
            type="button"
            onClick={() => insightMutation.mutate()}
            disabled={insightMutation.isPending}
            className="btn-primary min-h-11 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            {insightMutation.isPending ? 'Validando sintese...' : 'Gerar sintese'}
          </button>
        </div>
      </header>

      <aside className="rounded border border-accent/40 bg-accent/10 p-4 text-sm text-muted" aria-label="Limitacoes dos dados">
        <strong className="text-white">Escopo e cobertura:</strong> trabalho fora dos canais monitorados pode nao aparecer.
        Cada valor so e publicado abaixo quando a API fornece cobertura, amostra, periodo e caveat.
      </aside>

      <form className="grid gap-4 rounded border border-surface2 bg-surface p-4 sm:grid-cols-2 lg:grid-cols-4" aria-label="Filtros do cockpit">
        <div>
          <label htmlFor="period-start" className="text-xs font-semibold uppercase tracking-wider text-muted">Inicio</label>
          <input
            id="period-start"
            type="date"
            value={startDate}
            onChange={(event) => updateFilter('start_date', event.target.value)}
            className="input-field mt-2 min-h-11 rounded"
          />
        </div>
        <div>
          <label htmlFor="period-end" className="text-xs font-semibold uppercase tracking-wider text-muted">Fim</label>
          <input
            id="period-end"
            type="date"
            value={endDate}
            min={startDate || undefined}
            onChange={(event) => updateFilter('end_date', event.target.value)}
            className="input-field mt-2 min-h-11 rounded"
            aria-invalid={invalidPeriod}
            aria-describedby={invalidPeriod ? 'period-error' : undefined}
          />
          {invalidPeriod ? <p id="period-error" className="mt-1 text-xs text-rose-300">O fim deve ser posterior ao inicio.</p> : null}
        </div>
        <div>
          <label htmlFor="project-filter" className="text-xs font-semibold uppercase tracking-wider text-muted">Projeto</label>
          <select
            id="project-filter"
            value={projectId}
            onChange={(event) => updateFilter('project_id', event.target.value)}
            className="input-field mt-2 min-h-11 rounded"
          >
            <option value="">Todos os projetos</option>
            {projectsQuery.data?.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
          </select>
        </div>
        <div className="flex items-end">
          <button
            type="button"
            onClick={() => {
              const next = new URLSearchParams();
              next.set('view', view);
              setSearchParams(next, { replace: true });
            }}
            className="btn-secondary min-h-11 w-full rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
          >
            Limpar filtros
          </button>
        </div>
      </form>

      <nav className="overflow-x-auto border-b border-surface2" aria-label="Perspectivas do cockpit">
        <div className="flex min-w-max gap-1" role="tablist">
          {views.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={view === item.id}
              onClick={() => updateFilter('view', item.id)}
              className={`min-h-11 border-b-2 px-4 py-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent ${
                view === item.id ? 'border-accent text-white' : 'border-transparent text-muted hover:text-white'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      {computeMutation.isError ? (
        <p className="rounded border border-rose-500/50 bg-rose-500/10 p-4 text-sm text-rose-200" role="alert">
          Nao foi possivel recalcular o periodo. Os valores existentes nao foram alterados.
        </p>
      ) : null}

      {insightMutation.data ? (
        insightMutation.data.is_verified ? (
          <section className="rounded border border-accent/40 bg-surface p-5" aria-labelledby="insight-title">
            <p className="text-xs font-semibold uppercase tracking-wider text-accent">Narrativa numericamente verificada</p>
            <h2 id="insight-title" className="mt-1 font-semibold text-white">Sintese do periodo</h2>
            <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-muted">{insightMutation.data.narrative_text}</p>
          </section>
        ) : (
          <p className="rounded border border-amber-500/50 bg-amber-500/10 p-4 text-sm text-amber-200" role="alert">
            A narrativa foi suprimida porque o guardrail encontrou numeros sem sustentacao no payload calculado.
          </p>
        )
      ) : null}

      {metricsQuery.isLoading ? (
        <p className="rounded border border-surface2 p-12 text-center text-muted" role="status">Carregando metricas publicadas...</p>
      ) : metricsQuery.isError ? (
        <p className="rounded border border-rose-500/50 bg-rose-500/10 p-5 text-rose-200" role="alert">
          Metricas indisponiveis. Nenhum valor substituto foi exibido.
        </p>
      ) : (
        <section aria-label={views.find((item) => item.id === view)?.label} className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {currentDefinitions.map(([id, title, description, Icon]) => (
            <MetricCard
              key={id}
              title={title}
              description={description}
              metric={metricById(id)}
              icon={Icon}
              onOpen={setSelectedMetric}
            />
          ))}
        </section>
      )}

      <MetricDrilldownDialog metric={selectedMetric} filters={filters} onClose={() => setSelectedMetric(null)} />
    </div>
  );
};
