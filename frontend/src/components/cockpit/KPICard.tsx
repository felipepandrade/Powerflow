import React from 'react';
import { TrendingUp, TrendingDown, EyeOff, Info } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import clsx from 'clsx';

interface KPICardProps {
  title: string;
  value: number | string | null;
  unit?: string;
  description?: string;
  icon?: LucideIcon;
  delta?: number; // porcentagem de variação
  isSuppressed?: boolean;
  suppressionReason?: string;
  onClick?: () => void;
  healthStatus?: 'good' | 'warning' | 'danger' | 'neutral';
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  unit,
  description,
  icon: Icon,
  delta,
  isSuppressed = false,
  suppressionReason,
  onClick,
  healthStatus = 'neutral',
}) => {
  const statusColors = {
    good: 'border-l-emerald-500 text-emerald-400',
    warning: 'border-l-amber-500 text-amber-400',
    danger: 'border-l-rose-500 text-rose-400',
    neutral: 'border-l-accent text-accent',
  };

  return (
    <div
      onClick={onClick}
      className={clsx(
        'group relative bg-base border border-surface2 p-6 rounded-lg hover:border-accent/60 transition-all duration-300 shadow-sm cursor-pointer overflow-hidden border-l-4',
        statusColors[healthStatus]
      )}
    >
      <div className="flex justify-between items-start mb-3">
        <span className="text-xs font-bold uppercase tracking-wider text-muted group-hover:text-white transition-colors">
          {title}
        </span>
        {Icon && <Icon className="w-5 h-5 text-muted group-hover:text-accent transition-colors" />}
      </div>

      {isSuppressed ? (
        <div className="py-2 flex items-center gap-2 text-amber-400/90 text-xs">
          <EyeOff className="w-4 h-4 flex-shrink-0" />
          <span>{suppressionReason || 'Dado suprimido por K-Anonimato (K < 3)'}</span>
        </div>
      ) : (
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-4xl font-extrabold text-white tracking-tight">
            {value !== null && value !== undefined ? value : '—'}
          </span>
          {unit && <span className="text-xs text-muted font-medium uppercase">{unit}</span>}
        </div>
      )}

      {delta !== undefined && !isSuppressed && (
        <div className="flex items-center gap-1 text-xs mb-2 font-mono">
          {delta >= 0 ? (
            <span className="text-emerald-400 flex items-center gap-0.5 font-semibold">
              <TrendingUp className="w-3.5 h-3.5" /> +{delta}%
            </span>
          ) : (
            <span className="text-rose-400 flex items-center gap-0.5 font-semibold">
              <TrendingDown className="w-3.5 h-3.5" /> {delta}%
            </span>
          )}
          <span className="text-muted text-[10px] uppercase">vs semana anterior</span>
        </div>
      )}

      {description && (
        <p className="text-xs text-muted/80 font-light line-clamp-2 mt-1">
          {description}
        </p>
      )}

      <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] text-accent uppercase font-mono tracking-widest flex items-center gap-1">
        <Info className="w-3 h-3" /> Drill-down →
      </div>
    </div>
  );
};
