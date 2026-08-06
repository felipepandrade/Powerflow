import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CalendarDays, Clock } from 'lucide-react';
import { getCalendarEvents, getMetrics } from '../api/client';
import type { MetricValue } from '../api/client';
import { MetricCard } from '../components/cockpit/MetricCard';
import { MetricDrilldownDialog } from '../components/cockpit/MetricDrilldownDialog';

const toLocalIsoDate = (value: Date): string => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const formatEventTime = (value: string): string =>
  new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));

export const CalendarHonest = () => {
  const [selectedMetric, setSelectedMetric] = useState<MetricValue | null>(null);
  const startDate = toLocalIsoDate(new Date());
  const end = new Date();
  end.setDate(end.getDate() + 7);
  const endDate = toLocalIsoDate(end);
  const metricsQuery = useQuery({
    queryKey: ['metrics', 'capacity'],
    queryFn: () => getMetrics(),
  });
  const eventsQuery = useQuery({
    queryKey: ['calendar-events', startDate, endDate],
    queryFn: () => getCalendarEvents(startDate, endDate),
  });
  const metric = (id: string) => metricsQuery.data?.find((item) => item.metric_id === id);
  const events = eventsQuery.data?.items ?? [];

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Agenda sincronizada</p>
        <h1 className="mt-2 text-3xl font-bold text-white sm:text-4xl">Calendario e capacidade</h1>
        <p className="mt-2 max-w-3xl text-muted">
          Valores so aparecem com jornada, timezone, cobertura e eventos all-day tratados pelo backend.
        </p>
      </header>

      <section className="mt-7 grid gap-5 sm:grid-cols-2" aria-label="Indicadores de agenda">
        <MetricCard
          title="Horas em reuniao"
          description="Tempo ocupado por eventos considerados no periodo publicado."
          metric={metric('capacity.meeting_hours')}
          icon={Clock}
          onOpen={setSelectedMetric}
        />
        <MetricCard
          title="Percentual da jornada em reunioes"
          description="Parcela da jornada configurada comprometida por reunioes."
          metric={metric('capacity.meeting_ratio')}
          icon={CalendarDays}
          onOpen={setSelectedMetric}
        />
      </section>

      {metricsQuery.isError ? (
        <p className="mt-5 rounded border border-rose-500/50 bg-rose-500/10 p-4 text-sm text-rose-200" role="alert">
          Metricas de capacidade indisponiveis.
        </p>
      ) : null}

      <section className="mt-8 rounded border border-surface2 bg-surface p-6" aria-labelledby="upcoming-events-title">
        <CalendarDays className="h-7 w-7 text-muted" aria-hidden="true" />
        <h2 id="upcoming-events-title" className="mt-3 font-semibold text-white">Proximos eventos</h2>
        {eventsQuery.isLoading ? (
          <p className="mt-3 text-sm text-muted" role="status">Carregando eventos normalizados...</p>
        ) : eventsQuery.isError ? (
          <p className="mt-3 text-sm text-rose-200" role="alert">Eventos indisponiveis. Nenhum horario substituto foi exibido.</p>
        ) : eventsQuery.data?.state === 'unknown' ? (
          <p className="mt-3 text-sm text-muted">
            Cobertura incompleta: faltam {eventsQuery.data.coverage.missing_dates.join(', ')}. Os itens abaixo podem ser parciais.
          </p>
        ) : null}

        {events.length === 0 && eventsQuery.isSuccess ? (
          <p className="mt-3 text-sm text-muted">Nenhum evento retornado no periodo coberto.</p>
        ) : (
          <ul className="mt-4 divide-y divide-surface2">
            {events.map((event) => (
              <li key={`${event.source_item_id}-${event.starts_at}`} className="py-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="font-medium text-white">{event.is_redacted ? 'Compromisso privado' : event.subject || 'Assunto nao informado'}</p>
                  <time className="text-sm text-muted" dateTime={event.starts_at}>
                    {event.is_all_day ? 'Dia inteiro' : formatEventTime(event.starts_at)}
                  </time>
                </div>
                <p className="mt-1 text-xs text-muted">
                  {event.is_redacted ? 'Conteudo redigido por privacidade.' : `Disponibilidade: ${event.show_as || 'nao informada'}`}
                </p>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-xs text-muted">Fonte: calendar_events + daily_calendar_snapshots</p>
      </section>

      <MetricDrilldownDialog metric={selectedMetric} filters={{}} onClose={() => setSelectedMetric(null)} />
    </div>
  );
};