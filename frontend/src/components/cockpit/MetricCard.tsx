import { EyeOff, Info, ShieldAlert } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import clsx from 'clsx';
import type { MetricValue } from '../../api/client';

interface MetricCardProps {
  title: string;
  description: string;
  metric?: MetricValue;
  icon: LucideIcon;
  onOpen: (metric: MetricValue) => void;
}

const coverageLabels: Record<string, string> = {
  high: 'Cobertura alta',
  medium: 'Cobertura media',
  low: 'Cobertura baixa',
  unknown: 'Cobertura desconhecida',
};

const formatValue = (value: number, unit?: string): string => {
  const formatted = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value);
  return unit === '%' ? `${formatted}%` : formatted;
};

const formatDelta = (delta: number): string =>
  new Intl.NumberFormat('pt-BR', {
    style: 'percent',
    maximumFractionDigits: 1,
    signDisplay: 'always',
  }).format(delta);

export const MetricCard = ({ title, description, metric, icon: Icon, onOpen }: MetricCardProps) => {
  const isUnknown = !metric || (!metric.is_suppressed && metric.value === null);
  const hasEnvelope = Boolean(metric?.coverage && metric.caveat);
  const cannotPublish = isUnknown || !hasEnvelope;
  const coverageLevel = metric?.coverage?.level ?? 'unknown';
  const coveragePct = metric?.coverage?.pct;

  return (
    <article
      className={clsx(
        'relative flex min-h-72 flex-col rounded-lg border border-surface2 bg-surface p-5',
        coverageLevel === 'low' && 'opacity-75',
        metric?.is_suppressed && 'border-amber-500/50',
      )}
      aria-labelledby={`metric-${metric?.metric_id ?? title}-title`}
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
            {metric?.data_origin ? `Origem: ${metric.data_origin}` : 'Origem nao informada'}
          </p>
          <h3 id={`metric-${metric?.metric_id ?? title}-title`} className="font-semibold text-white">
            {title}
          </h3>
        </div>
        <Icon className="h-5 w-5 shrink-0 text-accent" aria-hidden="true" />
      </div>

      {metric?.is_suppressed ? (
        <div className="flex min-h-20 items-center gap-3 text-amber-300" role="status">
          <EyeOff className="h-5 w-5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-semibold">Valor suprimido</p>
            <p className="text-xs">{metric.suppression_reason || 'Amostra abaixo do minimo de privacidade.'}</p>
          </div>
        </div>
      ) : cannotPublish ? (
        <div className="flex min-h-20 items-center gap-3 text-muted" role="status">
          <ShieldAlert className="h-5 w-5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-semibold text-white">Desconhecido</p>
            <p className="text-xs">
              {!metric
                ? 'Sem valor publicado para o periodo.'
                : 'O backend nao forneceu valor e envelope de cobertura completos.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="min-h-20">
          <p className="text-4xl font-bold tracking-tight text-white">
            {formatValue(metric.value as number, metric.unit)}
            {metric.unit && metric.unit !== '%' ? (
              <span className="ml-2 text-xs font-medium uppercase text-muted">{metric.unit}</span>
            ) : null}
          </p>
          {metric.period_comparison?.delta_pct !== null &&
          metric.period_comparison?.delta_pct !== undefined ? (
            <p className="mt-2 text-xs text-muted">
              {formatDelta(metric.period_comparison.delta_pct)} vs. periodo anterior
            </p>
          ) : (
            <p className="mt-2 text-xs text-muted">Comparacao anterior indisponivel</p>
          )}
        </div>
      )}

      <p className="mt-3 text-sm leading-relaxed text-muted">{description}</p>

      <dl className="mt-4 grid grid-cols-2 gap-2 border-t border-surface2 pt-4 text-xs">
        <div>
          <dt className="text-muted">Cobertura</dt>
          <dd className="mt-1 font-medium text-white">
            {coverageLabels[coverageLevel]}
            {coveragePct !== null && coveragePct !== undefined
              ? ` / ${new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 0 }).format(coveragePct)}`
              : ''}
          </dd>
        </div>
        <div>
          <dt className="text-muted">Amostra</dt>
          <dd className="mt-1 font-medium text-white">
            {metric ? new Intl.NumberFormat('pt-BR').format(metric.sample_size) : 'Desconhecida'}
          </dd>
        </div>
      </dl>

      <button
        type="button"
        onClick={() => metric && onOpen(metric)}
        disabled={!metric || !hasEnvelope}
        className="mt-auto flex min-h-11 items-center justify-center gap-2 rounded border border-accent/50 px-3 py-2 text-sm font-semibold text-accent transition-colors hover:bg-accent/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:border-surface2 disabled:text-muted"
        aria-label={`Abrir formula, cobertura e evidencias de ${title}`}
      >
        <Info className="h-4 w-4" aria-hidden="true" />
        {metric && hasEnvelope ? 'Explicar e rastrear' : 'Rastreabilidade indisponivel'}
      </button>

      {metric?.caveat ? <p className="mt-3 text-xs text-muted">{metric.caveat}</p> : null}
    </article>
  );
};
