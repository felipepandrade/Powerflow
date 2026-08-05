import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  Layers,
  Clock,
  Calendar,
  Play,
  Sparkles,
  TrendingUp,
  BarChart3,
  PieChart,
  Users,
} from 'lucide-react';
import {
  getMetrics,
  computeMetrics,
  buildSnapshots,
  generateInsight,
  getTasks,
} from '../api/client';
import type { MetricValue, Task } from '../api/client';
import { EthicsBanner } from '../components/cockpit/EthicsBanner';
import { KPICard } from '../components/cockpit/KPICard';
import { NarrativeCard } from '../components/cockpit/NarrativeCard';
import { DrillDownModal } from '../components/cockpit/DrillDownModal';

export const Cockpit: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'overview' | 'flow' | 'capacity' | 'portfolio'>('overview');
  const [selectedMetricForDrilldown, setSelectedMetricForDrilldown] = useState<string | null>(null);

  // Queries
  const { data: metrics = [] } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => getMetrics(),
  });

  const { data: tasksData } = useQuery({
    queryKey: ['tasks'],
    queryFn: getTasks,
  });

  // Mutations
  const computeMutation = useMutation({
    mutationFn: () => computeMetrics(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metrics'] });
    },
  });

  const snapshotsMutation = useMutation({
    mutationFn: () => buildSnapshots(),
    onSuccess: () => {
      computeMutation.mutate();
    },
  });

  const insightMutation = useMutation({
    mutationFn: () => generateInsight('cockpit'),
  });

  // Helper para buscar valor da métrica
  const findMetric = (id: string): MetricValue | undefined => {
    return metrics.find((m) => m.metric_id === id);
  };

  const getMetricVal = (id: string, fallback = 0): number => {
    const m = findMetric(id);
    return m?.value !== null && m?.value !== undefined ? m.value : fallback;
  };

  const tasks: Task[] = tasksData?.data || [];

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto pb-16">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-surface2 pb-6">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight text-white flex items-center gap-3">
            Cockpit Gerencial <span className="text-xs bg-accent/20 text-accent border border-accent/40 px-2.5 py-1 rounded-full uppercase font-mono">v1.2 SaaS</span>
          </h1>
          <p className="text-sm text-muted mt-1 font-light">
            Painel Executivo Analítico — Diagnóstico de Fluxo, Capacidade e Saúde de Projetos.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => snapshotsMutation.mutate()}
            disabled={snapshotsMutation.isPending || computeMutation.isPending}
            className="flex items-center gap-2 bg-surface2 hover:bg-surface text-white text-xs font-semibold px-4 py-2.5 rounded-lg transition-colors border border-surface2 shadow-sm"
          >
            <Play className={`w-3.5 h-3.5 ${snapshotsMutation.isPending ? 'animate-spin' : ''}`} />
            Recalcular Métricas
          </button>

          <button
            onClick={() => insightMutation.mutate()}
            disabled={insightMutation.isPending}
            className="flex items-center gap-2 bg-accent hover:bg-accent/90 text-white text-xs font-bold px-4 py-2.5 rounded-lg transition-all shadow-md shadow-accent/20"
          >
            <Sparkles className={`w-3.5 h-3.5 ${insightMutation.isPending ? 'animate-spin' : ''}`} />
            Gerar Síntese LLM
          </button>
        </div>
      </div>

      {/* Banner de Governança Ética */}
      <EthicsBanner />

      {/* Síntese Narrativa da LLM (Se gerada) */}
      {insightMutation.data && (
        <NarrativeCard
          text={insightMutation.data.narrative_text}
          isVerified={insightMutation.data.is_verified}
          discrepancies={insightMutation.data.discrepancies}
          onRefresh={() => insightMutation.mutate()}
          isLoading={insightMutation.isPending}
        />
      )}

      {/* Navegação por Abas Temáticas */}
      <div className="flex border-b border-surface2 gap-6 text-sm font-semibold">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 flex items-center gap-2 transition-colors relative ${
            activeTab === 'overview' ? 'text-accent border-b-2 border-accent' : 'text-muted hover:text-white'
          }`}
        >
          <Activity className="w-4 h-4" /> Visão Geral Executiva
        </button>
        <button
          onClick={() => setActiveTab('flow')}
          className={`pb-3 flex items-center gap-2 transition-colors relative ${
            activeTab === 'flow' ? 'text-accent border-b-2 border-accent' : 'text-muted hover:text-white'
          }`}
        >
          <BarChart3 className="w-4 h-4" /> Demanda & Fluxo
        </button>
        <button
          onClick={() => setActiveTab('capacity')}
          className={`pb-3 flex items-center gap-2 transition-colors relative ${
            activeTab === 'capacity' ? 'text-accent border-b-2 border-accent' : 'text-muted hover:text-white'
          }`}
        >
          <Clock className="w-4 h-4" /> Agenda & Capacidade
        </button>
        <button
          onClick={() => setActiveTab('portfolio')}
          className={`pb-3 flex items-center gap-2 transition-colors relative ${
            activeTab === 'portfolio' ? 'text-accent border-b-2 border-accent' : 'text-muted hover:text-white'
          }`}
        >
          <Layers className="w-4 h-4" /> Portfólio & Saúde
        </button>
      </div>

      {/* Conteúdo da Aba */}
      {activeTab === 'overview' && (
        <div className="space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <KPICard
              title="Throughput (Vazão)"
              value={getMetricVal('flow.throughput')}
              unit="tarefas/dia"
              description="Quantidade total de tarefas concluídas no período."
              icon={TrendingUp}
              healthStatus="good"
              onClick={() => setSelectedMetricForDrilldown('flow.throughput')}
            />

            <KPICard
              title="Trabalho em Progresso (WIP)"
              value={getMetricVal('flow.wip')}
              unit="tarefas ativas"
              description="Demandas atualmente ativas em execução."
              icon={BarChart3}
              healthStatus={getMetricVal('flow.wip') > 5 ? 'warning' : 'good'}
              onClick={() => setSelectedMetricForDrilldown('flow.wip')}
            />

            <KPICard
              title="Lead Time (p85)"
              value={getMetricVal('flow.lead_time_p85')}
              unit="dias"
              description="Tempo necessário para concluir 85% das demandas."
              icon={Clock}
              healthStatus={getMetricVal('flow.lead_time_p85') > 7 ? 'danger' : 'good'}
              onClick={() => setSelectedMetricForDrilldown('flow.lead_time_p85')}
            />

            <KPICard
              title="Health Score Média"
              value={getMetricVal('project.health_score', 100)}
              unit="pts"
              description="Saúde geral calculada da carteira de projetos."
              icon={Activity}
              healthStatus={getMetricVal('project.health_score', 100) >= 80 ? 'good' : 'warning'}
              onClick={() => setSelectedMetricForDrilldown('project.health_score')}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <KPICard
              title="Horas em Reunião"
              value={getMetricVal('capacity.meeting_hours')}
              unit="horas"
              description="Tempo total em reuniões sincronizadas."
              icon={Calendar}
              healthStatus="neutral"
              onClick={() => setSelectedMetricForDrilldown('capacity.meeting_hours')}
            />

            <KPICard
              title="Tempo Ocupado em Reunião"
              value={getMetricVal('capacity.meeting_ratio')}
              unit="%"
              description="Percentual da jornada comprometida por reuniões."
              icon={PieChart}
              healthStatus={getMetricVal('capacity.meeting_ratio') > 40 ? 'danger' : 'good'}
              onClick={() => setSelectedMetricForDrilldown('capacity.meeting_ratio')}
            />

            <KPICard
              title="Trocas de Contexto"
              value={getMetricVal('capacity.context_switches')}
              unit="trocas/dia"
              description="Média de reuniões/demandas intercaladas."
              icon={Users}
              healthStatus="neutral"
              onClick={() => setSelectedMetricForDrilldown('capacity.context_switches')}
            />
          </div>
        </div>
      )}

      {activeTab === 'flow' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <KPICard
            title="Fluxo Líquido (Net Flow)"
            value={getMetricVal('flow.net_flow')}
            unit="tarefas"
            description="Entradas - Saídas no período."
            icon={TrendingUp}
            onClick={() => setSelectedMetricForDrilldown('flow.net_flow')}
          />
          <KPICard
            title="Idade do WIP (p85)"
            value={getMetricVal('flow.aging_wip_p85')}
            unit="dias"
            description="Idade das demandas abertas no fluxo."
            icon={Clock}
            onClick={() => setSelectedMetricForDrilldown('flow.aging_wip_p85')}
          />
          <KPICard
            title="Lead Time (p50)"
            value={getMetricVal('flow.lead_time_p50')}
            unit="dias"
            description="Mediana do tempo de conclusão."
            icon={Clock}
            onClick={() => setSelectedMetricForDrilldown('flow.lead_time_p50')}
          />
        </div>
      )}

      {activeTab === 'capacity' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <KPICard
            title="Horas em Reunião"
            value={getMetricVal('capacity.meeting_hours')}
            unit="horas"
            icon={Calendar}
            onClick={() => setSelectedMetricForDrilldown('capacity.meeting_hours')}
          />
          <KPICard
            title="Percentual de Reuniões"
            value={getMetricVal('capacity.meeting_ratio')}
            unit="%"
            icon={PieChart}
            onClick={() => setSelectedMetricForDrilldown('capacity.meeting_ratio')}
          />
          <KPICard
            title="Trocas de Contexto"
            value={getMetricVal('capacity.context_switches')}
            unit="trocas/dia"
            icon={Users}
            onClick={() => setSelectedMetricForDrilldown('capacity.context_switches')}
          />
        </div>
      )}

      {activeTab === 'portfolio' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <KPICard
            title="Health Score dos Projetos"
            value={getMetricVal('project.health_score', 100)}
            unit="pts"
            description="Score ponderado de saúde de todos os projetos ativos."
            icon={Activity}
            healthStatus="good"
            onClick={() => setSelectedMetricForDrilldown('project.health_score')}
          />
        </div>
      )}

      {/* Modal Universal de Drill-Down */}
      <DrillDownModal
        isOpen={Boolean(selectedMetricForDrilldown)}
        onClose={() => setSelectedMetricForDrilldown(null)}
        title={`Detalhamento de Evidências — ${selectedMetricForDrilldown}`}
        metricId={selectedMetricForDrilldown || undefined}
        tasks={tasks}
      />
    </div>
  );
};
