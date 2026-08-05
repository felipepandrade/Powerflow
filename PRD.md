# PRD — Powerflow
### Sistema Pessoal de Captura Autônoma, Gestão Correlacionada de Tarefas e **Cockpit Gerencial**

**Versão:** 1.2 (consolidada) · **Autor:** Felipe Porto Andrade · **Data:** 2026-08-04
**Destinatário:** agente de desenvolvimento assistido por IA (Antigravity, Cursor, Claude Code, Windsurf ou equivalente)

## Índice

1. Contexto, Problema e Advertência Metodológica
2. Visão do Produto
3. Objetivos e Métricas de Sucesso
4. Personas
5. Escopo
6. Modelo Conceitual do Domínio
7. Requisitos Funcionais (Épicos A–K)
8. Ética Analítica e Governança de Métricas
9. Requisitos Não-Funcionais
10. Arquitetura
11. Modelo de Dados
12. Catálogo de Métricas
13. Contratos de API
14. Estratégia de Deploy
15. Configuração
16. Estratégia de Testes
17. Roadmap de Entrega
18. Riscos e Mitigações
19. Documentação a ser Gerada
20. Prompt Inicial para o Agente
21. Próximos Passos

---

## 1. Contexto, Problema e Advertência Metodológica

### 1.1 O problema operacional (v1.0/v1.1)

Profissionais em posições de coordenação recebem demandas de forma **não estruturada** em três canais: e-mail (Outlook), mensagens (Teams) e reuniões (Calendário). O gargalo não é executar — é **capturar, correlacionar e acompanhar**.

| Dor | Manifestação concreta |
|---|---|
| Captura manual | Distinguir tarefa sua de FYI de delegação exige leitura ativa de todo o fluxo |
| Fragmentação | Uma demanda se espalha por 3 e-mails, 2 chats e 1 reunião |
| Ciclo longo | Tarefas dependentes de terceiros morrem por falta de gatilho, não de intenção |
| Contexto perdido | Sem o "porquê" e o "quem pediu", a tarefa vira item sem sentido duas semanas depois |
| Cegueira de capacidade | Compromissos assumidos ignoram a agenda real |

### 1.2 O problema gerencial (novo na v1.2)

Uma vez que o fluxo de trabalho está estruturado, capturado e datado, ele deixa de ser apenas uma lista e passa a ser **um registro longitudinal do funcionamento da gerência**. Isso permite responder perguntas que hoje só são respondidas por percepção:

| Pergunta gerencial | Hoje | Com o cockpit |
|---|---|---|
| De onde vem minha demanda? | Impressão | Distribuição por origem, área, projeto, tipo |
| Estou entregando mais do que entra? | Sensação | *Net flow* semanal, throughput vs. inflow |
| Onde meu fluxo trava? | Memória dos casos ruins | Tempo médio em `waiting_on` por interface |
| Quais interfaces geram mais espera? | Anedota | Ranking agregado por área com idade dos bloqueios |
| Quais projetos estão silenciosamente parando? | Descoberta tardia | Alerta de projeto sem atividade + marcos em risco |
| Minha agenda permite entregar o que prometi? | Descoberta no dia | Capacidade projetada vs. compromissos assumidos |
| Cumpro os prazos que eu mesmo dou? | Não se mede | Aderência a prazo e *slip* médio |
| O que levo para a reunião de resultados? | Montagem manual de horas | One-pager gerado, com drill-down até a evidência |

### 1.3 ⚠️ Advertência metodológica (ler antes de projetar qualquer dashboard)

**A fonte de dados é a sua caixa postal, seus chats e sua agenda.** Isso significa que o cockpit mede **o fluxo de trabalho que passa por você** — não a gerência em sentido objetivo e completo. Três consequências que precisam estar codificadas no produto, não apenas documentadas:

| Limitação | Consequência prática | Como o produto trata |
|---|---|---|
| **Viés de fonte única** | Trabalho que a equipe faz sem te copiar é invisível. Um time excelente e autônomo aparece como "pouca atividade". | Toda métrica exibe **badge de cobertura e escopo** ("visão do fluxo que passa pelo gestor"); nenhuma métrica de volume é apresentada como proxy de produtividade de terceiros |
| **Viés de canal** | Quem resolve por telefone ou presencialmente não gera registro. | `Interações` incluem reuniões; métricas de responsividade exibem contagem de touchpoints conhecidos, com aviso explícito de subestimação |
| **Métrica como incentivo** | Medir "tempo de resposta por pessoa" muda o comportamento das pessoas — quase sempre para pior (respostas rápidas e vazias). | Ver **Seção 8 — Ética Analítica**: agregação por área como padrão, k-anonimato, proibição de ranking individual |

**Princípio:** o cockpit é instrumento de **diagnóstico do sistema de trabalho**, não de **avaliação de pessoas**. Essa distinção precisa aparecer na UI, não só neste documento.

---

## 2. Visão do Produto

> Um copiloto pessoal que lê continuamente e-mails, chats e agenda; identifica compromissos com evidência rastreável; decide se cada informação é tarefa nova, atualização de uma existente ou contexto correlato; gerencia ativamente compromissos que dependem de terceiros; **e transforma esse registro longitudinal em um cockpit de diagnóstico e decisão gerencial.**

### Princípios de produto

| Princípio | Implicação de design |
|---|---|
| **Human-in-the-loop assimétrico** | Ações que *aumentam* trabalho aparente podem ser automáticas. Ações que *fecham o loop* (concluir, cancelar, antecipar prazo) exigem confirmação. |
| **Rastreabilidade total** | Toda tarefa, toda mudança de status **e todo número em dashboard** apontam para a fonte. Zero número órfão. |
| **Decisão determinística** | O LLM produz *evidência e hipótese*. A decisão e **todo cálculo numérico** são código testável — nunca o modelo. |
| **Métrica com ação** | Nenhuma métrica entra no cockpit sem a pergunta gerencial que responde e a ação esperada. Anti-vanity-metric por construção. |
| **Honestidade sobre incerteza** | Métrica sem cobertura suficiente é exibida como incerta ou suprimida — nunca apresentada como fato. |
| **Diagnóstico, não vigilância** | Agregação por padrão; nenhuma métrica de desempenho individual de terceiros. |
| **Privacidade por padrão** | Conteúdo sensível não sai do perímetro. Suporte a LLM local. Default restritivo. |
| **Local-first, cloud-ready** | Mesmo código, mesma imagem, no notebook ou na nuvem. |
| **Reversibilidade** | Toda ação automática é desfeita em um clique. |

---

## 3. Objetivos e Métricas de Sucesso

### 3.1 Camada operacional

| # | Objetivo | Métrica | Meta MVP |
|---|---|---|---|
| O1 | Reduzir captura manual | % de tarefas criadas via sugestão aceita | ≥ 70% |
| O2 | Precisão da extração | Precision de itens propostos | ≥ 80% |
| O3 | Cobertura da extração | Recall de tarefas reais | ≥ 75% |
| O4 | Acurácia da correlação | % de decisões corretas (nova / update / contexto) | ≥ 85% |
| O5 | Confiança nas automações | Taxa de *undo* de ações automáticas | ≤ 10% |
| O6 | Eliminar follow-ups esquecidos | Tarefas `waiting_on` acima do SLA | ≤ 5% |
| O7 | Fricção de triagem | Tempo médio de triagem diária | ≤ 5 min |
| O8 | Ruído controlado | % de itens de triagem marcados como irrelevantes | ≤ 20% |
| O9 | Custo operacional | Custo de LLM por dia | < USD 0,50 |

### 3.2 Camada gerencial (nova)

| # | Objetivo | Métrica | Meta |
|---|---|---|---|
| O10 | Reduzir esforço de reporte | Tempo para produzir o one-pager mensal | de horas para **< 15 min** |
| O11 | Antecipar problemas | % de projetos em atraso detectados pelo alerta **antes** de escalarem por terceiros | ≥ 70% |
| O12 | Confiabilidade dos números | Divergências encontradas em auditoria manual trimestral de 10 métricas | **0 divergências** |
| O13 | Métricas acionáveis | % de métricas do cockpit com ação registrada nos últimos 90 dias | ≥ 60% |
| O14 | Cobertura declarada | % de métricas exibindo indicador de cobertura/escopo | **100%** |
| O15 | Uso efetivo | Nº de decisões/ações registradas a partir de um insight ou alerta / mês | ≥ 4 |

> O13 e O15 existem para matar métrica decorativa. Se um indicador não gera ação em 90 dias, ele é candidato à remoção — e o sistema deve sinalizar isso.

---

## 4. Personas

- **P1 — Usuário Principal (Coordenador/Gerente).** Alto volume de mensagens, muitas tarefas delegadas, agenda densa. Precisa de visão consolidada de pendências por pessoa, projeto e dia — e agora também de **visão agregada do funcionamento da sua área** para reuniões de resultado e decisão.
- **P2 — Administrador Técnico (o próprio usuário no MVP).** Instala, configura credenciais, ajusta limiares, define métricas e alertas.
- **P3 — Consumidor de Reporte (chefia, pares) — indireto.** Não acessa o sistema no MVP; consome o **one-pager exportado**. Determina o formato de saída, não a interface.

---

## 5. Escopo

### 5.1 No escopo (MVP)

**Operacional (v1.0/v1.1)**
1. Autenticação Microsoft Entra ID (delegada, single-user)
2. Ingestão incremental de e-mails (Outlook) via Graph *delta*
3. Ingestão de chats 1:1 e de grupo do Teams
4. Ingestão de calendário com expansão de recorrências
5. Extração de sinais por LLM com citação literal obrigatória
6. Motor de correlação: nova tarefa / atualização / transição / subtarefa / duplicata / contexto / ruído
7. Fila de triagem (aprovar, editar, rejeitar, fundir, desambiguar)
8. CRUD de tarefas, projetos e stakeholders
9. Máquina de estados com histórico auditável e undo de ações automáticas
10. Motor de follow-up ciente de reuniões
11. Consciência de capacidade e pauta sugerida por reunião
12. Digest diário e semanal
13. Web UI (SPA) responsiva
14. Deploy local (Docker Compose) e cloud

**Cockpit gerencial (v1.2 — novo)**
15. **Estrutura organizacional leve:** áreas/times, vínculo de stakeholders, portfólios
16. **Marcos (milestones)** vinculados a projetos, com prazo e responsável
17. **Camada analítica (read model)** com *snapshots* diários append-only
18. **Motor de métricas determinístico** com registro versionado de definições
19. **Catálogo de KPIs** em 7 perspectivas (Seção 12)
20. **Cockpit executivo** + 6 dashboards temáticos com filtros e comparação de período
21. **Drill-down universal** de qualquer número até a tarefa e a evidência textual de origem
22. **Motor de alertas** (limiar + anomalia estatística simples)
23. **Insights narrativos assistidos por LLM** sobre métricas já calculadas, com guardrail numérico
24. **Registro de decisões e ações** vinculado a métricas e alertas
25. **Entrada manual e importação CSV** para dados não derivávies de comunicação
26. **Exportação de relatórios** (Markdown/PDF/PPTX) e **datasets** para BI corporativo (CSV/Parquet)

### 5.2 Fora do escopo do MVP (backlog explícito)

- Multi-tenant / multiusuário com isolamento
- **Acesso de terceiros ao cockpit** (chefia, pares) — requer modelo de permissão e revisão ética prévia
- Canais de reunião do Teams (`ChannelMessage.Read.All` — exige permissão de aplicação e *Protected APIs*)
- Transcrições de reuniões / Teams Premium
- Escrita bidirecional em To Do / Planner / Jira
- Ingestão de sistemas corporativos (SAP, ServiceNow, Jira, Power BI datasets)
- Previsão probabilística (Monte Carlo de prazo) — depende de ≥ 6 meses de histórico
- App mobile nativo
- Envio automático de e-mails sem confirmação humana

### 5.3 Não-objetivos (limites permanentes)

- **Não** é sistema de gestão de projetos corporativo — não substitui Planner/Jira
- **Não** é ferramenta de **avaliação de desempenho individual** nem de monitoramento de pessoas
- **Não** é substituto do BI corporativo — **alimenta** o BI, não compete com ele
- **Não** produz métrica sem cobertura declarada nem número sem rastreabilidade
- **Não** toma decisões de negócio em nome do usuário

---

## 6. Modelo Conceitual do Domínio

Quatro conceitos em cadeia, cada um com responsabilidade única:

```
SourceItem  ──▶   Signal   ──▶    Task    ──▶   Fact / Metric
(e-mail,          (fato            (unidade      (agregado
 chat,             extraído,        de trabalho    temporal,
 evento)           pré-decisão)     gerenciada)    read model)

 [ingestão]      [extração]      [correlação]    [analítica]
```

### 6.1 `SourceItem` — unidade canônica de ingestão
Abstração única sobre e-mail, mensagem de chat e evento de calendário, com discriminador `kind`. Toda evidência aponta para cá.

### 6.2 `Signal` — fato extraído, ainda não decidido
Um `SourceItem` produz zero ou N `Signals`: afirmações candidatas ainda não resolvidas contra o estado da base.

### 6.3 `Task` / `Project` / `Milestone` — o estado operacional mutável
O que existe agora. Muta.

### 6.4 `Snapshot` / `MetricValue` — o read model imutável (novo)

**Problema:** tabelas operacionais mutam. Se hoje uma tarefa está `done`, a base não sabe mais que ela ficou 12 dias em `blocked` — a menos que se reconstrua tudo do histórico, o que é caro e frágil para dashboards.

**Solução:** *snapshot* diário **append-only** do estado de cada tarefa e projeto + tabela de valores de métrica materializados. Séries temporais passam a ser leitura direta, não reconstrução.

| Conceito | Natureza | Uso |
|---|---|---|
| `daily_task_snapshots` | Append-only, 1 linha por tarefa ativa por dia | Aging, WIP histórico, tempo em estado, burn-up |
| `daily_project_snapshots` | Append-only, 1 linha por projeto por dia | Saúde histórica, tendência |
| `metric_values` | Materializado, recalculável | Séries de KPI por período e dimensão |
| `metric_definitions` | Registro versionado (code-first) | Fórmula, dono, ação esperada, limitações |

**Regra:** `task_status_history` continua sendo a **fonte de verdade auditável**; os snapshots são um *read model derivado e reconstruível*. Todo snapshot deve ser regenerável a partir do histórico (comando `taskflow backfill-snapshots`).

### 6.5 Entidades — visão geral

```
Area ──1:N── Stakeholder ──N:M── Task ──1:N── TaskEvidence ──N:1── SourceItem
                                    │                                  │
Portfolio ──1:N── Project ──1:N────┤                                  ├──1:1── CalendarEvent
                    │               ├──1:N── TaskStatusHistory          └──1:N── Signal
                    ├──1:N── Milestone                                            │
                    └──1:N── DailyProjectSnapshot                                  └──1:N── CorrelationRun
                                    │
                             DailyTaskSnapshot ──▶ MetricValue ──▶ Insight / Alert ──▶ DecisionLog
```

---

## 7. Requisitos Funcionais

Formato `RF-<épico>.<n>`, com critérios de aceite em Gherkin. **O agente deve gerar teste automatizado rastreável para cada critério.**

---

### Épico A — Autenticação e Conexão

**RF-A.1** Autenticação via Entra ID com MSAL: *Authorization Code + PKCE* (web) e *Device Code* (CLI/headless).

**RF-A.2** Token cache persistido cifrado (AES-GCM, chave derivada de `ENCRYPTION_KEY` ou keyring do SO). Refresh automático e transparente.

**RF-A.3** Tela de status com escopos concedidos, estado e última sincronização por canal (mail / chat / calendar).

**RF-A.4 — Escopos Graph delegados requeridos:**

| Escopo | Finalidade |
|---|---|
| `User.Read` | Identidade |
| `Mail.Read` | Ingestão de e-mails |
| `Mail.Send` | Nudges (somente após confirmação explícita) |
| `Chat.Read` | Ingestão de chats |
| `Calendars.Read` | Ingestão de calendário |
| `Calendars.Read.Shared` | Opcional |
| `People.Read` | Resolução de stakeholders |
| `User.ReadBasic.All` | **Novo** — enriquecer área/departamento de stakeholders para agregação organizacional |
| `offline_access` | Refresh token |

> ⚠️ **Dependência externa crítica:** *App Registration* com *admin consent* no tenant ENGIE. Apenas escopos **delegados** — nenhuma permissão de aplicação. `User.ReadBasic.All` é delegado e comumente aprovado, mas confirme com IT.

```gherkin
Cenário: Renovação transparente de token
  Dado que o access token expirou
  Quando o job de sincronização executa
  Então o refresh token obtém novo access token
  E a sincronização conclui sem intervenção do usuário

Cenário: Consentimento revogado
  Dado que o refresh token foi invalidado no tenant
  Quando a sincronização falha com 401 persistente
  Então o canal é marcado como "reauth_required"
  E o usuário recebe alerta na UI
  E nenhum retry adicional ocorre por 1 hora
```

---

### Épico B — Ingestão de E-mail e Chat

**RF-B.1** Sincronização incremental de e-mail via `GET /me/mailFolders/{id}/messages/delta`, com `deltaLink` por pasta.

**RF-B.2** Chats: enumerar `GET /me/chats`, então `GET /me/chats/{id}/messages` filtrado por `lastModifiedDateTime` — ou `/delta` quando suportado. **Validar suporte na versão corrente e implementar fallback por timestamp.**

**RF-B.3** Normalização para `SourceItem` via padrão Adapter — o domínio não conhece Graph.

**RF-B.4** Idempotência via `UNIQUE(kind, external_id, revision_hash)`.

**RF-B.5** Rate limits: honrar `Retry-After`, backoff exponencial com jitter, circuit breaker.

**RF-B.6** Escopo configurável: pastas incluídas/excluídas, chats silenciados, allow/blocklist de remetentes, descarte de automáticos (`X-Auto-Response-Suppress`, `no-reply@`, newsletters).

**RF-B.7 — Métrica de cobertura de ingestão (novo).** Cada execução registra: itens vistos, filtrados, extraídos, falhos. Alimenta o indicador de cobertura exigido pelo RF-I.6.

```gherkin
Cenário: Sincronização incremental
  Dado um deltaLink válido para a pasta Inbox
  Quando o job executa
  Então apenas mensagens criadas ou modificadas desde o último delta são recuperadas
  E o novo deltaLink é persistido atomicamente após processamento bem-sucedido

Cenário: Rate limit
  Dado que o Graph responde 429 com Retry-After: 30
  Quando o cliente recebe a resposta
  Então aguarda 30 segundos antes do retry
  E não excede 5 tentativas
```

---

### Épico F — Ingestão de Calendário

**RF-F.1** Sincronização incremental via `GET /me/calendarView/delta?startDateTime={T-30d}&endDateTime={T+90d}`.

> **Decisão:** usar `calendarView`, **não** `/events` — `calendarView` expande instâncias de recorrentes, comportamento necessário para 1:1s e weeklies, onde o acompanhamento realmente acontece. Janela deslizante configurável; `deltaLink` em `sync_state`.

**RF-F.2** Campos capturados:

| Campo | Uso |
|---|---|
| `subject`, `bodyPreview`, `body` | Extração de agenda e itens de ação |
| `organizer`, `attendees[].status.response` | Grafo de stakeholders; quem confirmou |
| `start`, `end`, `isAllDay`, `timeZone` | Ancoragem temporal, capacidade, **métricas de agenda** |
| `seriesMasterId`, `type`, `recurrence` | Séries e exceções; **análise de recorrentes** |
| `isOnlineMeeting`, `onlineMeeting.joinUrl` | **Chave de correlação com chats do Teams** |
| `isCancelled`, `showAs`, `responseStatus` | Filtros e sinais de mudança |
| `categories`, `importance` | Heurísticas de filtro e classificação temática |
| `webLink` | Deep link |
| `attachments` (metadados) | Contexto |
| `sensitivity` | **Filtro de privacidade** |

**RF-F.3 — Privacidade de calendário (não negociável).** Eventos com `sensitivity IN ('private','confidential')` ou `showAs='oof'` são ingeridos apenas como **bloco de tempo ocupado** (`start`, `end`, `busy_status`). Assunto, corpo e participantes ficam nulos e **nunca** são enviados ao LLM. Contam para métricas de **capacidade**, nunca para métricas de **conteúdo**.

**RF-F.4 — Pré-filtros determinísticos:**
- Cancelados → apenas `SCHEDULE_CHANGE`
- Declinados pelo usuário → ignorados (mas contados como "recusados" na métrica de agenda)
- Blocos pessoais → apenas ocupação
- Sem corpo, sem outros participantes, recorrente → apenas ocupação
- Instâncias de série: extrair conteúdo **apenas se `body_hash` mudou**

**RF-F.5 — Tipos de sinal de calendário:**

| Sinal | Efeito típico |
|---|---|
| `PREP_REQUIRED` | Nova tarefa com prazo = início da reunião |
| `AGENDA_COMMITMENT` | Nova tarefa ou vínculo a existente |
| `INTERACTION_OCCURRED` | Reseta relógio de *staleness*; registra touchpoint |
| `FORUM_AVAILABLE` | Substitui nudge por "levar na reunião de {data}" |
| `DEADLINE_ANCHOR` | Ancoragem ou ajuste de `due_date` / marco |
| `CAPACITY` | Alimenta visão "Hoje" e **métricas de agenda** |
| `SCHEDULE_CHANGE` | Reavalia prazos dependentes; alerta |

**RF-F.6 — Consciência de capacidade.** A visão "Hoje" calcula horas livres (`work_hours − reuniões − buffer`). Dias com < 1h livre exibem alerta.

**RF-F.7 — Correlação reunião ↔ chat do Teams** via `onlineMeeting.joinUrl`.

**RF-F.8 — Pauta sugerida** por reunião futura, com tarefas abertas relacionadas aos participantes ou ao projeto. Fixável pelo usuário.

**RF-F.9 — Classificação de reuniões para analítica (novo).** Cada evento recebe classificação derivada, para as métricas da Perspectiva 5:
- `meeting_class`: `1:1 | team | project | governance | external | personal_block`
- `has_agenda`: corpo com conteúdo estruturado
- `produced_action_items`: gerou ≥ 1 sinal acionável
- `is_recurring`
- Vínculo opcional a `project_id` / `area_id` para atribuição de tempo

```gherkin
Cenário: Reunião substitui cobrança por e-mail
  Dado uma tarefa em "waiting_on_others" com stakeholder Maria
  E que a tarefa está estagnada há 5 dias
  E que existe uma reunião futura com Maria em 18 horas
  Quando o motor de follow-up avalia a tarefa
  Então nenhum nudge por e-mail é sugerido
  E é criado um follow-up do tipo "bring_to_meeting" referenciando o evento

Cenário: Evento privado nunca alcança o LLM
  Dado um evento com sensitivity = "private"
  Quando a ingestão processa o evento
  Então apenas start, end e busy_status são persistidos
  E subject, body e attendees permanecem nulos
  E o evento nunca é enviado ao provedor de LLM
  E o evento conta apenas para métricas de capacidade

Cenário: Série recorrente sem conteúdo novo
  Dado uma reunião semanal cujo corpo não mudou
  Quando a ingestão processa a nova instância
  Então nenhuma extração por LLM é executada
  E apenas os sinais CAPACITY e INTERACTION_OCCURRED são gerados
```

---

### Épico C — Extração de Sinais

Pipeline de 4 estágios, custo crescente, filtragem agressiva:

```
[1] Pré-filtro determinístico   → descarta ~60%
[2] Classificador leve          → "contém compromisso acionável?" (modelo pequeno, thinking=0)
[3] Extração estruturada        → LLM reasoner com responseSchema forçado
[4] Persistência como Signal    → estado pending_correlation
```

**RF-C.1** Saída validada contra schema Pydantic. Falha → 1 retry com o erro no prompt → dead letter + revisão manual.

**RF-C.2 — Schema de saída:**

```json
{
  "has_actionable_item": true,
  "signals": [{
    "signal_type": "commitment | progress_update | completion | blocker | due_date_change | prep_required | agenda_commitment | deadline_anchor | context",
    "title": "string (máx 120 chars, verbo no imperativo)",
    "description": "string",
    "owner_type": "me | delegated | shared | unclear",
    "waiting_on": "string|null",
    "due_date": "YYYY-MM-DD|null",
    "due_date_confidence": "explicit | inferred | none",
    "priority": "critical | high | medium | low",
    "task_type": "action | decision | approval | information_request | commitment_made",
    "demand_origin": "internal_area | peer_area | management | external | self",
    "project_hint": "string|null",
    "explicit_identifiers": ["string"],
    "stakeholders": ["email|nome"],
    "estimated_effort_minutes": "int|null",
    "evidence_quote": "string (trecho LITERAL da fonte, obrigatório)",
    "confidence": 0.0
  }],
  "reasoning": "string (máx 200 chars)"
}
```

> `demand_origin` é novo na v1.2 — alimenta a análise de **origem da demanda** (Perspectiva 1).

**RF-C.3 — Guardrail anti-alucinação.** `evidence_quote` **deve** ser substring literal do `SourceItem`. Falha ⇒ sinal descartado, log WARNING.

**RF-C.4 — Roteamento por confiança:** `≥ EXTRACTION_MIN` (0,55) persiste como `Signal`; abaixo, descarta e loga para tuning.

**RF-C.5** Porta `LLMProvider` com adapters: **Gemini (default)**, Azure OpenAI, OpenAI, Anthropic, Ollama.

**RF-C.6 — Feedback loop.** Rejeições e edições persistidas em `task_proposals.user_edits`, injetadas como few-shots. Sem fine-tuning no MVP.

```gherkin
Cenário: Guardrail de evidência
  Dado que o LLM retorna evidence_quote não presente no corpo da fonte
  Quando o validador executa
  Então o sinal é descartado
  E um log WARNING é registrado com o id do source_item
```

---

### Épico G — Motor de Correlação e Resolução

Três estágios, **decisão final sempre determinística** no domínio.

```
Signal
  ├─▶ [G1] RECUPERAÇÃO       determinístico · barato · alto recall
  ├─▶ [G2] RACIOCÍNIO        1 chamada LLM · sinal + fichas dos candidatos
  └─▶ [G3] ARBITRAGEM        determinístico · domínio puro · testável
```

#### G1 — Recuperação de candidatos

**RF-G.1** Seis recuperadores em paralelo:

| # | Recuperador | Natureza | Peso |
|---|---|---|---|
| R1 | **Thread** — `conversation_id` idêntico | Determinístico, mais forte | 1,00 |
| R2 | **Evento** — `event_id`, `series_master_id` ou `join_url` | Determinístico | 0,95 |
| R3 | **Identificador explícito** — código de projeto, ticket, contrato | Determinístico | 0,90 |
| R4 | **Participantes** — Jaccard sobre stakeholders | Heurístico | 0,55 |
| R5 | **Léxico** — BM25 / FTS5 / `tsvector` | Heurístico | 0,65 |
| R6 | **Semântico** — kNN sobre embeddings | Semântico | 0,75 |

**RF-G.2 — Fusão por RRF:** `score = Σᵢ pesoᵢ / (RRF_K + rankᵢ)`, `RRF_K = 60`, com boost por proximidade temporal e por status ativo. Top-K = 8.

**RF-G.3 — Atalho determinístico.** Se R1 ou R2 retorna exatamente uma tarefa ativa e nenhum outro candidato passa do limiar, **G2 é pulado** para sinais simples (`progress_update`, `context`, `interaction`).

**RF-G.4** Candidatos vazios ⇒ `NEW_TASK` direto, sem chamada extra.

#### G2 — Raciocínio relacional

**RF-G.5** Uma chamada recebe: o `Signal`, o `SourceItem` (respeitando privacidade) e **fichas compactas** dos ≤ 8 candidatos (id, título, status, prazo, `waiting_on`, projeto, últimas 2 evidências, último update). **Nunca** a tarefa completa.

**RF-G.6 — Schema de saída:**

```json
{
  "signal_id": "uuid",
  "assessments": [{
    "task_id": "uuid",
    "relation": "same_task | status_update | due_date_change | scope_change | subtask_of | blocks | duplicate_of | related_context | unrelated",
    "confidence": 0.0,
    "rationale": "string (máx 200 chars)",
    "evidence_quote": "string (substring LITERAL do source item)",
    "proposed_change": {
      "to_status": "string|null",
      "new_due_date": "YYYY-MM-DD|null",
      "new_waiting_on": "string|null",
      "progress_note": "string|null",
      "priority": "string|null"
    }
  }],
  "decision": {
    "kind": "NEW_TASK | UPDATE_EXISTING | TRANSITION_EXISTING | SPLIT | MERGE_DUPLICATE | ATTACH_CONTEXT | NOISE",
    "primary_task_id": "uuid|null",
    "confidence": 0.0,
    "ambiguity_reason": "string|null"
  }
}
```

**RF-G.7 — Os 4 guardrails (programáticos, antes de qualquer efeito):**

| # | Guardrail | Falha ⇒ |
|---|---|---|
| 1 | `evidence_quote` é substring literal do `SourceItem` | Descarte do assessment |
| 2 | `task_id` pertence ao conjunto de candidatos enviado | Descarte — impede invenção de ID |
| 3 | `to_status` é transição válida na `TaskStateMachine` | Descarte da mudança de status |
| 4 | Dois candidatos `same_task` com confianças dentro de `CORR_AMBIGUITY_DELTA` | Força `ambiguity_reason` → triagem |

#### G3 — Arbitragem: matriz de decisão

**RF-G.8** Tabela determinística em `domain/policies/correlation_policy.py`:

| Decisão | Confiança | Condição adicional | Ação |
|---|---|---|---|
| `UPDATE_EXISTING` | ≥ 0,80 | — | **Auto-aplica** update + evidência |
| `UPDATE_EXISTING` | 0,55–0,80 | — | Triagem |
| `TRANSITION` → `in_progress`/`waiting_on_others`/`blocked` | ≥ 0,85 | Match determinístico (R1/R2) | **Auto-aplica**, `actor='llm'` |
| `TRANSITION` → `done` | ≥ 0,90 | Conclusão vinda do **responsável** **E** match determinístico | Auto-aplica, **reversível**, destacado no digest |
| `TRANSITION` → `done` | qualquer | Sem match determinístico | **Sempre triagem** |
| `TRANSITION` → `cancelled` | qualquer | — | **Sempre triagem — nunca automático** |
| `due_date_change` | ≥ 0,85 | Nova data **posterior** | Auto-aplica |
| `due_date_change` | qualquer | Nova data **anterior** (antecipação) | **Sempre triagem** |
| `NEW_TASK` | ≥ 0,85 | Candidatos vazios ou todos `unrelated` | Auto-cria (`auto_created=true`) |
| `NEW_TASK` | 0,55–0,85 | — | Triagem |
| `SPLIT` / `subtask_of` | ≥ 0,80 | — | Triagem (mudança estrutural) |
| `MERGE_DUPLICATE` | ≥ 0,90 | — | Triagem com preview |
| `ATTACH_CONTEXT` | ≥ 0,60 | — | **Auto-aplica** evidência `role='context'`, sem alterar status/prazo |
| `NOISE` | ≥ 0,70 | — | Descarta; loga |
| qualquer | < 0,55 | — | Descarta; loga |

**Princípios invioláveis:**
1. Tudo que **aumenta** trabalho aparente pode ser automático — erro barato e visível.
2. Tudo que **fecha o loop** (`done`, `cancelled`, antecipar prazo) exige humano, salvo evidência forte com match determinístico.
3. Toda ação automática é **reversível em um clique** e listada no digest.

**RF-G.9 — `ATTACH_CONTEXT` é cidadão de primeira classe.** A maior parte do tráfego é assunto correlato. Absorvê-lo sem gerar item acionável é o que impede fadiga de triagem — e, na v1.2, é também o que enriquece a análise de contexto por projeto.

**RF-G.10 — Reprocessamento tardio.** Sinais em `pending_correlation` por `SIGNAL_PENDING_TTL_DAYS` (7). Reavaliação de órfãos apenas em G1 (barato); sobem a G2 só se surgir candidato acima do limiar.

**RF-G.11 — Ledger de interações.** `stakeholder_interactions` registra todo touchpoint (e-mail in/out, chat, **reunião realizada**, nudge). `last_interaction_at` alimenta *staleness* **e as métricas de interface da Perspectiva 3**.

```gherkin
Cenário: Chat confirma conclusão de tarefa da mesma thread
  Dado uma tarefa em "waiting_on_others" vinculada ao chat "19:abc"
  Quando uma mensagem do responsável diz "subi o relatório, tá aprovado"
  Então R2 retorna a tarefa com score 0.95
  E o LLM classifica relation = "status_update", to_status = "done", confidence >= 0.90
  E a transição é aplicada com actor = "llm"
  E o item consta no digest como "concluído automaticamente — reverter?"

Cenário: E-mail correlato não vira tarefa
  Dado uma tarefa aberta sobre o Projeto Alfa
  Quando chega um memorando de contexto do Projeto Alfa, sem pedido
  Então a decisão é ATTACH_CONTEXT
  E nenhuma tarefa nova é criada
  E a evidência é anexada com role = "context"

Cenário: Antecipação de prazo nunca é automática
  Dado uma tarefa com due_date em 30 dias
  Quando um e-mail indica prazo para a próxima semana
  Então a mudança vai para triagem, mesmo com confiança 0.95

Cenário: LLM não pode inventar task_id
  Dado que o LLM retorna task_id ausente do conjunto de candidatos
  Quando o guardrail 2 executa
  Então o assessment é descartado
  E o bloqueio é registrado em correlation_runs.guardrail_blocks
```

---

### Épico D — Gestão de Tarefas, Projetos e Estrutura Organizacional

**RF-D.1 — Máquina de estados** com transições validadas em tabela única. Transição inválida ⇒ `409 Conflict`.

```
inbox → open → in_progress → waiting_on_others → blocked → done
                    ↓                                        ↑
                 cancelled ←──────────────────────────────────┘
```

**RF-D.2 — `TaskStatusHistory` imutável:** `from_status`, `to_status`, `actor` (`user|system|llm`), `reason`, `signal_id`, `snapshot`, `timestamp`. **É a fonte de verdade para toda métrica de tempo em estado.**

**RF-D.3 — Undo de ações automáticas.** Toda entrada com `actor IN ('llm','system')` expõe `POST /tasks/{id}/undo/{history_id}`, restaurando status, prazo e `waiting_on` a partir do `snapshot`, e marcando o `Signal` como `discarded` (feedback loop).

**RF-D.4 — Projetos** com progresso derivado: % concluído, tarefas em risco, próximo marco, itens sem movimento.

**RF-D.5 — Marcos (`milestones`) — novo.** Entidade própria vinculada a projeto: nome, data alvo, responsável, status (`planned|at_risk|met|missed|cancelled`), data de conclusão real. Base das métricas de aderência de portfólio. Podem ser criados manualmente ou propostos por `DEADLINE_ANCHOR`.

**RF-D.6 — Portfólios — novo.** Agrupador de projetos acima do nível de projeto, para visão executiva.

**RF-D.7 — Estrutura organizacional leve — novo.**
- `areas`: unidades organizacionais (própria gerência, áreas pares, áreas externas), com hierarquia opcional (`parent_area_id`)
- Stakeholders vinculados a área, enriquecidos por Graph (`department`, `jobTitle`) com **override manual** — o dado do diretório frequentemente está desatualizado
- Flag `is_own_team` para distinguir equipe própria de interfaces externas — **determina o tratamento ético das métricas** (Seção 8)

**RF-D.8 — Stakeholders** resolvidos via Graph People API, com métricas derivadas: pendências, tempo médio de resposta, último touchpoint.

**RF-D.9 — Visões operacionais da UI:**

| Visão | Conteúdo |
|---|---|
| **Hoje** | Foco do dia + capacidade + reuniões + itens vencendo |
| **Triagem** | Propostas e ambiguidades, com evidência e candidatos lado a lado |
| **Aguardando terceiros** | Agrupado por pessoa, com último touchpoint e ação sugerida |
| **Projetos** | Kanban + saúde derivada + marcos |
| **Calendário** | Próximos eventos com pauta sugerida |
| **Timeline da tarefa** | Evidências + updates + reuniões + interações, cronológico |
| **Auditoria de correlação** | Candidatos, scores por recuperador, assessments, regra aplicada, guardrails |
| **Settings** | Filtros, limiares, regras, provedores de IA, **definições de métrica e alertas** |

**RF-D.10 — Busca full-text** em tarefas, descrições e evidências (FTS5 / `tsvector`).

---

### Épico E — Motor de Follow-up

**RF-E.1 — Regras de *staleness* configuráveis:**

| Condição | Ação |
|---|---|
| `waiting_on_others` sem interação > 3 dias | Sugerir nudge |
| `due_date` em ≤ 2 dias e status ≠ `done` | Alerta de prazo |
| `due_date` vencida | Escalar prioridade + alerta |
| `in_progress` sem update > 7 dias | Pedir check-in |
| `blocked` > 5 dias | Sugerir escalação |
| Reunião com o bloqueador em < 48h | Substituir nudge por `bring_to_meeting` |
| Reunião passada com o bloqueador | Resetar relógio; sugerir check-in de resultado |
| **Marco `at_risk` a < 10 dias** | **Novo** — alerta de portfólio |

**RF-E.2 — Rascunho de nudge** pelo LLM (tom `direct|cordial|formal`), com destinatários e citação da thread.

**RF-E.3 — Nenhum envio automático.** `Mail.Send` só após clique explícito. **Não negociável.**

**RF-E.4 — Canais:** `email`, `teams`, `bring_to_meeting`.

**RF-E.5 — Digests:**

| Digest | Conteúdo |
|---|---|
| **Diário** | Triagem pendente · tarefas do dia · **ações automáticas aplicadas (com undo)** · capacidade · pauta das reuniões · itens em risco · **alertas gerenciais abertos** |
| **Semanal** | Concluídas · envelhecidas · saúde dos projetos · taxa de undo · pendências por pessoa · **variação dos KPIs principais + insight narrativo** |

**RF-E.6** Snooze e recorrência de follow-up por tarefa.

---

### Épico I — Camada Analítica e Cockpit Gerencial ★ NOVO

#### I.1 Fundação: snapshots e read model

**RF-I.1 — Snapshot diário append-only.** Job diário (default 23:50, timezone configurável) grava:
- `daily_task_snapshots`: uma linha por tarefa não terminal + tarefas concluídas naquele dia. Campos: status, prioridade, projeto, `waiting_on`, `due_date`, idade, dias no status atual, dias acumulados em cada estado, flags de risco.
- `daily_project_snapshots`: por projeto — contagens por status, marcos em risco, dias sem atividade, health score e **sua decomposição**.

**RF-I.2 — Reconstrutibilidade.** `taskflow backfill-snapshots --from --to` regenera snapshots a partir de `task_status_history`. **Teste obrigatório:** snapshot regenerado deve ser idêntico ao original (propriedade de determinismo).

**RF-I.3 — Idempotência.** Reexecutar o job para a mesma data substitui a partição daquela data, sem duplicar. Chave `UNIQUE(snapshot_date, task_id)`.

#### I.2 Motor de métricas

**RF-I.4 — Registro de métricas como código.** Cada métrica é um objeto declarativo em `domain/metrics/`, com contrato obrigatório:

```python
Metric(
    id="flow.net_flow",
    name="Fluxo líquido",
    question="Estou entregando mais do que entra?",      # obrigatório
    formula="inflow(period) - throughput(period)",
    unit="tarefas/semana",
    grain=["day", "week", "month"],
    dimensions=["project", "area", "demand_origin", "task_type"],
    source="daily_task_snapshots + task_status_history",
    direction="lower_is_better",
    target=0,
    limitations="Considera apenas demanda capturada pelos canais monitorados.",
    coverage_basis="ingestion_coverage",
    expected_action="Se positivo por 3 semanas, renegociar escopo ou redistribuir.",  # obrigatório
    owner="felipe.andrade",
    version=1,
)
```

**RF-I.5 — Definition of Ready de métrica (gate no CI).** O build **falha** se qualquer métrica registrada não tiver: `question`, `formula`, `limitations`, `expected_action`, `owner` e **teste unitário com fixture sintética e resultado esperado**. Isso é o mecanismo estrutural anti-métrica-decorativa.

**RF-I.6 — Cobertura e confiança obrigatórias.** Toda resposta de métrica inclui:

```json
{
  "value": 12.4,
  "coverage": { "level": "high|medium|low", "pct": 0.93, "basis": "..." },
  "sample_size": 148,
  "is_suppressed": false,
  "suppression_reason": null,
  "caveat": "Visão do fluxo que passa pelo gestor.",
  "period_comparison": { "previous": 9.1, "delta_pct": 0.36 }
}
```

Regras: `sample_size < MIN_SAMPLE` (default 5) ⇒ `is_suppressed=true`; cobertura de ingestão < 70% no período ⇒ `coverage.level='low'` e a UI exibe a métrica **esmaecida com aviso**. **Nenhuma métrica é exibida sem esse envelope.**

**RF-I.7 — Cálculo 100% determinístico.** Todo número vem de SQL/código testável. **Proibido** LLM em cálculo, agregação ou classificação numérica. Violação = defeito bloqueante.

**RF-I.8 — Materialização e cache.** `metric_values` armazena séries por (métrica, período, dimensão, versão da definição). Invalidação: mudança de `version` da definição ou novo snapshot. Postgres pode usar *materialized views*; SQLite usa tabelas materializadas por job. Recálculo sob demanda via `POST /metrics/recompute`.

**RF-I.9 — Versionamento de definição.** Alterar fórmula exige incrementar `version`. Séries antigas mantêm a versão com que foram calculadas, e a UI marca a quebra na linha do tempo. **Sem isso, tendência histórica se torna mentira silenciosa.**

#### I.3 Dashboards

**RF-I.10 — Cockpit Executivo** (tela única, ≤ 12 indicadores): net flow, WIP, aging p85, aderência a prazo, pendências em interfaces, projetos em risco, marcos do mês, % tempo em reunião, capacidade da próxima semana, alertas abertos, triagem pendente, saúde do sistema. Cada card: valor, delta vs. período anterior, sparkline, badge de cobertura, drill-down.

**RF-I.11 — Dashboards temáticos** (um por perspectiva do Catálogo, Seção 12):

| # | Dashboard | Pergunta central |
|---|---|---|
| 1 | Demanda & Carga | De onde vem o trabalho e quanto entra? |
| 2 | Fluxo & Tempo | Onde o trabalho fica parado e quanto demora? |
| 3 | Interfaces & Dependências | Quais interfaces geram espera? |
| 4 | Portfólio & Marcos | Quais projetos e marcos estão em risco? |
| 5 | Agenda & Capacidade | Meu tempo comporta o que prometi? |
| 6 | Compromissos & Prazos | Cumpro o que prometo? |
| 7 | Saúde do Sistema | Posso confiar nesses números? |

**RF-I.12 — Filtros globais** persistentes por visão: período (com presets e comparação), portfólio, projeto, área, stakeholder, tipo de tarefa, origem da demanda, prioridade. Estado refletido na URL (compartilhável e recarregável).

**RF-I.13 — Drill-down universal (requisito estruturante).** **Todo** número é clicável e desce até a lista de tarefas que o compõem, e de cada tarefa até a **evidência textual literal na fonte**, com deep link para o e-mail/chat/evento original. Nenhum agregado é folha da navegação.

> Este é o requisito que separa "dashboard em que confio" de "dashboard bonito que ninguém usa em reunião". Quando alguém questionar um número na reunião de resultados, a resposta é três cliques — não "vou verificar".

**RF-I.14 — Dashboards configuráveis.** Grid de widgets com posição, tamanho, métrica, granularidade e visualização. Salvos como `dashboards` + `dashboard_widgets`. Layouts padrão vêm *seedados* e são restauráveis.

**RF-I.15 — Visualizações suportadas:** cartão KPI com delta, série temporal, barras/barras empilhadas, **CFD (cumulative flow diagram)**, **scatter de lead time com percentis**, **histograma de aging por status**, heatmap (dia × hora para agenda), matriz de risco de portfólio, tabela com ordenação e exportação.

**RF-I.16 — Comparação de períodos** em todas as séries: período anterior equivalente, mesmo período do ano anterior (quando houver histórico), média móvel de 4/8/12 semanas.

#### I.4 Alertas

**RF-I.17 — Regras de limiar.** `alert_rules` declarativas: métrica, dimensão, operador, valor, janela de persistência (evita disparo por ruído de um dia), severidade, canal. Ex.: *"net flow > 0 por 3 semanas consecutivas ⇒ high"*.

**RF-I.18 — Detecção de anomalia (estatística simples, explicável).** Desvio > *k*·σ (default 2) contra baseline de 8 semanas, com mínimo de amostra. **Sem ML de caixa preta** — o alerta precisa ser explicável em uma frase, ou não será levado a sério.

**RF-I.19 — Ciclo de vida do alerta:** `open → acknowledged → actioned → resolved | dismissed`, com responsável, prazo e vínculo opcional a `DecisionLog`. Alertas não reconhecidos em N dias são reforçados no digest.

**RF-I.20 — Anti-fadiga de alerta.** Máximo configurável de alertas ativos (default 7); acima disso, agrupamento por tema e sinalização de excesso. Alerta disparado > 3 vezes sem ação sugere **revisão da regra ou do limiar** — o sistema questiona a própria configuração.

#### I.5 Registro de decisões

**RF-I.21 — `DecisionLog`.** O usuário registra decisões/ações vinculadas a métrica, alerta, insight ou projeto: contexto, decisão, ação, responsável, prazo, resultado esperado. Revisão pendente após o prazo ("a decisão surtiu efeito?").

**RF-I.22 — Fechamento do ciclo analítico.** A cada decisão registrada, o sistema captura o valor da métrica no momento e, no vencimento da revisão, apresenta **antes vs. depois**. É o que alimenta O13 e transforma dashboard em instrumento de gestão.

#### I.6 Relatórios e exportação

**RF-I.23 — One-pager gerencial.** Relatório de período (semanal/mensal/trimestral) com: KPIs principais e variação, saúde do portfólio, marcos do período, principais bloqueios por interface (agregado), entregas concluídas, riscos, decisões registradas, e narrativa gerada (Épico J). Exportável em **Markdown, PDF e PPTX**.

**RF-I.24 — Relatórios agendados.** Geração automática e entrega por e-mail no dia/hora configurados. **Sempre em modo rascunho para revisão antes de qualquer envio a terceiros** — coerente com RF-E.3.

**RF-I.25 — Datasets para BI corporativo.** Endpoints read-only de exportação em CSV e Parquet, com datasets estáveis e versionados: `fact_task_daily`, `fact_task_transitions`, `fact_interactions`, `fact_meetings`, `dim_task`, `dim_project`, `dim_stakeholder`, `dim_area`, `dim_date`, `metric_values`.

> Racional: o BI corporativo (Power BI) já existe e tem governança. O TaskFlow não deve competir com ele — deve ser uma **fonte confiável e bem modelada** que possa ser consumida. Datasets contêm apenas dados agregados/estruturados, **nunca corpo de mensagem**.

```gherkin
Cenário: Métrica sem ação esperada quebra o build
  Dado uma métrica registrada sem o campo expected_action
  Quando a suíte de validação do registro executa
  Então o build falha com mensagem apontando a métrica e o campo ausente

Cenário: Amostra insuficiente suprime a métrica
  Dado uma métrica com sample_size = 3 e MIN_SAMPLE = 5
  Quando a métrica é solicitada
  Então is_suppressed = true
  E nenhum valor numérico é retornado
  E suppression_reason indica amostra insuficiente

Cenário: Cobertura baixa degrada a confiança
  Dado que a cobertura de ingestão no período foi de 62%
  Quando qualquer métrica de volume é solicitada
  Então coverage.level = "low"
  E a UI exibe o indicador esmaecido com aviso explícito

Cenário: Drill-down até a evidência
  Dado o cartão "Pendências em interfaces = 14"
  Quando o usuário clica no número
  Então é exibida a lista das 14 tarefas que compõem o valor
  E ao abrir uma tarefa, a evidência textual literal e o deep link para a fonte são exibidos

Cenário: Snapshot regenerado é idêntico
  Dado snapshots existentes para 2026-07-15
  Quando backfill-snapshots é executado para a mesma data
  Então o resultado é idêntico ao original em todos os campos
  E nenhuma linha é duplicada

Cenário: Mudança de fórmula versiona a métrica
  Dado uma métrica na versão 1 com série histórica calculada
  Quando a fórmula é alterada sem incrementar version
  Então o teste de governança de métricas falha

Cenário: LLM não calcula número
  Dado qualquer endpoint de métricas
  Quando a resposta é produzida
  Então nenhuma chamada a LLMProvider ocorreu no caminho de cálculo
```

---

### Épico J — Insights Narrativos Assistidos ★ NOVO

**RF-J.1 — Papel estritamente delimitado do LLM.** O LLM recebe **exclusivamente métricas já calculadas** (valores, deltas, séries, dimensões, alertas ativos, marcos) e produz: síntese do período, hipóteses explicativas, e ações sugeridas com prioridade. **Nunca** recebe tarefas cruas para "analisar" e **nunca** produz número novo.

**RF-J.2 — Guardrail numérico (paralelo ao `evidence_quote`).** Todo número presente no texto gerado é extraído por parser e **validado contra o payload de entrada**. Número não conferido ⇒ o insight é rejeitado, com 1 retry; segunda falha ⇒ narrativa suprimida e apenas os números são exibidos.

> Este é o guardrail que impede o modo de falha mais perigoso do produto: um texto fluente e convincente com um número errado, apresentado em reunião de diretoria.

**RF-J.3 — Schema de saída:**

```json
{
  "period": "2026-07-01/2026-07-31",
  "headline": "string (máx 140 chars)",
  "summary": "string (máx 800 chars)",
  "findings": [{
    "statement": "string",
    "metric_ids": ["flow.net_flow"],
    "referenced_values": [{"metric_id": "...", "value": 12.4, "period": "..."}],
    "confidence": "high|medium|low",
    "is_hypothesis": true
  }],
  "suggested_actions": [{
    "action": "string",
    "rationale": "string",
    "priority": "high|medium|low",
    "related_metric_ids": ["..."],
    "related_task_ids": ["..."]
  }],
  "data_caveats": ["string"]
}
```

**RF-J.4 — Distinção obrigatória entre fato e hipótese.** Correlação nunca é apresentada como causa. Todo item com `is_hypothesis=true` é rotulado visualmente como hipótese a verificar. Se o LLM não distinguir, o item é descartado.

**RF-J.5 — Caveats obrigatórios.** `data_caveats` deve refletir as limitações reais do período (cobertura baixa, amostra pequena, viés de fonte única). Não pode vir vazio quando há cobertura degradada.

**RF-J.6 — Rastreabilidade do insight.** Cada `finding` referencia `metric_ids` e permite drill-down até as tarefas. Insight sem referência a métrica é rejeitado.

**RF-J.7 — Sob demanda e agendado.** Gerado no digest semanal, no one-pager mensal e a pedido. Persistido em `insights` com o payload de entrada — permite auditar depois *"com que números essa conclusão foi tirada?"*.

**RF-J.8 — Sugestões de ação são propostas.** Nenhuma ação sugerida é executada automaticamente. Um clique converte em tarefa ou em `DecisionLog`.

```gherkin
Cenário: Número alucinado rejeita o insight
  Dado um payload de métricas em que net_flow = 12.4
  Quando o LLM gera texto contendo "net flow de 18 tarefas"
  Então o guardrail numérico detecta 18 como valor ausente do payload
  E o insight é rejeitado
  E após um retry falho, apenas os números calculados são exibidos

Cenário: Hipótese é rotulada
  Dado um finding que atribui aumento de lead time a férias de um stakeholder
  Quando o insight é exibido
  Então o item aparece rotulado como hipótese
  E não como conclusão

Cenário: Ação sugerida não é executada
  Dado um insight com ação sugerida "renegociar prazo do Projeto Beta"
  Quando o insight é exibido
  Então nenhuma alteração ocorre em tarefas ou projetos
  E o usuário pode converter a sugestão em tarefa ou decisão com um clique
```

---

### Épico K — Fontes Complementares e Entrada Manual ★ NOVO

Nem tudo que a gerência precisa medir passa por e-mail. Sem este épico, o cockpit fica incompleto e perde credibilidade justamente nos indicadores que a chefia pergunta primeiro.

**RF-K.1 — Entrada manual de indicadores.** Séries de KPI alimentadas manualmente (headcount, orçamento executado, volume operacional, indicadores de segurança, índices contratuais), com: métrica, período, valor, unidade, fonte declarada, autor, timestamp. Histórico de alterações preservado.

**RF-K.2 — Importação CSV/XLSX.** Upload com mapeamento de colunas, validação de tipos, preview antes de confirmar, e relatório de erros por linha. Reimportação idempotente por chave (métrica, período, dimensão).

**RF-K.3 — Distinção visual de origem.** Todo indicador exibe `data_origin`: `derived` (calculado do fluxo), `manual`, `imported`. Métricas mistas exibem a composição. Confundir dado observado com dado declarado é caminho direto para perda de confiança no cockpit.

**RF-K.4 — Lembrete de atualização.** Métrica manual com periodicidade declarada gera lembrete quando vence e é marcada como **desatualizada** no dashboard (não exibida como se fosse atual).

**RF-K.5 — Metas e baselines.** Meta por métrica e período, com origem (`self|management|contractual`). Dashboards exibem realizado vs. meta e projeção simples de tendência linear — explicitamente rotulada como projeção.

**RF-K.6 — Anotações de contexto.** Marcadores em datas específicas ("reorganização da equipe", "férias coletivas", "início do projeto X"), exibidos como linhas verticais nas séries temporais. Sem isso, toda variação vira mistério e a análise de tendência fica ingênua.

```gherkin
Cenário: Métrica manual vencida é sinalizada
  Dado uma métrica manual com periodicidade mensal e último valor de 2 meses atrás
  Quando o dashboard é carregado
  Então a métrica é exibida com marcação de desatualizada
  E o valor antigo não é apresentado como atual

Cenário: Importação idempotente
  Dado um CSV já importado
  Quando o mesmo arquivo é reimportado
  Então nenhum valor é duplicado
  E os valores existentes são atualizados com registro de alteração
```

---

### Épico H — Provedor de LLM (Gemini)

**RF-H.1** Adapter `GeminiProvider` implementando a porta `LLMProvider`, via SDK oficial Google Gen AI (Python).

**RF-H.2 — Dois níveis de modelo:**

| Nível | Uso | Variável | Perfil |
|---|---|---|---|
| `classifier` | Estágio 2 da extração, altíssimo volume | `LLM_MODEL_CLASSIFIER` | Rápido, `thinking_budget=0` |
| `reasoner` | Extração (C) + correlação (G2) + **narrativa (J)** | `LLM_MODEL_REASONER` | Capaz, thinking moderado |

**RF-H.3 — Saída estruturada obrigatória** via `response_mime_type="application/json"` + `response_schema` derivado dos modelos Pydantic. **Não confiar em instrução textual de formato.**

**RF-H.4 — Controle de raciocínio** por caso de uso. Se o modelo não suportar, degrada silenciosamente e loga uma vez.

**RF-H.5 — Cache de contexto** para prompt de sistema e few-shots. Fallback transparente. Registrar `cached_tokens`.

**RF-H.6 — Gestão de chave de API:**
- Origem: `GEMINI_API_KEY` **ou** UI (`Settings → Provedores de IA`)
- Via UI: cifrada em repouso (AES-GCM, chave derivada de `ENCRYPTION_KEY`), em `provider_credentials`
- **Nunca** logada, **nunca** retornada pela API (só máscara `AIza••••••3f2a`), **nunca** em erro ou stack trace
- Botão **"Testar conexão"** → chamada mínima real com modelo, latência e status
- **Validação na inicialização** via `models.list`: confirma existência do `model_id` e suporte a `responseSchema`

**RF-H.7 — Resiliência.** `429 RESOURCE_EXHAUSTED` com backoff exponencial + jitter, honrando `retryDelay`. Circuit breaker. Contadores RPM/TPM/TPD. A 80% do teto diário, sinais de baixa prioridade vão para fila adiada — **narrativa de insight é a primeira a ser adiada**, por ser prescindível.

**RF-H.8 — Segurança de conteúdo.** `safety_settings` explícitos. Bloqueio ⇒ item marcado `blocked_by_safety` e enviado à triagem, **nunca** descartado silenciosamente.

**RF-H.9 — Multi-provedor.** Gemini default; Azure OpenAI, OpenAI, Anthropic, Ollama ativos. **Nenhuma dependência do SDK Google fora de `adapters/llm/gemini/`.**

**RF-H.10 — Governança de dados (atenção).** O tier gratuito da Gemini API tipicamente permite uso de conteúdo para melhoria do serviço; o tier pago, não. **Recomendação forte:** tier pago ou Vertex AI, com validação prévia da Segurança da Informação ENGIE antes de processar e-mail, chat e calendário corporativos. Documentar em `docs/SECURITY.md` e avisar na UI quando a chave for de tier gratuito.

```gherkin
Cenário: Modelo inexistente falha rápido
  Dado LLM_MODEL_REASONER = "gemini-inexistente-9.9"
  Quando a aplicação inicializa
  Então a inicialização falha com erro claro
  E a mensagem lista os modelos disponíveis para a chave
  E a API key não aparece em nenhum log

Cenário: Teto diário adia narrativa antes de operação
  Dado que 80% do DAILY_TOKEN_BUDGET foi consumido
  Quando há geração de insight e correlação de sinais pendentes
  Então a geração de insight é adiada
  E a correlação de sinais continua sendo processada
```

---

## 8. Ética Analítica e Governança de Métricas ★ NOVO

Esta seção é normativa. O agente deve implementá-la como **código**, não como recomendação.

### 8.1 Fronteira fundamental

| Permitido | Proibido |
|---|---|
| Medir o **fluxo de trabalho** (tempo em estado, filas, gargalos, volume) | Medir **produtividade individual** de terceiros |
| Métricas de **interface entre áreas**, agregadas | **Ranking** de pessoas por tempo de resposta |
| Pendências abertas por pessoa **na visão operacional de follow-up** | Pendências por pessoa como **KPI de desempenho** em dashboard |
| Tempo médio de resposta **por área** | Tempo médio de resposta **por indivíduo externo à equipe** |
| Métricas do **próprio usuário** sem restrição | Inferência sobre horário de trabalho, presença ou disponibilidade de terceiros |

### 8.2 Regras implementáveis

**RF-ETH.1 — K-anonimato.** Métrica agregada por área só é exibida com ≥ `MIN_GROUP_SIZE` (default 3) pessoas contribuindo. Abaixo, suprimida com motivo explícito. Impede desanonimização de área com uma pessoa.

**RF-ETH.2 — Sem ranking individual.** É **proibido** por design ordenar pessoas por métrica de desempenho no cockpit. A visão "Aguardando terceiros" é operacional e existe para **você agir** (cobrar, ajudar, desbloquear) — nunca renderizada como ranking, placar ou comparativo.

**RF-ETH.3 — Métricas de pessoa restritas à equipe própria e ao propósito.** Para stakeholders com `is_own_team=true`, indicadores individuais de **carga e bloqueio** são permitidos (finalidade: apoio e redistribuição). Ainda assim, **nenhuma** métrica de "eficiência" ou "velocidade" individual, e nenhuma comparação entre membros.

**RF-ETH.4 — Sem inferência comportamental.** Proibido derivar métrica de horário de envio de mensagens, atividade fora do horário, tempo de resposta noturno, ou qualquer proxy de presença/dedicação. Vale inclusive para o próprio usuário — exceto como indicador de **saúde própria** explicitamente ativado por ele.

**RF-ETH.5 — Aviso de finalidade na UI.** Todo dashboard com dados de terceiros exibe, de forma persistente: *"Visão do fluxo de trabalho que passa por esta gerência. Não constitui avaliação de desempenho individual."*

**RF-ETH.6 — Escopo mínimo de retenção analítica.** Snapshots e `metric_values` contêm apenas dados estruturados e agregáveis — **nunca** corpo de mensagem. Purga conforme `RETENTION_DAYS`, com agregados mensais mantidos por período maior (`ANALYTICS_RETENTION_MONTHS`).

**RF-ETH.7 — Exportação consciente.** Todo relatório exportado carrega no rodapé: período, cobertura, limitações e a nota de finalidade. Sem isso, o número circula descontextualizado — e um número descontextualizado em apresentação corporativa é um passivo, não um ativo.

**RF-ETH.8 — Trilha de acesso.** Log de quem gerou qual relatório e quando (relevante quando/se houver compartilhamento).

### 8.3 Governança de definições

**RF-ETH.9 — Métrica tem dono e ação.** Sem `owner` e `expected_action`, não entra (RF-I.5).

**RF-ETH.10 — Revisão trimestral automática.** O sistema lista métricas sem ação registrada em 90 dias e **propõe sua remoção**. Combate proliferação e a ilusão de controle por quantidade de indicadores.

**RF-ETH.11 — Auditoria de exatidão.** Comando `taskflow audit-metric <id> --period` exibe a query executada, os registros que compõem o número e a soma verificável — para conferência manual contra a realidade (meta O12).

> **Recomendação prática:** antes de usar métricas que envolvam terceiros em qualquer contexto formal (avaliação, reunião de resultados com nomes, reporte à chefia), vale a validação com RH/Compliance/Privacidade da ENGIE. Métrica derivada de comunicação pessoal tem sensibilidade jurídica e cultural distinta de métrica de sistema transacional, mesmo quando os dados são legitimamente acessíveis a você.

---

## 9. Requisitos Não-Funcionais

| ID | Categoria | Requisito |
|---|---|---|
| NF-1 | Performance operacional | Ingestão + extração + correlação de 200 itens em < 8 min; p95 da API < 300 ms (excl. LLM) |
| NF-2 | **Performance analítica** | **p95 de carga de dashboard < 1,5 s com 24 meses de histórico; job de snapshot < 60 s; recálculo completo de métricas < 5 min** |
| NF-3 | Confiabilidade | Jobs idempotentes; retry com backoff; DLQ; nenhuma perda de `deltaLink` em crash |
| NF-4 | **Correção analítica** | **Todo número reconstruível a partir de `task_status_history`; snapshots regeneráveis e idênticos; nenhuma métrica sem teste com fixture** |
| NF-5 | Segurança | Segredos apenas em env vars / keyring / Key Vault. Tokens e API keys cifrados. HTTPS em cloud. Nunca segredo em código, commit ou log |
| NF-6 | Privacidade | `STORE_FULL_BODY=false` por default. Eventos privados nunca ao LLM. **Snapshots e métricas sem corpo de mensagem.** Retenção configurável com purga. Redaction de PII em logs |
| NF-7 | Observabilidade | JSON estruturado (`structlog`), `correlation_id`, métricas Prometheus, health checks, **auditoria de correlação e de cálculo de métricas** |
| NF-8 | Custo | Contador de tokens por estágio; teto diário; pré-filtro; atalho determinístico; context caching; **narrativa adiada antes de operação** |
| NF-9 | Portabilidade | Idêntico em local e cloud; nenhuma dependência proprietária no core. **Métricas funcionam em SQLite e Postgres** (sem SQL exclusivo de um dialeto no domínio) |
| NF-10 | Manutenibilidade | Cobertura ≥ 80% global, ≥ 90% em `domain/`, **100% das métricas com teste**; mypy strict; lint em CI |
| NF-11 | Acessibilidade | WCAG 2.1 AA; navegação por teclado; **gráficos com tabela de dados equivalente e paleta segura para daltonismo** |
| NF-12 | Compliance | LGPD/GDPR; nenhum dado usado para treinar modelos (tier pago); DPIA antes de produção; **Seção 8 implementada como código** |
| NF-13 | Reversibilidade | 100% das ações automáticas revertíveis em um clique |
| NF-14 | **Explicabilidade** | **Todo número tem: fórmula visível, fonte, cobertura e drill-down. Todo alerta é explicável em uma frase** |

---

## 10. Arquitetura

### 10.1 Estilo

**Monolito modular com Arquitetura Hexagonal (Ports & Adapters)** + **CQRS-lite** para a camada analítica: o caminho de escrita (operacional, normalizado, transacional) é separado do caminho de leitura (analítico, desnormalizado, materializado).

```
┌────────────────────────────────────────────────────────────────────┐
│  ADAPTERS DE ENTRADA                                               │
│  REST API (FastAPI) · Web UI (SPA) · CLI (Typer) · Scheduler         │
└──────────────────────────────┬─────────────────────────────────────┘
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│  APPLICATION — Casos de Uso                                        │
│  ── Escrita (operacional) ────────────────────────────────────────  │
│  SyncMailbox · SyncChats · SyncCalendar                              │
│  ExtractSignals · CorrelateSignal · ApplyDecision                    │
│  TriageProposal · TransitionTask · UndoAutoAction                    │
│  EvaluateStaleness · BuildMeetingAgenda · ComputeCapacity            │
│  ── Leitura (analítica) ★ ────────────────────────────────────────  │
│  BuildDailySnapshots · BackfillSnapshots                             │
│  ComputeMetrics · QueryMetric · DrillDownMetric                      │
│  EvaluateAlertRules · DetectAnomalies                                │
│  GenerateInsight · GenerateReport · ExportDataset                    │
│  RegisterDecision · ReviewDecisionOutcome                            │
└──────────────────────────────┬─────────────────────────────────────┘
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│  DOMAIN — puro · zero I/O · zero dependência externa                │
│                                                                     │
│  Entidades:  Task · Project · Milestone · Portfolio · Area           │
│              SourceItem · CalendarEvent · Signal · Stakeholder        │
│              TaskProposal · FollowUp · Alert · Insight · Decision     │
│                                                                     │
│  Políticas:  TaskStateMachine · CorrelationPolicy ★                  │
│              CandidateFusion (RRF) · StalenessPolicy                 │
│              CapacityPolicy · PrivacyRedactionPolicy                 │
│              ConfidenceRouter · DeduplicationPolicy                  │
│              ★ MetricRegistry · MetricComputation                     │
│              ★ CoveragePolicy · SuppressionPolicy (k-anonimato)       │
│              ★ AlertRuleEngine · AnomalyDetector                      │
│              ★ HealthScorePolicy · EthicsGuard                        │
│                                                                     │
│  Ports:      SourceProvider · LLMProvider · EmbeddingProvider         │
│              TaskRepository · SignalRepository · Notifier             │
│              ★ AnalyticsReadModel · SnapshotRepository                │
│              ★ MetricStore · ReportRenderer · DatasetExporter          │
│              Clock · UnitOfWork · Queue                               │
└──────────────────────────────┬─────────────────────────────────────┘
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│  ADAPTERS DE SAÍDA                                                 │
│  GraphMailSource · GraphChatSource · GraphCalendarSource             │
│  GeminiProvider · AzureOpenAIProvider · OllamaProvider               │
│  SQLAlchemyRepository · PgVectorIndex / SqliteVecIndex               │
│  ★ PostgresAnalyticsReadModel / SqliteAnalyticsReadModel             │
│  ★ MarkdownReporter · WeasyPrintPdfReporter · PptxReporter           │
│  ★ CsvExporter · ParquetExporter                                     │
│  GraphMailNotifier · RedisQueue / InProcessQueue                      │
└────────────────────────────────────────────────────────────────────┘
```

★ = novo ou expandido na v1.2. `CorrelationPolicy` e `MetricRegistry` são os dois componentes mais críticos do sistema — ambos determinísticos, ambos no domínio, ambos com cobertura de teste exaustiva.

**Regras de dependência (invioláveis):**
1. `domain/` não importa **nada** de `adapters/` ou `application/`
2. **A camada analítica lê apenas do read model** (snapshots + metric_values + views); **nunca** faz join ad-hoc em tabelas operacionais dentro de handler de dashboard
3. **Nenhum cálculo numérico no frontend** — a UI renderiza o que a API computou. Métrica calculada em duas camadas divergirá, e a divergência será descoberta na reunião errada

### 10.2 Estrutura de diretórios

```
taskflow/
├── apps/
│   ├── api/                       # FastAPI: routers, DTOs, middlewares
│   ├── worker/                    # jobs agendados e consumers
│   └── cli/                       # sync, extract, correlate, snapshot,
│                                  # backfill-snapshots, recompute-metrics,
│                                  # audit-metric, report, eval, migrate
├── src/taskflow/
│   ├── domain/
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── policies/
│   │   │   ├── task_state_machine.py
│   │   │   ├── correlation_policy.py
│   │   │   ├── candidate_fusion.py
│   │   │   ├── staleness_policy.py
│   │   │   ├── capacity_policy.py
│   │   │   ├── privacy_redaction.py
│   │   │   ├── coverage_policy.py          ★
│   │   │   ├── suppression_policy.py       ★ k-anonimato
│   │   │   ├── health_score_policy.py      ★
│   │   │   ├── alert_rule_engine.py        ★
│   │   │   ├── anomaly_detector.py         ★
│   │   │   └── ethics_guard.py             ★
│   │   ├── metrics/                        ★ registro de métricas
│   │   │   ├── registry.py
│   │   │   ├── definitions/                # um módulo por perspectiva
│   │   │   │   ├── p1_demand.py
│   │   │   │   ├── p2_flow.py
│   │   │   │   ├── p3_interfaces.py
│   │   │   │   ├── p4_portfolio.py
│   │   │   │   ├── p5_calendar.py
│   │   │   │   ├── p6_commitments.py
│   │   │   │   └── p7_system.py
│   │   │   └── validators.py               # gate do Definition of Ready
│   │   └── ports/
│   ├── application/
│   │   ├── use_cases/
│   │   ├── retrievers/                     # R1..R6
│   │   ├── analytics/                      ★ snapshot, compute, drilldown
│   │   ├── reporting/                      ★ one-pager, agendamento
│   │   └── dto/
│   ├── adapters/
│   │   ├── graph/
│   │   ├── llm/{gemini,azure_openai,openai,anthropic,ollama}/
│   │   ├── persistence/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   ├── analytics/                  ★ read model, views, SQL por dialeto
│   │   │   └── migrations/
│   │   ├── reporting/                      ★ markdown, pdf, pptx
│   │   ├── export/                         ★ csv, parquet
│   │   ├── queue/
│   │   └── notification/
│   ├── prompts/                            # versionados, com changelog
│   └── config/
├── web/
│   ├── src/features/
│   │   ├── triage/ tasks/ calendar/ projects/
│   │   └── cockpit/                        ★ dashboards, widgets, drilldown
│   └── src/components/charts/              ★ biblioteca de visualizações
├── tests/
│   ├── unit/                               # domain, sem I/O
│   ├── integration/                        # repos e adapters
│   ├── contract/                           # Graph em cassettes
│   ├── metrics/                            ★ fixture sintética por métrica
│   ├── evaluation/                         # datasets dourados de LLM
│   └── e2e/
├── infra/{docker,compose,terraform}/
├── docs/
├── AGENTS.md
└── pyproject.toml
```

### 10.3 Stack tecnológica

| Camada | Escolha | Justificativa |
|---|---|---|
| Linguagem | Python 3.12+ | Ecossistema de LLM/Graph/analítica maduro |
| API | FastAPI + Pydantic v2 | Validação, OpenAPI, async; schemas reaproveitados no `responseSchema` |
| ORM | SQLAlchemy 2.0 + Alembic | Portabilidade SQLite ↔ Postgres |
| DB local | SQLite + FTS5 + sqlite-vec | Zero infra; snapshots e métricas em tabelas materializadas |
| DB cloud | PostgreSQL 16 + pgvector | JSONB, `tsvector`, embeddings, **materialized views**, particionamento por data |
| **Analítica** | **SQL puro + SQLAlchemy Core** | **Transparente, auditável, portável. Sem engine de BI embarcada** |
| **Dataframes** | **Polars** (agregações complexas, export Parquet) | Rápido, memória previsível, API explícita |
| Fila | APScheduler (local) · ARQ + Redis (cloud) | Porta única, adapter trocável |
| Frontend | React 18 + TS + Vite + Tailwind + shadcn/ui + TanStack Query | Alta produtividade com agentes de código |
| **Gráficos** | **Recharts** (padrão) + **visx** para CFD/scatter | Composável, acessível, sem licença comercial |
| **Relatórios** | **Jinja2 → Markdown → WeasyPrint (PDF)** · **python-pptx** | Sem dependência de Office instalado |
| **Ingestão Local** | **Outlook MAPI/COM (`pywin32`)** | **Nativa, local e em tempo real sem dependência de admin Azure/Graph API** |
| Auth MS | MSAL Python / COM MAPI Local | Integração local MAPI (Outlook/Teams) + suporte MSAL Graph API para cloud |
| LLM | **Gemini (default)** · **ChatGPT Assinatura (OAuth PKCE)** · **M365 Copilot Corporativo (Sessão Web Edge)** · Azure OpenAI · OpenAI · Ollama | Structured output nativo; multi-provedor por porta desacoplada (`LLMProvider`) com suporte a franquia de tokens e autorização sem TI |
| Embeddings | Gemini (768d) ou local (`bge-m3`) | Recuperador R6 e dedup |
| Testes | pytest, pytest-asyncio, testcontainers, respx, Playwright | Pirâmide completa |
| Qualidade | ruff, mypy (strict), pre-commit | Padronização automatizada |
| Empacotamento | uv, Docker multi-stage, distroless | Build rápido, imagem enxuta |
| CI/CD | GitHub Actions ou Azure DevOps | lint → type → test → **metrics-gate** → eval → build → scan → deploy |

> **Decisão deliberada:** não embarcar Superset, Metabase ou Cube.js. O catálogo é pequeno e específico, e a exigência de drill-down até evidência textual e envelope de cobertura obrigatório é mais fácil de garantir em código próprio do que de encaixar numa ferramenta genérica. Para consumo corporativo amplo, a resposta é o export para Power BI (RF-I.25), não uma segunda ferramenta de BI.

---

## 11. Modelo de Dados

DDL de referência em dialeto neutro. Implementar via SQLAlchemy + Alembic, compatível com SQLite e Postgres.

```sql
-- ═══════════════════════════════════════════════════════════════════
--  INGESTÃO
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE source_items (
    id                UUID PRIMARY KEY,
    kind              TEXT NOT NULL,        -- 'email'|'teams_chat'|'calendar_event'
    channel           TEXT NOT NULL,
    external_id       TEXT NOT NULL,
    conversation_id   TEXT,                 -- threadId|chatId|seriesMasterId
    revision_hash     TEXT NOT NULL,
    author_email      TEXT,
    author_name       TEXT,
    participants      JSON,
    title             TEXT,
    body_preview      TEXT,
    body_full         TEXT,                 -- só se STORE_FULL_BODY=true
    occurred_at       TIMESTAMPTZ NOT NULL,
    has_attachments   BOOLEAN DEFAULT FALSE,
    importance        TEXT,
    web_link          TEXT,
    is_redacted       BOOLEAN DEFAULT FALSE,
    processing_status TEXT NOT NULL,        -- pending|filtered|extracted|correlated|failed
    filtered_reason   TEXT,
    blocked_by_safety BOOLEAN DEFAULT FALSE,
    processed_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT now(),
    UNIQUE (kind, external_id, revision_hash)
);
CREATE INDEX ix_source_conv   ON source_items(conversation_id);
CREATE INDEX ix_source_status ON source_items(processing_status, occurred_at DESC);
CREATE INDEX ix_source_kind   ON source_items(kind, occurred_at DESC);

CREATE TABLE calendar_events (
    source_item_id       UUID PRIMARY KEY REFERENCES source_items(id) ON DELETE CASCADE,
    graph_event_id       TEXT NOT NULL,
    series_master_id     TEXT,
    instance_type        TEXT,
    body_hash            TEXT,
    starts_at            TIMESTAMPTZ NOT NULL,
    ends_at              TIMESTAMPTZ NOT NULL,
    duration_minutes     INT,
    is_all_day           BOOLEAN DEFAULT FALSE,
    timezone             TEXT,
    location             TEXT,
    is_online            BOOLEAN DEFAULT FALSE,
    join_url             TEXT,
    linked_chat_id       TEXT,
    organizer_email      TEXT,
    my_response          TEXT,
    show_as              TEXT,
    sensitivity          TEXT,
    is_cancelled         BOOLEAN DEFAULT FALSE,
    recurrence_rule      JSON,
    attendee_count       INT,
    categories           JSON,
    -- classificação analítica (RF-F.9)
    meeting_class        TEXT,   -- 1:1|team|project|governance|external|personal_block
    has_agenda           BOOLEAN DEFAULT FALSE,
    produced_action_items BOOLEAN DEFAULT FALSE,
    is_recurring         BOOLEAN DEFAULT FALSE,
    attributed_project_id UUID,
    attributed_area_id    UUID
);
CREATE INDEX ix_cal_window ON calendar_events(starts_at, ends_at);
CREATE INDEX ix_cal_series ON calendar_events(series_master_id);
CREATE INDEX ix_cal_join   ON calendar_events(join_url);
CREATE INDEX ix_cal_class  ON calendar_events(meeting_class, starts_at);

CREATE TABLE sync_state (
    id                   UUID PRIMARY KEY,
    channel              TEXT NOT NULL,     -- mail|chat|calendar
    resource_id          TEXT NOT NULL,
    delta_link           TEXT,
    window_start         TIMESTAMPTZ,
    window_end           TIMESTAMPTZ,
    last_synced_at       TIMESTAMPTZ,
    last_error           TEXT,
    consecutive_failures INT DEFAULT 0,
    state                TEXT DEFAULT 'healthy',
    UNIQUE (channel, resource_id)
);

-- Cobertura de ingestão (RF-B.7) — base do indicador de confiança
CREATE TABLE ingestion_runs (
    id              UUID PRIMARY KEY,
    channel         TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ,
    items_seen      INT DEFAULT 0,
    items_filtered  INT DEFAULT 0,
    items_extracted INT DEFAULT 0,
    items_failed    INT DEFAULT 0,
    success         BOOLEAN,
    error           TEXT,
    correlation_id  TEXT
);
CREATE INDEX ix_ingestion_runs ON ingestion_runs(channel, started_at DESC);

-- ═══════════════════════════════════════════════════════════════════
--  SINAIS E CORRELAÇÃO
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE signals (
    id                UUID PRIMARY KEY,
    source_item_id    UUID NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
    signal_type       TEXT NOT NULL,
    payload           JSON NOT NULL,
    evidence_quote    TEXT,
    extraction_conf   NUMERIC,
    demand_origin     TEXT,      -- internal_area|peer_area|management|external|self
    state             TEXT NOT NULL,  -- pending_correlation|resolved|expired|discarded
    decision_kind     TEXT,
    decision_conf     NUMERIC,
    resolved_task_id  UUID REFERENCES tasks(id) ON DELETE SET NULL,
    retry_count       INT DEFAULT 0,
    embedding         VECTOR(768),
    embedding_model   TEXT,
    created_at        TIMESTAMPTZ DEFAULT now(),
    resolved_at       TIMESTAMPTZ
);
CREATE INDEX ix_signals_state ON signals(state, created_at);
CREATE INDEX ix_signals_type  ON signals(signal_type);

CREATE TABLE correlation_runs (
    id                UUID PRIMARY KEY,
    signal_id         UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    candidates        JSON NOT NULL,
    llm_assessments   JSON,
    final_decision    TEXT NOT NULL,
    final_confidence  NUMERIC,
    applied           BOOLEAN NOT NULL,
    routed_to_triage  BOOLEAN NOT NULL,
    policy_rule_id    TEXT NOT NULL,
    guardrail_blocks  JSON,
    skipped_llm       BOOLEAN DEFAULT FALSE,
    latency_ms        INT,
    correlation_id    TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_corr_signal ON correlation_runs(signal_id);

-- ═══════════════════════════════════════════════════════════════════
--  ESTRUTURA ORGANIZACIONAL  ★ NOVO
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE areas (
    id             UUID PRIMARY KEY,
    name           TEXT NOT NULL,
    short_name     TEXT,
    parent_area_id UUID REFERENCES areas(id) ON DELETE SET NULL,
    kind           TEXT NOT NULL,   -- own_team|peer_area|management|external|vendor
    is_own_team    BOOLEAN DEFAULT FALSE,   -- ★ define tratamento ético (Seção 8)
    created_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE portfolios (
    id          UUID PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    owner_id    UUID REFERENCES stakeholders(id),
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE stakeholders (
    id                 UUID PRIMARY KEY,
    email              TEXT UNIQUE,
    display_name       TEXT NOT NULL,
    job_title          TEXT,
    department         TEXT,                 -- do Graph
    area_id            UUID REFERENCES areas(id) ON DELETE SET NULL,
    area_source        TEXT,                 -- graph|manual  (override manual)
    graph_user_id      TEXT,
    avg_response_hours NUMERIC,
    is_active          BOOLEAN DEFAULT TRUE,
    created_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_stakeholder_area ON stakeholders(area_id);

-- ═══════════════════════════════════════════════════════════════════
--  DOMÍNIO DE TAREFAS
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE projects (
    id            UUID PRIMARY KEY,
    portfolio_id  UUID REFERENCES portfolios(id) ON DELETE SET NULL,
    name          TEXT NOT NULL,
    description   TEXT,
    status        TEXT NOT NULL,      -- active|on_hold|completed|cancelled
    owner_id      UUID REFERENCES stakeholders(id),
    area_id       UUID REFERENCES areas(id),
    start_date    DATE,
    target_date   DATE,
    color         TEXT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE milestones (            -- ★ NOVO
    id             UUID PRIMARY KEY,
    project_id     UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    target_date    DATE NOT NULL,
    owner_id       UUID REFERENCES stakeholders(id),
    status         TEXT NOT NULL,    -- planned|at_risk|met|missed|cancelled
    completed_at   DATE,
    source         TEXT NOT NULL,    -- manual|derived_from_signal
    signal_id      UUID REFERENCES signals(id),
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_milestones_target ON milestones(target_date, status);

CREATE TABLE tasks (
    id                       UUID PRIMARY KEY,
    title                    TEXT NOT NULL,
    description              TEXT,
    status                   TEXT NOT NULL,
    priority                 TEXT NOT NULL DEFAULT 'medium',
    task_type                TEXT,
    demand_origin            TEXT,            -- ★ análise de origem da demanda
    requester_id             UUID REFERENCES stakeholders(id),
    project_id               UUID REFERENCES projects(id) ON DELETE SET NULL,
    milestone_id             UUID REFERENCES milestones(id) ON DELETE SET NULL,
    parent_task_id           UUID REFERENCES tasks(id) ON DELETE CASCADE,
    waiting_on_id            UUID REFERENCES stakeholders(id),
    due_date                 DATE,
    due_date_source          TEXT,
    original_due_date        DATE,            -- ★ 1ª data prometida (slip analysis)
    due_date_change_count    INT DEFAULT 0,   -- ★ replanejamentos
    estimated_effort_minutes INT,
    snooze_until             TIMESTAMPTZ,
    auto_created             BOOLEAN DEFAULT FALSE,
    llm_confidence           NUMERIC,
    started_at               TIMESTAMPTZ,     -- ★ 1ª entrada em in_progress
    last_activity_at         TIMESTAMPTZ NOT NULL,
    last_interaction_at      TIMESTAMPTZ,
    embedding                VECTOR(768),
    embedding_model          TEXT,
    completed_at             TIMESTAMPTZ,
    created_at               TIMESTAMPTZ DEFAULT now(),
    updated_at               TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_tasks_status_activity ON tasks(status, last_interaction_at);
CREATE INDEX ix_tasks_due ON tasks(due_date) WHERE status NOT IN ('done','cancelled');
CREATE INDEX ix_tasks_waiting ON tasks(waiting_on_id) WHERE status = 'waiting_on_others';
CREATE INDEX ix_tasks_project ON tasks(project_id, status);

CREATE TABLE task_evidence (
    id             UUID PRIMARY KEY,
    task_id        UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    source_item_id UUID NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
    signal_id      UUID REFERENCES signals(id) ON DELETE SET NULL,
    quote          TEXT NOT NULL,
    role           TEXT NOT NULL,   -- origin|update|completion_signal|context|meeting_agenda
    created_at     TIMESTAMPTZ DEFAULT now(),
    UNIQUE (task_id, source_item_id, quote)
);

CREATE TABLE task_status_history (   -- fonte de verdade para métricas de tempo
    id           UUID PRIMARY KEY,
    task_id      UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    from_status  TEXT,
    to_status    TEXT NOT NULL,
    actor        TEXT NOT NULL,     -- user|system|llm
    reason       TEXT,
    signal_id    UUID REFERENCES signals(id),
    is_undone    BOOLEAN DEFAULT FALSE,
    undone_at    TIMESTAMPTZ,
    snapshot     JSON,              -- estado anterior completo, p/ undo
    created_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_history_task_time ON task_status_history(task_id, created_at);

CREATE TABLE task_updates (
    id             UUID PRIMARY KEY,
    task_id        UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    content        TEXT NOT NULL,
    source         TEXT NOT NULL,   -- manual|extracted
    source_item_id UUID REFERENCES source_items(id),
    signal_id      UUID REFERENCES signals(id),
    created_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE task_stakeholders (
    task_id        UUID REFERENCES tasks(id) ON DELETE CASCADE,
    stakeholder_id UUID REFERENCES stakeholders(id) ON DELETE CASCADE,
    role           TEXT NOT NULL,   -- requester|assignee|informed
    PRIMARY KEY (task_id, stakeholder_id, role)
);

CREATE TABLE task_meeting_links (
    task_id           UUID REFERENCES tasks(id) ON DELETE CASCADE,
    source_item_id    UUID REFERENCES source_items(id) ON DELETE CASCADE,
    link_type         TEXT NOT NULL,   -- prep_for|discussed_in|forum_for|deadline_anchor
    confidence        NUMERIC,
    is_user_confirmed BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (task_id, source_item_id, link_type)
);

CREATE TABLE stakeholder_interactions (
    id               UUID PRIMARY KEY,
    stakeholder_id   UUID NOT NULL REFERENCES stakeholders(id) ON DELETE CASCADE,
    task_id          UUID REFERENCES tasks(id) ON DELETE CASCADE,
    source_item_id   UUID REFERENCES source_items(id) ON DELETE SET NULL,
    interaction_type TEXT NOT NULL,  -- email_in|email_out|chat|meeting_held|nudge_sent
    occurred_at      TIMESTAMPTZ NOT NULL,
    created_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_interactions ON stakeholder_interactions(stakeholder_id, occurred_at DESC);
CREATE INDEX ix_interactions_task ON stakeholder_interactions(task_id, occurred_at DESC);

-- ═══════════════════════════════════════════════════════════════════
--  TRIAGEM E FOLLOW-UP
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE task_proposals (
    id                UUID PRIMARY KEY,
    signal_id         UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    proposal_kind     TEXT NOT NULL,  -- new_task|update|transition|merge|split|disambiguate
    payload           JSON NOT NULL,
    candidate_tasks   JSON,
    confidence        NUMERIC NOT NULL,
    status            TEXT NOT NULL,  -- pending|accepted|rejected|merged|expired
    resolved_task_id  UUID REFERENCES tasks(id),
    rejection_reason  TEXT,
    user_edits        JSON,
    created_at        TIMESTAMPTZ DEFAULT now(),
    resolved_at       TIMESTAMPTZ
);
CREATE INDEX ix_proposals_status ON task_proposals(status, created_at DESC);

CREATE TABLE follow_ups (
    id                UUID PRIMARY KEY,
    task_id           UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    rule_id           TEXT NOT NULL,
    channel           TEXT NOT NULL DEFAULT 'email',  -- email|teams|bring_to_meeting
    target_meeting_id UUID REFERENCES source_items(id),
    suggested_at      TIMESTAMPTZ DEFAULT now(),
    draft_subject     TEXT,
    draft_body        TEXT,
    status            TEXT NOT NULL,  -- suggested|sent|dismissed|snoozed
    sent_at           TIMESTAMPTZ
);

-- ═══════════════════════════════════════════════════════════════════
--  READ MODEL ANALÍTICO  ★ NOVO
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE daily_task_snapshots (
    snapshot_date        DATE NOT NULL,
    task_id              UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    status               TEXT NOT NULL,
    priority             TEXT,
    task_type            TEXT,
    demand_origin        TEXT,
    project_id           UUID,
    portfolio_id         UUID,
    milestone_id         UUID,
    requester_area_id    UUID,
    waiting_on_id        UUID,
    waiting_on_area_id   UUID,
    due_date             DATE,
    original_due_date    DATE,
    age_days             INT NOT NULL,          -- desde created_at
    days_in_status       INT NOT NULL,
    cum_days_open        INT,
    cum_days_in_progress INT,
    cum_days_waiting     INT,
    cum_days_blocked     INT,
    is_overdue           BOOLEAN DEFAULT FALSE,
    is_at_risk           BOOLEAN DEFAULT FALSE,
    is_stale             BOOLEAN DEFAULT FALSE,
    completed_today      BOOLEAN DEFAULT FALSE,
    created_today        BOOLEAN DEFAULT FALSE,
    estimated_effort_minutes INT,
    PRIMARY KEY (snapshot_date, task_id)
);
CREATE INDEX ix_dts_date    ON daily_task_snapshots(snapshot_date);
CREATE INDEX ix_dts_project ON daily_task_snapshots(project_id, snapshot_date);
CREATE INDEX ix_dts_status  ON daily_task_snapshots(status, snapshot_date);
-- Postgres: particionar por RANGE(snapshot_date), mensal

CREATE TABLE daily_project_snapshots (
    snapshot_date        DATE NOT NULL,
    project_id           UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    portfolio_id         UUID,
    status               TEXT NOT NULL,
    tasks_total          INT,
    tasks_open           INT,
    tasks_in_progress    INT,
    tasks_waiting        INT,
    tasks_blocked        INT,
    tasks_done           INT,
    tasks_overdue        INT,
    milestones_total     INT,
    milestones_at_risk   INT,
    milestones_missed    INT,
    days_since_activity  INT,
    oldest_blocked_days  INT,
    health_score         NUMERIC,        -- 0..100
    health_components    JSON,           -- ★ decomposição explicável
    PRIMARY KEY (snapshot_date, project_id)
);

CREATE TABLE daily_calendar_snapshots (
    snapshot_date          DATE NOT NULL PRIMARY KEY,
    total_meeting_minutes  INT,
    meeting_count          INT,
    recurring_count        INT,
    external_count         INT,
    with_agenda_count      INT,
    produced_actions_count INT,
    largest_free_block_min INT,
    free_blocks_ge_90min   INT,
    available_minutes      INT,
    utilization_pct        NUMERIC,
    declined_count         INT,
    minutes_by_class       JSON,
    minutes_by_project     JSON
);

-- Registro de definições (lineage) — espelho persistido do código
CREATE TABLE metric_definitions (
    id                TEXT NOT NULL,       -- 'flow.net_flow'
    version           INT NOT NULL,
    name              TEXT NOT NULL,
    perspective       TEXT NOT NULL,
    question          TEXT NOT NULL,
    formula           TEXT NOT NULL,
    unit              TEXT,
    direction         TEXT,                -- higher_is_better|lower_is_better|neutral
    grain             JSON NOT NULL,
    dimensions        JSON NOT NULL,
    source            TEXT NOT NULL,
    limitations       TEXT NOT NULL,
    coverage_basis    TEXT,
    expected_action   TEXT NOT NULL,
    owner             TEXT NOT NULL,
    data_origin       TEXT NOT NULL,       -- derived|manual|imported|mixed
    is_active         BOOLEAN DEFAULT TRUE,
    effective_from    DATE NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (id, version)
);

CREATE TABLE metric_values (
    id                UUID PRIMARY KEY,
    metric_id         TEXT NOT NULL,
    metric_version    INT NOT NULL,
    grain             TEXT NOT NULL,       -- day|week|month|quarter
    period_start      DATE NOT NULL,
    period_end        DATE NOT NULL,
    dimension_key     TEXT NOT NULL DEFAULT '_total',  -- ex: 'project:uuid'
    dimension_value   TEXT,
    value             NUMERIC,
    numerator         NUMERIC,
    denominator       NUMERIC,
    sample_size       INT,
    coverage_pct      NUMERIC,
    coverage_level    TEXT,                -- high|medium|low
    is_suppressed     BOOLEAN DEFAULT FALSE,
    suppression_reason TEXT,
    computed_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE (metric_id, metric_version, grain, period_start, dimension_key)
);
CREATE INDEX ix_mv_lookup ON metric_values(metric_id, grain, period_start DESC);

CREATE TABLE metric_runs (
    id             UUID PRIMARY KEY,
    started_at     TIMESTAMPTZ NOT NULL,
    finished_at    TIMESTAMPTZ,
    metrics_count  INT,
    values_written INT,
    duration_ms    INT,
    success        BOOLEAN,
    error          TEXT,
    correlation_id TEXT
);

-- Entradas manuais e importadas (Épico K)
CREATE TABLE manual_metric_entries (
    id              UUID PRIMARY KEY,
    metric_id       TEXT NOT NULL,
    grain           TEXT NOT NULL,
    period_start    DATE NOT NULL,
    dimension_key   TEXT DEFAULT '_total',
    value           NUMERIC NOT NULL,
    unit            TEXT,
    declared_source TEXT NOT NULL,
    entered_by      TEXT NOT NULL,
    import_batch_id UUID,
    note            TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    superseded_by   UUID REFERENCES manual_metric_entries(id),
    UNIQUE (metric_id, grain, period_start, dimension_key, superseded_by)
);

CREATE TABLE metric_targets (
    id           UUID PRIMARY KEY,
    metric_id    TEXT NOT NULL,
    grain        TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end   DATE,
    target_value NUMERIC NOT NULL,
    origin       TEXT NOT NULL,      -- self|management|contractual
    note         TEXT,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE context_annotations (   -- marcadores nas séries temporais
    id          UUID PRIMARY KEY,
    occurred_on DATE NOT NUL
```sql
-- ═══════════════════════════════════════════════════════════════════
--  READ MODEL ANALÍTICO (cont.)  ★ NOVO
-- ═══════════════════════════════════════════════════════════════════

-- Marcadores de contexto nas séries temporais (RF-K.6)
CREATE TABLE context_annotations (
    id          UUID PRIMARY KEY,
    occurred_on DATE NOT NULL,
    ends_on     DATE,                    -- períodos (ex.: férias coletivas)
    title       TEXT NOT NULL,
    description TEXT,
    kind        TEXT NOT NULL,           -- reorg|vacation|project_start|project_end
                                         -- |incident|policy_change|other
    scope       TEXT NOT NULL DEFAULT 'global',  -- global|portfolio|project|area
    scope_id    UUID,
    created_by  TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_annotations_date ON context_annotations(occurred_on);

-- ═══════════════════════════════════════════════════════════════════
--  DASHBOARDS  ★ NOVO
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE dashboards (
    id           UUID PRIMARY KEY,
    slug         TEXT NOT NULL UNIQUE,   -- 'executive'|'flow'|'interfaces'|...
    name         TEXT NOT NULL,
    description  TEXT,
    perspective  TEXT,                   -- p1..p7|executive|custom
    is_default   BOOLEAN DEFAULT FALSE,  -- seedado, restaurável
    default_filters JSON,
    sort_order   INT DEFAULT 0,
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE dashboard_widgets (
    id             UUID PRIMARY KEY,
    dashboard_id   UUID NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    metric_id      TEXT,                 -- null p/ widgets compostos
    metric_ids     JSON,                 -- p/ séries múltiplas
    widget_type    TEXT NOT NULL,        -- kpi_card|time_series|bar|stacked_bar
                                         -- |cfd|scatter_leadtime|histogram_aging
                                         -- |heatmap|risk_matrix|table|annotation_list
    title          TEXT,
    grain          TEXT,                 -- day|week|month|quarter
    dimension      TEXT,                 -- eixo de quebra
    comparison     TEXT,                 -- previous_period|year_ago|moving_avg_4|none
    grid_x         INT NOT NULL,
    grid_y         INT NOT NULL,
    grid_w         INT NOT NULL,
    grid_h         INT NOT NULL,
    config         JSON,                 -- limites de eixo, cores, percentis
    created_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_widgets_dashboard ON dashboard_widgets(dashboard_id, grid_y, grid_x);

CREATE TABLE saved_views (               -- filtros salvos e compartilháveis
    id           UUID PRIMARY KEY,
    dashboard_id UUID REFERENCES dashboards(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    filters      JSON NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════════════
--  ALERTAS  ★ NOVO
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE alert_rules (
    id                UUID PRIMARY KEY,
    rule_key          TEXT NOT NULL UNIQUE,
    name              TEXT NOT NULL,
    kind              TEXT NOT NULL,     -- threshold|anomaly|staleness|milestone
    metric_id         TEXT,
    dimension_key     TEXT,
    grain             TEXT,
    operator          TEXT,              -- gt|gte|lt|lte|eq|ne
    threshold_value   NUMERIC,
    persistence_periods INT DEFAULT 1,   -- evita disparo por ruído de 1 dia
    anomaly_sigma     NUMERIC,           -- p/ kind=anomaly
    baseline_periods  INT DEFAULT 8,
    severity          TEXT NOT NULL,     -- info|medium|high|critical
    channels          JSON,              -- ['ui','digest','email']
    is_active         BOOLEAN DEFAULT TRUE,
    explanation_template TEXT NOT NULL,  -- ★ alerta explicável em 1 frase
    suggested_action  TEXT,
    fired_count       INT DEFAULT 0,
    actioned_count    INT DEFAULT 0,     -- ★ base p/ auto-revisão da regra
    created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE alerts (
    id               UUID PRIMARY KEY,
    rule_id          UUID NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    metric_id        TEXT,
    dimension_key    TEXT,
    period_start     DATE,
    triggered_value  NUMERIC,
    baseline_value   NUMERIC,
    deviation        NUMERIC,
    severity         TEXT NOT NULL,
    explanation      TEXT NOT NULL,      -- renderizado do template
    status           TEXT NOT NULL,      -- open|acknowledged|actioned|resolved|dismissed
    acknowledged_at  TIMESTAMPTZ,
    resolved_at      TIMESTAMPTZ,
    dismissed_reason TEXT,
    owner            TEXT,
    due_date         DATE,
    decision_id      UUID,               -- FK lógica p/ decision_log
    drill_down_query JSON,               -- ★ payload p/ reproduzir a lista de origem
    created_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_alerts_status ON alerts(status, severity, created_at DESC);

-- ═══════════════════════════════════════════════════════════════════
--  INSIGHTS E DECISÕES  ★ NOVO
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE insights (
    id                 UUID PRIMARY KEY,
    scope              TEXT NOT NULL,    -- weekly|monthly|quarterly|on_demand
    period_start       DATE NOT NULL,
    period_end         DATE NOT NULL,
    filters            JSON,
    input_payload      JSON NOT NULL,    -- ★ métricas exatas enviadas ao LLM
    headline           TEXT,
    summary            TEXT,
    findings           JSON,             -- [{statement, metric_ids, values, is_hypothesis}]
    suggested_actions  JSON,
    data_caveats       JSON,
    numeric_guard_passed BOOLEAN NOT NULL,
    guard_failures     JSON,             -- números rejeitados, se houver
    retry_count        INT DEFAULT 0,
    is_suppressed      BOOLEAN DEFAULT FALSE,
    model              TEXT,
    correlation_id     TEXT,
    created_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_insights_period ON insights(scope, period_start DESC);

CREATE TABLE decision_log (
    id                 UUID PRIMARY KEY,
    title              TEXT NOT NULL,
    context            TEXT NOT NULL,
    decision           TEXT NOT NULL,
    action             TEXT,
    owner              TEXT,
    due_date           DATE,
    expected_outcome   TEXT,
    -- vínculos
    metric_id          TEXT,
    metric_snapshot    JSON,             -- ★ valor no momento da decisão
    alert_id           UUID REFERENCES alerts(id) ON DELETE SET NULL,
    insight_id         UUID REFERENCES insights(id) ON DELETE SET NULL,
    project_id         UUID REFERENCES projects(id) ON DELETE SET NULL,
    created_task_ids   JSON,
    -- revisão
    review_due_date    DATE,
    review_status      TEXT DEFAULT 'pending',  -- pending|reviewed|skipped
    reviewed_at        TIMESTAMPTZ,
    outcome_assessment TEXT,             -- worked|partial|no_effect|worsened
    outcome_metric_snapshot JSON,        -- ★ valor na revisão → antes/depois
    outcome_note       TEXT,
    created_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_decisions_review ON decision_log(review_status, review_due_date);

-- ═══════════════════════════════════════════════════════════════════
--  RELATÓRIOS  ★ NOVO
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE report_templates (
    id           UUID PRIMARY KEY,
    slug         TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    scope        TEXT NOT NULL,          -- weekly|monthly|quarterly|custom
    sections     JSON NOT NULL,          -- ordem e configuração das seções
    include_insight BOOLEAN DEFAULT TRUE,
    formats      JSON NOT NULL,          -- ['md','pdf','pptx']
    schedule_cron TEXT,
    recipients   JSON,                   -- rascunho apenas (RF-I.24)
    is_active    BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE report_runs (
    id            UUID PRIMARY KEY,
    template_id   UUID REFERENCES report_templates(id) ON DELETE SET NULL,
    period_start  DATE NOT NULL,
    period_end    DATE NOT NULL,
    filters       JSON,
    insight_id    UUID REFERENCES insights(id),
    coverage_pct  NUMERIC,
    status        TEXT NOT NULL,         -- draft|reviewed|exported|sent
    artifacts     JSON,                  -- [{format, path, size, checksum}]
    generated_by  TEXT,
    generated_at  TIMESTAMPTZ DEFAULT now(),
    exported_at   TIMESTAMPTZ
);
CREATE INDEX ix_report_runs ON report_runs(period_start DESC);

CREATE TABLE export_runs (               -- trilha de acesso (RF-ETH.8)
    id           UUID PRIMARY KEY,
    export_type  TEXT NOT NULL,          -- dataset_csv|dataset_parquet|report_pdf|...
    dataset_name TEXT,
    filters      JSON,
    row_count    INT,
    requested_by TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- ═══════════════════════════════════════════════════════════════════
--  OPERAÇÃO
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE provider_credentials (
    id                UUID PRIMARY KEY,
    provider          TEXT NOT NULL UNIQUE,
    encrypted_api_key BYTEA NOT NULL,
    key_fingerprint   TEXT NOT NULL,
    endpoint          TEXT,
    tier              TEXT,              -- free|paid|unknown
    last_validated_at TIMESTAMPTZ,
    validation_status TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE llm_invocations (
    id                UUID PRIMARY KEY,
    stage             TEXT NOT NULL,     -- classify|extract|correlate|draft|insight|embed
    use_case          TEXT NOT NULL,
    provider          TEXT NOT NULL,
    model             TEXT NOT NULL,
    prompt_tokens     INT,
    cached_tokens     INT,
    thinking_tokens   INT,
    completion_tokens INT,
    latency_ms        INT,
    cost_usd          NUMERIC,
    success           BOOLEAN,
    error             TEXT,
    correlation_id    TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_llm_daily ON llm_invocations(created_at, stage);
```

### 11.1 Datasets de exportação para BI (RF-I.25)

Views estáveis e versionadas. **Nenhuma contém corpo de mensagem** — apenas dados estruturados e agregáveis.

| Dataset (view) | Grão | Uso típico em BI |
|---|---|---|
| `dim_date` | Dia | Calendário com semana/mês/trimestre/dia útil |
| `dim_task` | Tarefa | Atributos estáveis + datas-chave |
| `dim_project` | Projeto | Portfólio, área, dono, datas alvo |
| `dim_milestone` | Marco | Prazo, status, aderência |
| `dim_stakeholder` | Pessoa | **Área e flag `is_own_team`; sem métrica de desempenho** |
| `dim_area` | Área | Hierarquia organizacional |
| `fact_task_daily` | Tarefa × dia | WIP, aging, CFD, burn-up |
| `fact_task_transitions` | Transição | Lead time, tempo em estado, retrabalho |
| `fact_interactions` | Touchpoint | Interfaces, responsividade agregada |
| `fact_meetings` | Reunião | Tempo, classe, ação produzida |
| `metric_values` | Métrica × período × dimensão | KPIs já calculados (fonte única de verdade) |

> **Princípio:** o número que aparece no Power BI deve ser **o mesmo** que aparece no cockpit. Por isso `metric_values` é exportado — não se recalcula métrica no BI. Cálculo duplicado é divergência garantida.

---

## 12. Catálogo de Métricas

Catálogo inicial do MVP: **7 perspectivas, ~55 métricas**. Toda métrica exige `question`, `formula`, `limitations`, `expected_action`, `owner` e teste com fixture (RF-I.5).

> **Convenção de leitura:** `id` · **Pergunta** que responde · **Ação esperada** quando desvia.
> Colunas omitidas por brevidade (fórmula, dimensões, grão) são obrigatórias no código.

### Perspectiva 1 — Demanda & Carga

| id | Pergunta | Ação esperada |
|---|---|---|
| `demand.inflow` | Quantas demandas novas entram por período? | Comparar com `flow.throughput`; se inflow > throughput por 3 períodos, renegociar escopo |
| `demand.by_origin` | De onde vem o trabalho (área própria, pares, gestão, externo, autogerado)? | Se uma origem domina inesperadamente, investigar processo a montante |
| `demand.by_requester_area` | Quais áreas mais demandam? | Alto volume recorrente ⇒ propor rotina, template ou SLA formal |
| `demand.by_type` | Que natureza de trabalho predomina (ação, decisão, aprovação, informação)? | Excesso de `approval` ⇒ candidato a delegação de alçada |
| `demand.unplanned_ratio` | % de demanda não vinculada a projeto | > 40% sustentado ⇒ estruturar como projeto ou rotina |
| `demand.critical_share` | % de demanda entrando como crítica | Inflação de prioridade ⇒ revisar critério de classificação |
| `demand.arrival_variability` | Quão irregular é a chegada (coef. de variação)? | Alta variabilidade explica filas mesmo com capacidade média suficiente |
| `demand.self_generated_ratio` | Quanto do trabalho eu mesmo gero? | Baixo demais pode indicar postura só reativa |

### Perspectiva 2 — Fluxo & Tempo

| id | Pergunta | Ação esperada |
|---|---|---|
| `flow.throughput` | Quantas tarefas concluo por período? | Base de todo cálculo de capacidade |
| `flow.net_flow` | Estou entregando mais do que entra? | Positivo por 3 semanas ⇒ renegociar, redistribuir ou reduzir WIP |
| `flow.wip` | Quantas tarefas abertas simultaneamente? | Acima do limite pessoal ⇒ parar de começar, começar a terminar |
| `flow.lead_time_p50` / `_p85` / `_p95` | Quanto tempo do pedido à entrega? | Usar **p85 como promessa**, não a média |
| `flow.cycle_time_p50` / `_p85` | Quanto tempo do início efetivo à entrega? | Diferença grande vs. lead time ⇒ fila de entrada é o gargalo, não a execução |
| `flow.time_in_status` | Onde o tempo é consumido por estado? | Estado dominante indica onde intervir |
| `flow.waiting_ratio` | % do lead time em espera por terceiros | > 50% ⇒ o gargalo é interface, não capacidade própria |
| `flow.blocked_ratio` | % do lead time bloqueado | Alto ⇒ investigar causa-raiz de bloqueio recorrente |
| `flow.aging_wip_p85` | Quão velhas são as tarefas ainda abertas? | Atacar as mais velhas primeiro — envelhecer não melhora nada |
| `flow.stale_count` | Quantas tarefas sem movimento acima do SLA? | Zerar semanalmente ou fechar explicitamente |
| `flow.flow_efficiency` | cycle_time útil / cycle_time total | < 30% ⇒ o problema é espera, não esforço |
| `flow.rework_rate` | % de tarefas que voltaram de estado (regressão) | Alto ⇒ critério de "pronto" mal definido |
| `flow.cfd` | Como o fluxo acumulado evolui? | Faixas que engrossam mostram acúmulo visualmente |

### Perspectiva 3 — Interfaces & Dependências

> ⚠️ Toda métrica desta perspectiva é **agregada por área** por padrão, sujeita a k-anonimato (RF-ETH.1) e proibição de ranking individual (RF-ETH.2).

| id | Pergunta | Ação esperada |
|---|---|---|
| `interface.pending_count_by_area` | Quantas pendências minhas estão em cada área? | Concentração ⇒ conversa estrutural com a interface, não cobrança individual |
| `interface.avg_wait_days_by_area` | Quanto tempo espero, em média, por área? | Acima do aceitável ⇒ propor SLA ou caminho alternativo |
| `interface.oldest_pending_days` | Qual a pendência mais antiga por área? | Escalar antes que vire problema visível |
| `interface.resolution_rate_by_area` | % de pendências resolvidas no período | Baixa e persistente ⇒ escalar formalmente |
| `interface.nudges_per_resolution` | Quantas cobranças por item resolvido? | > 2 ⇒ o canal ou o processo está errado |
| `interface.interaction_density` | Quantos touchpoints por tarefa em espera? | Muito baixo ⇒ minha própria falta de acompanhamento |
| `interface.dependency_concentration` | % de pendências concentradas na maior interface | Alta ⇒ risco de ponto único de falha |
| `interface.own_team_load` | Distribuição de carga na equipe própria | **Finalidade: apoio e redistribuição.** Nunca comparação de eficiência |

### Perspectiva 4 — Portfólio & Marcos

| id | Pergunta | Ação esperada |
|---|---|---|
| `portfolio.projects_by_health` | Distribuição dos projetos por faixa de saúde | Concentração em vermelho ⇒ repriorizar portfólio |
| `portfolio.projects_at_risk` | Quantos e quais projetos em risco? | Plano de recuperação ou parada explícita |
| `portfolio.silent_projects` | Projetos sem atividade há > N dias | Decidir: retomar, reduzir escopo ou encerrar formalmente |
| `portfolio.milestone_adherence` | % de marcos cumpridos no prazo | < 70% ⇒ o problema é estimativa, não execução |
| `portfolio.milestones_upcoming` | Marcos nos próximos 30/60/90 dias | Verificar capacidade antes de assumir mais |
| `portfolio.avg_milestone_slip_days` | Quantos dias, em média, os marcos atrasam | Usar como fator de correção nas próximas estimativas |
| `portfolio.wip_by_project` | Onde meu esforço está concentrado? | Dispersão excessiva ⇒ focar |
| `portfolio.progress_vs_time` | Progresso realizado vs. tempo decorrido | Divergência ⇒ replanejar cedo |
| `portfolio.blocked_by_project` | Bloqueios ativos por projeto | Priorizar desbloqueio antes de novas frentes |

### Perspectiva 5 — Agenda & Capacidade

| id | Pergunta | Ação esperada |
|---|---|---|
| `calendar.meeting_time_ratio` | % do tempo útil em reuniões | > 60% sustentado ⇒ recusar, delegar ou encurtar |
| `calendar.meeting_time_by_class` | Como o tempo se distribui (1:1, time, projeto, governança, externo)? | Excesso em governança ⇒ questionar valor dos fóruns |
| `calendar.recurring_time_ratio` | % do tempo em reuniões recorrentes | Alto ⇒ auditoria de recorrentes; é a economia mais fácil de agenda |
| `calendar.meetings_without_agenda` | % de reuniões sem pauta | Exigir pauta ou declinar |
| `calendar.meetings_producing_actions` | % de reuniões que geram item acionável | Baixo ⇒ reunião informativa que poderia ser e-mail |
| `calendar.focus_blocks` | Quantos blocos livres ≥ 90 min por semana? | < 3 ⇒ agenda incompatível com trabalho de fundo |
| `calendar.largest_free_block` | Qual o maior bloco contínuo disponível? | Base realista de planejamento diário |
| `calendar.capacity_available` | Horas livres projetadas por período | Comparar com compromissos antes de aceitar mais |
| `calendar.overcommitment_index` | Esforço estimado comprometido / capacidade disponível | > 1 ⇒ **já está prometido mais do que cabe** |
| `calendar.fragmentation_index` | Quão picada é a agenda (nº de janelas / tempo livre)? | Alta fragmentação explica baixa entrega mesmo com "tempo livre" |
| `calendar.after_hours_load` | Carga fora do horário de trabalho | **Somente auto-monitoramento, opt-in.** Nunca aplicado a terceiros (RF-ETH.4) |

### Perspectiva 6 — Compromissos & Prazos

| id | Pergunta | Ação esperada |
|---|---|---|
| `commit.on_time_delivery` | % de tarefas entregues no prazo | < 80% ⇒ o problema está na promessa, não no esforço |
| `commit.overdue_count` | Quantas tarefas vencidas agora? | Zerar ou renegociar explicitamente — não deixar apodrecer |
| `commit.avg_slip_days` | Quantos dias, em média, atraso | Usar como buffer padrão nas próximas promessas |
| `commit.replanning_rate` | Média de replanejamentos por tarefa | > 1,5 ⇒ estimativa inicial sistematicamente otimista |
| `commit.promise_accuracy` | Prazo prometido vs. lead time realizado (p85) | Calibrar promessa pelo p85 histórico |
| `commit.due_soon` | Vencendo em 7 dias | Verificação preventiva semanal |
| `commit.no_due_date_ratio` | % de tarefas sem prazo | Alto ⇒ compromissos invisíveis, sem gatilho de cobrança |
| `commit.commitments_made_to_others` | Quantos compromissos eu assumi com terceiros? | Cruzar com capacidade antes de assumir mais |

### Perspectiva 7 — Saúde do Sistema (meta-métricas)

> Sem esta perspectiva, o cockpit não é auditável — e um cockpit não auditável não deve ser usado em decisão.

| id | Pergunta | Ação esperada |
|---|---|---|
| `system.ingestion_coverage` | Que % do fluxo esperado foi ingerido? | < 90% ⇒ investigar antes de confiar em qualquer número |
| `system.extraction_precision` | Qual a precisão da extração (dataset dourado)? | Queda ⇒ revisar prompt ou modelo |
| `system.correlation_accuracy` | Qual a acurácia da correlação? | < 85% ⇒ recalibrar limiares |
| `system.auto_action_rate` | % de ações aplicadas automaticamente | Contexto para interpretar a taxa de undo |
| `system.undo_rate` | % de ações automáticas revertidas | **> 10% ⇒ elevar limiares imediatamente** |
| `system.triage_backlog` | Quantos itens aguardam triagem? | Crescente ⇒ ruído alto ou hábito de triagem ausente |
| `system.triage_time_daily` | Tempo gasto em triagem por dia | > 5 min ⇒ ajustar filtros e limiares |
| `system.llm_cost_daily` | Custo diário de LLM | Acima do teto ⇒ revisar pré-filtros e atalhos |
| `system.sync_health` | Canais saudáveis vs. degradados | Qualquer canal degradado invalida métricas do período |
| `system.data_freshness` | Há quanto tempo foi a última sincronização bem-sucedida? | > 24h ⇒ banner de dados desatualizados no cockpit |
| `system.metrics_without_action` | Métricas sem ação registrada em 90 dias | **Candidatas a remoção** (RF-ETH.10) |
| `system.manual_metrics_stale` | Métricas manuais vencidas | Atualizar ou marcar como descontinuada |

### 12.1 Definição do Health Score de projeto (RF-I.1)

Determinístico, decomposto e **explicável** — `health_components` armazena cada parcela:

| Componente | Peso | Cálculo |
|---|---|---|
| Aderência a marcos | 30% | marcos cumpridos no prazo / marcos vencidos |
| Atraso de tarefas | 25% | 1 − (tarefas vencidas / tarefas ativas) |
| Atividade recente | 20% | decaimento por `days_since_activity` |
| Bloqueios | 15% | penalidade por bloqueio ativo, ponderada pela idade |
| Progresso vs. tempo | 10% | % concluído / % do prazo decorrido, saturado em 1 |

Faixas: **verde ≥ 75** · **amarelo 50–74** · **vermelho < 50**. Amostra insuficiente ⇒ `null` com motivo, nunca zero.

> Exibir apenas "saúde = 62 (amarelo)" sem a decomposição gera desconfiança justificada. O drill-down do score mostra as cinco parcelas e os itens que as compõem.

---

## 13. Contratos de API

Base: `/api/v1`

### Autenticação e sincronização

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/auth/login` · `/auth/callback` · `/auth/status` | OAuth PKCE e estado de conexão |
| `POST` | `/sync/run?channels=mail,chat,calendar` | Dispara sincronização |
| `GET` | `/sync/status` | Estado por canal/recurso + cobertura da última execução |

### Sinais, correlação e triagem

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/signals?state=pending_correlation` | Sinais não resolvidos |
| `POST` | `/signals/{id}/recorrelate` | Força reavaliação |
| `GET` | `/signals/{id}/correlation` | Auditoria: candidatos, scores, assessments, regra, guardrails |
| `GET` | `/proposals?status=pending&kind=` | Fila de triagem |
| `POST` | `/proposals/{id}/accept` · `/reject` · `/merge` · `/disambiguate` | Resolução de proposta |

### Tarefas, projetos e estrutura

| Método | Endpoint | Descrição |
|---|---|---|
| `GET/POST` | `/tasks` | Lista com filtros · criação manual |
| `GET/PATCH` | `/tasks/{id}` | Detalhe completo · atualização parcial |
| `POST` | `/tasks/{id}/transition` · `/updates` · `/snooze` | Operações de tarefa |
| `POST` | `/tasks/{id}/undo/{history_id}` | **Reverte ação automática** |
| `GET` | `/tasks/{id}/timeline` | Evidências + updates + reuniões + interações |
| `GET/POST/PATCH` | `/projects` · `/portfolios` · `/milestones` · `/areas` | CRUD + métricas derivadas |
| `GET` | `/projects/{id}/health` | Score + **decomposição em componentes** |
| `GET` | `/stakeholders/{id}/pending` · `/interactions` | Visão operacional por pessoa |

### Calendário e capacidade

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/calendar/upcoming?days=7` | Eventos com pauta sugerida e carga |
| `GET/POST` | `/calendar/events/{id}/agenda[/{task_id}]` | Pauta da reunião · fixar item |
| `GET` | `/capacity?from=&to=` | Horas livres, blocos de foco, índice de sobrecompromisso |

### Follow-up e digest

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/follow-ups?status=suggested&channel=` | Follow-ups sugeridos |
| `POST` | `/follow-ups/{id}/send` · `/dismiss` | Envio após confirmação · descarte |
| `GET` | `/digest/daily` · `/digest/weekly` | Digest renderizado |

### ★ Cockpit — métricas

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/metrics/catalog` | Catálogo completo com `question`, fórmula, limitações, ação esperada, versão |
| `GET` | `/metrics/{metric_id}` | Valor com **envelope obrigatório** (RF-I.6): cobertura, amostra, supressão, comparação |
| `GET` | `/metrics/{metric_id}/series` | Série temporal com `grain`, dimensão, comparação e anotações de contexto |
| `POST` | `/metrics/batch` | Múltiplas métricas em uma chamada (carga de dashboard) |
| `GET` | `/metrics/{metric_id}/drilldown` | **Lista de tarefas que compõem o valor**, paginada |
| `GET` | `/metrics/{metric_id}/explain` | Fórmula, fonte, SQL executado, limitações, versão vigente |
| `POST` | `/metrics/recompute` | Recálculo (por métrica, período ou completo) |
| `GET` | `/metrics/runs` | Histórico de execuções do motor de métricas |

### ★ Cockpit — dashboards e snapshots

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/dashboards` | Lista (padrão + customizados) |
| `GET` | `/dashboards/{slug}` | Layout + widgets |
| `GET` | `/dashboards/{slug}/data?filters=` | **Payload consolidado, tudo já calculado no backend** |
| `POST/PATCH/DELETE` | `/dashboards[/{id}]` · `/widgets` | Gestão de layout |
| `POST` | `/dashboards/{slug}/reset` | Restaura layout padrão |
| `GET/POST` | `/saved-views` | Filtros salvos e compartilháveis |
| `POST` | `/snapshots/build?date=` | Gera snapshot de uma data |
| `POST` | `/snapshots/backfill?from=&to=` | Reconstrói histórico a partir de `task_status_history` |
| `GET` | `/snapshots/status` | Cobertura de datas, lacunas detectadas |

### ★ Cockpit — alertas, insights e decisões

| Método | Endpoint | Descrição |
|---|---|---|
| `GET/POST/PATCH` | `/alert-rules[/{id}]` | Gestão de regras (limiar e anomalia) |
| `POST` | `/alert-rules/evaluate` | Avaliação sob demanda |
| `GET` | `/alerts?status=open&severity=` | Alertas ativos |
| `POST` | `/alerts/{id}/acknowledge` · `/action` · `/resolve` · `/dismiss` | Ciclo de vida |
| `GET` | `/alerts/{id}/drilldown` | Itens que originaram o alerta |
| `POST` | `/insights/generate` | Gera narrativa (scope, período, filtros) |
| `GET` | `/insights?scope=&period=` | Histórico de insights |
| `GET` | `/insights/{id}/audit` | **Payload de métricas usado + resultado do guardrail numérico** |
| `POST` | `/insights/{id}/actions/{idx}/convert` | Converte sugestão em tarefa ou decisão |
| `GET/POST/PATCH` | `/decisions[/{id}]` | Registro de decisões |
| `POST` | `/decisions/{id}/review` | Avaliação de resultado (antes/depois) |
| `GET` | `/decisions/pending-review` | Revisões vencidas |

### ★ Cockpit — entrada manual, relatórios e exportação

| Método | Endpoint | Descrição |
|---|---|---|
| `GET/POST` | `/manual-metrics` | Entradas manuais com histórico de alteração |
| `POST` | `/manual-metrics/import` | Upload CSV/XLSX com mapeamento e preview |
| `GET` | `/manual-metrics/stale` | Métricas manuais vencidas |
| `GET/POST` | `/targets` | Metas por métrica e período |
| `GET/POST/DELETE` | `/annotations` | Anotações de contexto nas séries |
| `GET/POST` | `/report-templates` | Templates e agendamento |
| `POST` | `/reports/generate` | Gera one-pager (retorna `report_run_id`) |
| `GET` | `/reports/{id}` | Metadados + artefatos |
| `GET` | `/reports/{id}/download?format=md\|pdf\|pptx` | Download |
| `GET` | `/exports/datasets` | Datasets disponíveis com schema |
| `GET` | `/exports/datasets/{name}?format=csv\|parquet&from=&to=` | Exportação para BI |

### Configuração e operação

| Método | Endpoint | Descrição |
|---|---|---|
| `GET/PATCH` | `/settings` | Filtros, limiares, regras, horário de trabalho, **config analítica** |
| `GET/PUT` | `/settings/providers/{provider}` | Chave (**write-only**; GET retorna só máscara) |
| `POST` | `/settings/providers/{provider}/test` | Testa conexão |
| `GET` | `/settings/providers/{provider}/models` | Modelos disponíveis para a chave |
| `GET` | `/metrics` | Prometheus (métricas técnicas) |
| `GET` | `/system/health-report` | **Perspectiva 7 consolidada** |
| `GET` | `/health/live` · `/health/ready` | Health checks |

**Padrões obrigatórios:** paginação por cursor · erros RFC 7807 (`application/problem+json`) · `Idempotency-Key` em POSTs mutáveis · versionamento por path · OpenAPI 3.1 automático · **toda resposta de métrica com o envelope do RF-I.6**.

---

## 14. Estratégia de Deploy

### 14.1 Local (perfil `local`)

```bash
git clone … && cd taskflow
cp .env.example .env    # GEMINI_API_KEY, GRAPH_CLIENT_ID, GRAPH_TENANT_ID, ENCRYPTION_KEY
docker compose -f infra/compose/local.yml up
```

- Um container app (API + worker in-process via APScheduler)
- SQLite em volume (`./data/taskflow.db`) com FTS5 e sqlite-vec
- **Snapshots e `metric_values` como tabelas materializadas** (SQLite não tem materialized view)
- LLM: Gemini via API **ou** Ollama sidecar (privacidade máxima)
- UI servida como estáticos pela própria API em `http://localhost:8080`
- Setup wizard: device code flow → provedor de IA → **backfill inicial de snapshots**
- **Alvo:** `git clone` → `.env` → um comando → funcionando

### 14.2 Cloud (perfil `cloud`)

- Containers **API** e **worker** separados, escala independente
- PostgreSQL gerenciado com **pgvector**; `daily_task_snapshots` **particionada por mês**
- **Materialized views** para agregados de alta cardinalidade, com refresh no job noturno
- Redis para fila (ARQ) e cache de payload de dashboard
- Segredos em Azure Key Vault, injetados como env vars
- Referência: Azure Container Apps + Azure Database for PostgreSQL Flexible Server
- Terraform em `infra/terraform` (fase 9)
- Migrations Alembic como job de pré-deploy

### 14.3 Jobs agendados

| Job | Frequência | Observação |
|---|---|---|
| `sync_all` | 15 min | Mail, chat, calendar |
| `extract_signals` | Contínuo (fila) | Respeita teto de tokens |
| `correlate_signals` | Contínuo (fila) | Atalho determinístico antes de G2 |
| `recorrelate_orphans` | 6 h | Apenas G1, barato |
| `evaluate_staleness` | 1 h | Follow-ups e nudges |
| **`build_daily_snapshots`** | **Diário, 23:50 TZ local** | **Idempotente; base de tudo analítico** |
| **`compute_metrics`** | **Diário, após snapshots** | **+ recálculo incremental de 7 dias** |
| **`evaluate_alert_rules`** | **Diário, após métricas** | **Limiar + anomalia** |
| **`generate_weekly_insight`** | **Semanal (seg 07:00)** | **Adiável se teto de tokens atingido** |
| **`generate_scheduled_reports`** | **Conforme cron** | **Sempre em rascunho** |
| `purge_retention` | Semanal | Respeita `RETENTION_DAYS` e retenção analítica |
| `refresh_materialized_views` | Diário (cloud) | Após métricas |

### 14.4 Ordem de dependência (crítica)

```
sync → extract → correlate → [estado operacional consistente]
                                        ↓
                          build_daily_snapshots (23:50)
                                        ↓
                              compute_metrics
                                        ↓
                          evaluate_alert_rules
                                        ↓
                     generate_insight / reports (opcional)
```

Falha em `build_daily_snapshots` **não** deve disparar `compute_metrics` com dados parciais — o job seguinte verifica a existência do snapshot do dia e aborta com alerta explícito. Métrica calculada sobre snapshot incompleto é pior que métrica ausente.

---

## 15. Configuração (`.env`)

```env
# ── Aplicação ───────────────────────────────────────────────────────
APP_ENV=local                            # local|cloud
LOG_LEVEL=INFO
ENCRYPTION_KEY=                          # base64, 32 bytes
TIMEZONE=America/Sao_Paulo

# ── Persistência ────────────────────────────────────────────────────
DATABASE_URL=sqlite+aiosqlite:///./data/taskflow.db
QUEUE_BACKEND=inprocess                  # inprocess|redis
REDIS_URL=

# ── Microsoft Graph ─────────────────────────────────────────────────
GRAPH_CLIENT_ID=
GRAPH_TENANT_ID=
GRAPH_AUTH_FLOW=device_code              # device_code|auth_code_pkce
SYNC_INTERVAL_MINUTES=15

# ── LLM: Gemini (default) ───────────────────────────────────────────
LLM_PROVIDER=gemini
GEMINI_API_KEY=                          # ou via UI (cifrada em repouso)
LLM_MODEL_CLASSIFIER=                    # ★ ID exato obtido via models.list
LLM_MODEL_REASONER=                      # ★ ID exato obtido via models.list
LLM_VALIDATE_MODEL_ON_STARTUP=true
LLM_THINKING_BUDGET_CLASSIFY=0
LLM_THINKING_BUDGET_EXTRACT=1024
LLM_THINKING_BUDGET_CORRELATE=2048
LLM_THINKING_BUDGET_INSIGHT=4096
LLM_ENABLE_CONTEXT_CACHE=true
LLM_MAX_RETRIES=4
LLM_SAFETY_THRESHOLD=BLOCK_ONLY_HIGH
DAILY_TOKEN_BUDGET=200000
LLM_DEFER_INSIGHT_AT_BUDGET_PCT=0.80     # narrativa é adiada antes da operação

# ── Embeddings ──────────────────────────────────────────────────────
EMBEDDING_PROVIDER=gemini
EMBEDDING_DIM=768

# ── Privacidade e retenção ──────────────────────────────────────────
STORE_FULL_BODY=false
RETENTION_DAYS=180
ANALYTICS_RETENTION_MONTHS=36            # agregados vivem mais que o detalhe

# ── Ingestão: calendário ────────────────────────────────────────────
CALENDAR_ENABLED=true
CALENDAR_WINDOW_PAST_DAYS=30
CALENDAR_WINDOW_FUTURE_DAYS=90
CALENDAR_INCLUDE_PRIVATE=false           # privados = só bloco de tempo
CALENDAR_MIN_ATTENDEES_FOR_EXTRACTION=2

# ── Capacidade ──────────────────────────────────────────────────────
WORK_HOURS_START=08:30
WORK_HOURS_END=18:00
WORK_DAYS=1,2,3,4,5
CAPACITY_BUFFER_MINUTES=60
FOCUS_BLOCK_MIN_MINUTES=90

# ── Extração ────────────────────────────────────────────────────────
EXTRACTION_MIN_CONFIDENCE=0.55

# ── Correlação ──────────────────────────────────────────────────────
CORRELATION_TOP_K=8
CORRELATION_RRF_K=60
CORR_AUTO_UPDATE_MIN=0.80
CORR_AUTO_TRANSITION_MIN=0.85
CORR_AUTO_DONE_MIN=0.90
CORR_NEW_TASK_MIN=0.85
CORR_ATTACH_CONTEXT_MIN=0.60
CORR_NOISE_MIN=0.70
CORR_DISCARD_MAX=0.55
CORR_AMBIGUITY_DELTA=0.10
SIGNAL_PENDING_TTL_DAYS=7
ALLOW_AUTO_DONE=true
ALLOW_AUTO_CANCEL=false                  # ★ deve permanecer false

# ── Follow-up ───────────────────────────────────────────────────────
STALENESS_WAITING_DAYS=3
STALENESS_IN_PROGRESS_DAYS=7
STALENESS_BLOCKED_DAYS=5
PREFER_MEETING_OVER_EMAIL_HOURS=48
NUDGE_TONE=cordial                       # direct|cordial|formal

# ── ★ Analítica ─────────────────────────────────────────────────────
ANALYTICS_ENABLED=true
SNAPSHOT_HOUR=23:50                      # hora local do job diário
SNAPSHOT_INCLUDE_TERMINAL_DAYS=1         # concluídas ainda entram no snapshot do dia
METRICS_INCREMENTAL_WINDOW_DAYS=7        # recálculo incremental por execução
METRICS_MIN_SAMPLE=5                     # abaixo disso, supressão (RF-I.6)
METRICS_COVERAGE_LOW_THRESHOLD=0.70      # < 70% ⇒ coverage.level='low'
METRICS_COVERAGE_HIGH_THRESHOLD=0.90     # ≥ 90% ⇒ 'high'
METRICS_DEFAULT_GRAIN=week
METRICS_PERCENTILES=50,85,95
DASHBOARD_CACHE_TTL_SECONDS=300
DATA_FRESHNESS_WARNING_HOURS=24          # banner de dados desatualizados

# ── ★ Ética analítica (Seção 8) ─────────────────────────────────────
ETHICS_MIN_GROUP_SIZE=3                  # k-anonimato por área (RF-ETH.1)
ETHICS_ALLOW_INDIVIDUAL_METRICS=own_team_only   # own_team_only|self_only|none
ETHICS_ALLOW_AFTER_HOURS_METRICS=self_only      # self_only|none
ETHICS_SHOW_PURPOSE_BANNER=true                 # RF-ETH.5 — não desativável em export

# ── ★ Alertas ───────────────────────────────────────────────────────
ALERTS_ENABLED=true
ALERTS_MAX_ACTIVE=7                      # anti-fadiga (RF-I.20)
ALERTS_ANOMALY_SIGMA=2.0
ALERTS_BASELINE_PERIODS=8
ALERTS_DEFAULT_PERSISTENCE=2             # períodos consecutivos antes de disparar
ALERTS_UNACKED_REMINDER_DAYS=3
ALERTS_RULE_REVIEW_AFTER_FIRES=3         # dispara 3× sem ação ⇒ revisar regra

# ── ★ Insights narrativos ───────────────────────────────────────────
INSIGHTS_ENABLED=true
INSIGHTS_WEEKLY_CRON=0 7 * * 1
INSIGHTS_NUMERIC_GUARD_STRICT=true       # ★ não desativar
INSIGHTS_MAX_RETRIES=1
INSIGHTS_MIN_COVERAGE=0.70               # abaixo disso, não gera narrativa

# ── ★ Relatórios e exportação ───────────────────────────────────────
REPORTS_ENABLED=true
REPORTS_OUTPUT_DIR=./data/reports
REPORTS_DEFAULT_FORMATS=md,pdf
REPORTS_ALWAYS_DRAFT=true                # ★ nunca envia sem revisão (RF-I.24)
EXPORTS_ENABLED=true
EXPORTS_MAX_ROWS=500000
EXPORTS_INCLUDE_MESSAGE_BODY=false       # ★ deve permanecer false
```

### 15.1 Variáveis que não devem ser alteradas sem justificativa registrada

| Variável | Default | Por quê é sensível |
|---|---|---|
| `ALLOW_AUTO_CANCEL` | `false` | Cancelamento automático destrói compromisso sem rastro de decisão humana |
| `INSIGHTS_NUMERIC_GUARD_STRICT` | `true` | Desativar permite número alucinado em apresentação de diretoria |
| `EXPORTS_INCLUDE_MESSAGE_BODY` | `false` | Vazamento de conteúdo de comunicação em planilha compartilhada |
| `REPORTS_ALWAYS_DRAFT` | `true` | Envio automático de relatório a terceiros sem revisão |
| `ETHICS_MIN_GROUP_SIZE` | `3` | Abaixo de 3, agregação por área permite identificação individual |
| `ETHICS_SHOW_PURPOSE_BANNER` | `true` | Número circulando sem nota de finalidade e limitação |
| `CALENDAR_INCLUDE_PRIVATE` | `false` | Conteúdo confidencial de agenda enviado a LLM externo |
| `STORE_FULL_BODY` | `false` | Amplia drasticamente a superfície de dados em repouso |

> O agente deve implementar essas oito variáveis com **aviso explícito na inicialização** quando divergirem do default seguro, e registrá-las em `docs/SECURITY.md`.

---

## 16. Estratégia de Testes

### 16.1 Pirâmide

| Nível | Escopo | Ferramenta | Meta |
|---|---|---|---|
| **Unitário** | Domínio puro: `TaskStateMachine`, `CorrelationPolicy`, `CandidateFusion`, `StalenessPolicy`, `CapacityPolicy`, `PrivacyRedactionPolicy`, **`CoveragePolicy`, `SuppressionPolicy`, `HealthScorePolicy`, `AlertRuleEngine`, `AnomalyDetector`, `EthicsGuard`** | pytest | **≥ 90% em `domain/`** |
| **★ Métricas** | **Uma fixture sintética por métrica, com resultado esperado calculado à mão** | pytest | **100% das métricas registradas** |
| **Integração** | Repositórios, migrations, índices vetoriais, **read model analítico**, adapters | pytest + testcontainers | Caminhos críticos, em SQLite **e** Postgres |
| **Contrato** | Graph fixado em cassettes (mail, chat, `calendarView/delta`), incluindo 429, 401, `410 Gone`, séries com exceção | respx / VCR.py | Todos os cenários de erro |
| **Avaliação (LLM)** | Datasets dourados — ver 16.3 | pytest custom + relatório | **Gate no CI** |
| **E2E** | Triagem → aceite → transição → follow-up → undo · **cockpit → drill-down → evidência** · **alerta → decisão → revisão** | Playwright | Fluxos principais |

> **Regra absoluta:** chamadas de LLM **nunca** em testes unitários ou de integração — sempre stub da porta `LLMProvider`. A suíte de avaliação é separada e roda sob demanda/nightly.

### 16.2 ★ Gate de governança de métricas (novo, bloqueante no CI)

Um teste de meta-validação percorre o `MetricRegistry` e **falha o build** se qualquer métrica:

1. Não tiver `question`, `formula`, `limitations`, `expected_action`, `owner` preenchidos
2. Não tiver teste correspondente em `tests/metrics/`
3. Tiver `formula` alterada sem incremento de `version` (comparação com snapshot do registro em `metric_definitions`)
4. Declarar `dimensions` inexistentes no read model
5. Retornar valor sem o envelope do RF-I.6
6. Violar `EthicsGuard` — métrica individual sobre stakeholder externo, ranking de pessoas, ou métrica de horário/presença de terceiros

> Item 6 é o que torna a Seção 8 executável em vez de decorativa. Uma métrica antiética não passa do commit.

### 16.3 Datasets dourados e gates de qualidade

| Conjunto | Volume mínimo | Rótulo | Gate no CI |
|---|---|---|---|
| Extração — e-mail/chat | 50 itens | é tarefa? campos esperados | precision ≥ 0,80 |
| Extração — calendário | 20 eventos | tipo de sinal esperado | precision ≥ 0,80 |
| **Correlação** | **40 pares (sinal, estado da base)** | decisão esperada + `task_id` | **acurácia ≥ 0,85** |
| Correlação — negativos | 15 casos correlatos não acionáveis | `ATTACH_CONTEXT` / `NOISE` | recall ≥ 0,90 |
| **★ Insight narrativo** | **10 payloads de métricas com narrativa de referência** | **números presentes no texto** | **guardrail numérico: 100% de detecção de número inventado** |

### 16.4 Testes determinísticos obrigatórios (sem LLM)

**Operacionais (v1.1)**
- `CorrelationPolicy`: **toda linha da matriz RF-G.8** com teste próprio, incluindo bloqueios (auto-done sem match determinístico, antecipação de prazo, cancelamento automático)
- `CandidateFusion`: RRF produz ordenação estável e reprodutível
- `TaskStateMachine`: matriz completa de transições válidas e inválidas
- `CapacityPolicy`: eventos sobrepostos, all-day, fora do horário, timezones distintos
- **Propriedade de privacidade:** nenhum `SourceItem` com `sensitivity IN ('private','confidential')` alcança o payload enviado ao `LLMProvider` — spy no adapter, build falha se ocorrer
- **Propriedade de segredo:** nenhuma API key em log, resposta de API ou mensagem de erro
- **Undo:** para cada tipo de ação automática, restauração exata do estado anterior

**★ Analíticos (v1.2)**
- **Determinismo de snapshot:** `backfill-snapshots` para uma data já processada produz resultado **idêntico** (propriedade)
- **Idempotência de snapshot:** reexecução não duplica linha nem altera contagem
- **Consistência histórico ↔ snapshot:** `cum_days_*` derivado de `task_status_history` confere com o acumulado do snapshot, para 100 cenários gerados
- **Supressão por amostra:** `sample_size < METRICS_MIN_SAMPLE` ⇒ `is_suppressed=true`, sem valor numérico
- **K-anonimato:** área com 2 pessoas ⇒ métrica suprimida com motivo
- **Propriedade "LLM não calcula":** spy no `LLMProvider` durante todos os endpoints de métrica — **zero invocações**
- **Propriedade "frontend não calcula":** teste de contrato garante que a resposta de `/dashboards/{slug}/data` contém todos os valores renderizados, sem agregação no cliente
- **Versionamento:** alterar fórmula sem incrementar `version` falha o gate
- **Guardrail numérico de insight:** payload com `net_flow=12.4` + texto contendo `18` ⇒ rejeição detectada
- **Drill-down soma:** para 20 métricas de contagem, `len(drilldown) == value` (propriedade de reconciliação)
- **Paridade SQLite ↔ Postgres:** as mesmas fixtures produzem os mesmos valores nos dois dialetos
- **Explicabilidade de alerta:** todo alerta gerado tem `explanation` não vazia e renderizada do template

> O teste de **drill-down soma** é o mais valioso do conjunto analítico. Se o número do cartão não bate com a lista que ele abre, a confiança no cockpit morre na primeira reunião — e não volta.

### 16.5 Métricas operacionais de qualidade monitoradas

| Métrica | Limiar de ação |
|---|---|
| Taxa de undo de ações automáticas | > 10% ⇒ elevar limiares de auto-aplicação |
| Precision de extração (nightly) | Queda > 5 p.p. ⇒ revisar prompt/modelo |
| Acurácia de correlação (nightly) | < 85% ⇒ recalibrar |
| Rejeições do guardrail numérico | > 20% dos insights ⇒ revisar prompt de narrativa |
| Duração do job de snapshot | > 60 s ⇒ revisar índices ou particionamento |
| p95 de carga de dashboard | > 1,5 s ⇒ materializar mais agregados |

---

## 17. Roadmap de Entrega

Cada fase termina com: código funcional, testes verdes, documentação atualizada, commit convencional atômico.

| Fase | Escopo | Entregável verificável |
|---|---|---|
| **0 — Fundação** | Scaffold, uv/pyproject, ruff + mypy + pre-commit, Docker, compose local, settings, DI container, logging estruturado, health checks, CI | `docker compose up` sobe API respondendo `/health/live` |
| **1 — Domínio** | Entidades, value objects, ports, `TaskStateMachine`, `CorrelationPolicy`, `CandidateFusion`, `StalenessPolicy`, `CapacityPolicy`, `PrivacyRedactionPolicy` — 100% puro | Testes unitários verdes, **zero I/O** |
| **2 — Persistência** | Models, migrations Alembic, repositórios, UnitOfWork, índice vetorial, FTS, seed | CRUD testado em SQLite **e** Postgres |
| **3 — Graph: Mail & Chat** | Auth MSAL, token cache cifrado, `GraphMailSource`, `GraphChatSource`, delta, rate limit, circuit breaker, pré-filtros, `ingestion_runs` | `taskflow sync --channels=mail,chat` ingere caixa real; contratos verdes |
| **3.5 — Graph: Calendário** | `GraphCalendarSource`, `calendarView/delta`, séries e exceções, **redação de privacidade**, vínculo evento↔chat, sinais de calendário, classificação de reuniões, `CapacityPolicy` aplicada | `taskflow sync --channels=calendar`; propriedade de privacidade verde |
| **4 — Extração (Gemini)** | `GeminiProvider` (2 níveis, structured output, thinking budget, context caching, safety, gestão de chave), prompts versionados, guardrail de evidência, pipeline de 4 estágios, `Signal` | `taskflow extract`; avaliação de extração ≥ 0,80 precision |
| **4.5 — Correlação** | 6 recuperadores, RRF, atalho determinístico, G2 relacional, 4 guardrails, matriz de arbitragem, `correlation_runs`, ledger de interações, reprocessamento tardio | `taskflow correlate`; avaliação de correlação ≥ 0,85 acurácia |
| **5 — API + UI operacional** | Endpoints operacionais, OpenAPI, SPA: Hoje (com capacidade), Triagem, Aguardando, Projetos, Calendário + Pauta, Timeline, Auditoria de correlação, Undo, Settings de provedores | E2E: triagem → aceite → transição automática → undo |
| **6 — Follow-up** | Motor de regras ciente de reuniões, canal `bring_to_meeting`, nudges, digests diário e semanal, scheduler, snooze | Digest com ações automáticas e undo; nudge enviável com confirmação |
| **★ 6.5 — Estrutura organizacional** | `areas`, `portfolios`, `milestones`, vínculo de stakeholders com override manual, enriquecimento via Graph, flag `is_own_team` | CRUD completo; hierarquia de área navegável; marcos vinculados a projetos |
| **★ 7 — Fundação analítica** | `daily_task_snapshots`, `daily_project_snapshots`, `daily_calendar_snapshots`, job diário, `backfill-snapshots`, `HealthScorePolicy` decomposto, particionamento (Postgres) | **Propriedade de determinismo verde**; backfill de 90 dias reconstrói histórico idêntico |
| **★ 7.5 — Motor de métricas** | `MetricRegistry` code-first, ~55 métricas em 7 perspectivas, `CoveragePolicy`, `SuppressionPolicy`, `EthicsGuard`, `metric_values`, versionamento, `compute_metrics`, `audit-metric`, **gate de governança no CI** | **Gate de métricas bloqueante ativo**; 100% das métricas com fixture; paridade SQLite↔Postgres |
| **★ 8 — Cockpit UI** | Cockpit executivo, 7 dashboards temáticos, filtros globais com estado na URL, **drill-down universal até evidência**, biblioteca de gráficos (KPI, série, CFD, scatter, histograma, heatmap, matriz de risco), comparação de períodos, layout configurável, banner de finalidade | **E2E: número → lista → tarefa → evidência literal → deep link na fonte**; p95 < 1,5 s com 24 meses |
| **★ 8.5 — Alertas & Decisões** | `alert_rules` (limiar + anomalia explicável), ciclo de vida do alerta, anti-fadiga, auto-revisão de regra, `DecisionLog` com antes/depois, revisão vencida no digest | Alerta dispara → reconhece → decide → revisa, com métrica antes/depois |
| **★ 9 — Insights & Relatórios** | Épico J completo (narrativa com **guardrail numérico**, fato vs. hipótese, caveats, rastreabilidade), one-pager em MD/PDF/PPTX, relatórios agendados em rascunho, Épico K (entrada manual, CSV, metas, anotações), datasets para BI | **Guardrail numérico rejeita 100% dos números inventados** no dataset de teste; one-pager gerado em < 15 min de esforço |
| **10 — Produção** | Perfil cloud, ARQ + Redis, Postgres + pgvector particionado, materialized views, Terraform, runbook, backup/restore, purga, dashboards de observabilidade | Deploy cloud + runbook validado + restore testado |
| **11 — Backlog** | Sync bidirecional To Do/Planner, canais do Teams, multiusuário com permissão, acesso de terceiros ao cockpit, previsão Monte Carlo, PWA mobile | — |

### 17.1 Marcos de valor entregável

Não é necessário chegar à fase 11 para o sistema ser útil. Três pontos de parada com valor real:

| Marco | Fases | Valor entregue |
|---|---|---|
| **M1 — Captura funcionando** | 0 → 5 | Tarefas capturadas automaticamente de e-mail, chat e agenda, com triagem e correlação. Já substitui a captura manual. |
| **M2 — Acompanhamento ativo** | 6 → 6.5 | Follow-up ciente de reuniões, estrutura de projetos e marcos. Já resolve a perda de follow-up de ciclo longo. |
| **M3 — Cockpit gerencial** | 7 → 9 | Dashboards, alertas, decisões e one-pager. Já substitui a montagem manual de reporte. |

**Recomendação:** rodar M1 e M2 em uso real por **pelo menos 6 a 8 semanas antes de iniciar a fase 7**. Razão prática: métrica calculada sobre 3 semanas de dados não tem baseline, não tem tendência e não tem significado estatístico. Pior — se a taxa de captura ainda estiver sendo calibrada nesse período, os primeiros números do cockpit serão sistematicamente enviesados, e a desconfiança inicial num dashboard tende a ser permanente. Acumule histórico antes de medir.

---

## 18. Riscos e Mitigações

### 18.1 Riscos operacionais (v1.0/v1.1)

| Risco | Impacto | Prob. | Mitigação |
|---|---|---|---|
| App Registration não aprovado no tenant ENGIE | **Bloqueante** | Média | Engajar IT/Security na fase 0; desenvolver contra sandbox; avançar com fixtures. Apenas escopos delegados reduz atrito |
| Correlação errada aplica update em tarefa errada | Alto | Média | Guardrail 2 (`task_id` entre candidatos); auditoria em `correlation_runs`; undo 1-clique; triagem em ambiguidade |
| Auto-conclusão indevida | Alto | Média | Limiar 0,90 + match determinístico + origem = responsável; `cancelled` nunca automático; destaque no digest; monitorar undo |
| Dados sensíveis de calendário ao LLM | **Alto** | Média | Redação por `sensitivity` com default restritivo; teste de propriedade no CI; blocklist de categorias |
| Gemini tier gratuito com dados corporativos | **Alto** | Média | Exigir tier pago ou Vertex AI; detecção e aviso na UI; validação prévia de Segurança da Informação |
| Extração de baixa precisão gera ruído | Alto | Média | Datasets dourados com gate; limiares conservadores; `ATTACH_CONTEXT` absorve correlatos; feedback loop |
| Fadiga de triagem leva ao abandono | Alto | Média | `ATTACH_CONTEXT` de primeira classe; meta ≤ 5 min/dia; navegação por teclado; métrica O8 |
| Explosão de custo de LLM | Médio | Média | Atalho determinístico; candidatos vazios sem LLM; fichas compactas; context caching; teto com fila adiada |
| Delta token expirado → resync completo | Médio | Alta | `410 Gone` tratado com resync incremental por janela |
| Recorrentes geram sinais duplicados | Médio | Alta | Dedup por `body_hash`; extração só quando conteúdo muda |
| Teams API delegada com limitações | Médio | Média | Validar na fase 3; degradar para mail + calendar |
| Deriva de embeddings ao trocar provedor | Médio | Baixa | Persistir `embedding_model` + `dim`; job de reindexação; falha explícita em mismatch |
| Nome de modelo inválido | Baixo | Alta | `model_id` configurável + validação `models.list` na inicialização |
| Scope creep | Médio | Alta | Não-objetivos explícitos (5.3); escopo do MVP congelado |

### 18.2 ★ Riscos analíticos e gerenciais (v1.2)

| Risco | Impacto | Prob. | Mitigação |
|---|---|---|---|
| **Métrica errada apresentada em reunião de diretoria** | **Crítico** | Média | Drill-down universal obrigatório; `audit-metric`; fixture por métrica; teste de reconciliação (`len(drilldown) == value`); paridade entre dialetos |
| **Insight com número alucinado** | **Crítico** | Média | Guardrail numérico estrito com validação por parser; 2ª falha ⇒ narrativa suprimida; auditoria do payload em `insights.input_payload` |
| **Métrica interpretada como avaliação de pessoas** | **Alto** | **Alta** | Seção 8 implementada como código: `EthicsGuard` no CI, k-anonimato, proibição de ranking, banner de finalidade em UI e export, rodapé em relatório |
| **Viés de fonte única gera conclusão errada** | **Alto** | **Alta** | Envelope de cobertura obrigatório em toda métrica; `caveat` fixo; supressão por amostra; `system.ingestion_coverage` na Perspectiva 7; banner de dados desatualizados |
| **Baseline insuficiente produz tendência falsa** | Alto | Alta | Fases 7+ recomendadas após 6–8 semanas de uso real; supressão por amostra; anotações de contexto para explicar variação |
| **Proliferação de métricas decorativas** | Médio | **Alta** | `expected_action` obrigatório; `system.metrics_without_action`; revisão trimestral que **propõe remoção** (RF-ETH.10); catálogo com dono |
| **Fadiga de alerta** | Médio | Alta | Máximo de 7 ativos; persistência mínima antes de disparar; agrupamento; auto-revisão após 3 disparos sem ação |
| **Mudança de fórmula corrompe série histórica** | Alto | Média | Versionamento obrigatório; gate no CI; marcação visual da quebra na linha do tempo |
| **Snapshot perdido cria lacuna irreparável** | Alto | Baixa | `backfill-snapshots` a partir de `task_status_history` (fonte de verdade); `/snapshots/status` detecta lacunas; teste de determinismo |
| **`compute_metrics` roda sobre snapshot parcial** | Alto | Média | Job verifica existência do snapshot do dia e **aborta com alerta** em vez de calcular parcial |
| **Dashboard lento com histórico grande** | Médio | Média | Read model materializado; particionamento mensal; endpoint consolidado; cache com TTL; NF-2 como gate |
| **Cálculo divergente entre backend e frontend** | Alto | Média | **Proibição de cálculo no cliente**, com teste de contrato; `/dashboards/{slug}/data` retorna tudo pronto |
| **Divergência entre cockpit e Power BI** | Médio | Média | Exportar `metric_values` (não recalcular no BI); datasets versionados; documentar lineage |
| **Métrica manual desatualizada tratada como atual** | Médio | Alta | `data_origin` visível; lembrete de vencimento; marcação de desatualizada; `system.manual_metrics_stale` |
| **Cockpit compartilhado sem contexto** | Alto | Média | Rodapé obrigatório em export (período, cobertura, limitações, finalidade); trilha de acesso em `export_runs` |
| **Gaming da própria métrica** | Médio | Média | Métrica é diagnóstica e privada ao usuário no MVP; `DecisionLog` privilegia efeito sobre número; acesso de terceiros fora do escopo |

### 18.3 O risco mais provável, nomeado explicitamente

**O cockpit ser construído, ficar bonito, e não ser usado.**

É o destino mais comum de dashboards internos. Os quatro mecanismos deste PRD desenhados especificamente contra isso:

1. **`expected_action` obrigatório** — métrica sem ação prevista não entra no catálogo
2. **`DecisionLog` com revisão antes/depois** — fecha o ciclo entre olhar o número e agir
3. **`system.metrics_without_action` + revisão trimestral** — o sistema propõe podar o que não gerou ação
4. **Drill-down universal** — permite defender qualquer número em reunião, que é a condição prática para levá-lo à reunião

Nenhum desses é opcional. Se algum for cortado por prazo, o valor do cockpit cai desproporcionalmente.

---

## 19. Documentação a ser Gerada pelo Agente

| # | Artefato | Conteúdo |
|---|---|---|
| 1 | `README.md` | Quickstart local < 5 min, pré-requisitos, troubleshooting |
| 2 | `AGENTS.md` | Convenções, regra de dependência, comandos (`make test`, `make lint`, `make eval`, `make metrics-gate`), o que nunca alterar |
| 3 | `docs/ARCHITECTURE.md` | C4 (contexto, container, componente) em Mermaid, incluindo separação CQRS-lite |
| 4 | `docs/CORRELATION_ENGINE.md` | 3 estágios, recuperadores e pesos, matriz de arbitragem completa, 4 guardrails, exemplos por tipo de decisão |
| 5 | `docs/CALENDAR_INGESTION.md` | `calendarView` vs `events`, séries e exceções, privacidade, cálculo de capacidade |
| 6 | ★ `docs/ANALYTICS.md` | Read model, snapshots, reconstrutibilidade, motor de métricas, versionamento, cobertura, materialização, paridade entre dialetos |
| 7 | ★ `docs/METRICS_CATALOG.md` | **Gerado automaticamente do `MetricRegistry`** — fórmula, pergunta, dimensões, limitações, ação esperada, dono, versão. Nunca escrito à mão |
| 8 | ★ `docs/ANALYTICS_ETHICS.md` | Seção 8 expandida: fronteiras, k-anonimato, proibições, como `EthicsGuard` valida, orientação para validação com RH/Compliance |
| 9 | ★ `docs/DASHBOARDS.md` | Cada dashboard: pergunta central, widgets, drill-down, como interpretar, o que **não** concluir |
| 10 | ★ `docs/INSIGHT_GUARDRAILS.md` | Papel do LLM na narrativa, guardrail numérico, fato vs. hipótese, modos de falha conhecidos |
| 11 | `docs/DATA_MODEL.md` | ERD Mermaid (operacional + analítico) + dicionário de dados |
| 12 | `docs/PROMPTS.md` | Prompts versionados com changelog e resultado de avaliação por versão |
| 13 | `docs/SETUP_ENTRA_ID.md` | App Registration, escopos, admin consent |
| 14 | `docs/SETUP_LLM_PROVIDER.md` | Obter API key, descobrir `model_id` via `models.list`, tiers e governança |
| 15 | `docs/PRIVACY.md` | Matriz do que é armazenado e do que é enviado ao LLM, por fonte e configuração |
| 16 | `docs/SECURITY.md` | STRIDE simplificado, segredos, retenção, governança por provedor, **as 8 variáveis sensíveis (15.1)** |
| 17 | `docs/RUNBOOK.md` | Alertas, incidentes, backup/restore, rotação de segredos, reindexação, **recuperação de lacuna de snapshot**, **recálculo de métricas** |
| 18 | ★ `docs/BI_INTEGRATION.md` | Datasets exportados, schema, chaves, lineage, como conectar Power BI sem recalcular métrica |
| 19 | `docs/adr/` | ADRs (Nygard). Mínimo: ingestão por `Signal`; hexagonal; Gemini default; `calendarView` vs `events`; arbitragem determinística; monolito modular; **snapshots append-only vs. cálculo on-the-fly**; **métricas code-first vs. config em banco**; **SQL próprio vs. ferramenta de BI embarcada**; **LLM restrito a narrativa** |
| 20 | `openapi.json` | Gerado automaticamente |
| 21 | `CHANGELOG.md` | Keep a Changelog + SemVer |

---

## 20. Prompt Inicial para o Agente

Cole este bloco junto com o PRD completo:

```
Você vai implementar o projeto descrito no PRD anexo (TaskFlow v1.2).

═══ REGRAS DE EXECUÇÃO ═══
 1. Trabalhe FASE POR FASE, na ordem:
    0 → 1 → 2 → 3 → 3.5 → 4 → 4.5 → 5 → 6 → 6.5 → 7 → 7.5 → 8 → 8.5 → 9 → 10
    Não avance sem que os testes da fase atual estejam passando.
 2. Ao iniciar cada fase: apresente um plano de implementação e aguarde meu OK.
 3. Ao concluir cada fase: rode lint + type check + testes + metrics-gate,
    mostre o resultado, e faça um commit convencional único.
 4. Arquitetura hexagonal: `domain/` não importa NADA de `adapters/` ou
    `application/`. Se precisar violar, PARE e pergunte.
 5. Escreva o teste junto com a implementação. Cada critério Gherkin do PRD
    deve ter teste rastreável pelo ID (RF-x.y).
 6. NUNCA faça chamadas reais a LLM ou Microsoft Graph em testes unitários ou
    de integração. Use stubs das portas e fixtures/cassettes.
 7. Nenhum segredo em código, commit ou log. Só variáveis de ambiente ou o
    cofre cifrado provider_credentials.
 8. Decisão técnica relevante fora do PRD: registre um ADR em docs/adr/ e
    pergunte antes de prosseguir.
 9. Código legível e explícito sobre código "esperto". Type hints completos.
    Docstrings em portas e políticas de domínio.
10. Ambiguidade ou contradição no PRD: PERGUNTE. Não invente requisito nem
    silencie a dúvida.

═══ DOMÍNIO: INGESTÃO E CORRELAÇÃO ═══
11. Unidade canônica de ingestão é `source_items` (discriminador `kind`) +
    `calendar_events`. NÃO crie tabela `messages`.
12. Extração e correlação são estágios SEPARADOS, mediados por `Signal`.
    Nunca uma única chamada de LLM que extraia e decida ao mesmo tempo.
13. A decisão final de correlação é SEMPRE determinística, em
    domain/policies/correlation_policy.py. O LLM produz avaliação e evidência;
    a policy decide. Um teste por linha da matriz RF-G.8.
14. Todo assessment do LLM passa pelos 4 guardrails do RF-G.7 antes de
    qualquer efeito. Sem exceção.
15. Nenhuma ação automática sem registro em `correlation_runs` e sem caminho
    de undo. O undo reverte COMPLETAMENTE, via snapshot em
    task_status_history.
16. Eventos com sensitivity private/confidential NUNCA vão ao LLM. Escreva
    teste de propriedade que FALHE o build se isso ocorrer.
17. O model_id do Gemini é SEMPRE variável de ambiente. Não invente nem
    hardcode. Valide via models.list na inicialização, falhando com mensagem
    que liste os modelos disponíveis para a chave.
18. API keys: cifradas em repouso, write-only na API, mascaradas na UI, jamais
    em log ou erro. Escreva teste que garanta isso.
19. Antes de chamar o estágio G2, verifique o atalho determinístico RF-G.3.
    Custo importa.
20. ATTACH_CONTEXT é cidadão de primeira classe, não caso de borda. A maior
    parte do tráfego cai nele. Mesmo cuidado que NEW_TASK.

═══ DOMÍNIO: CAMADA ANALÍTICA (v1.2) ═══
21. `task_status_history` é a FONTE DE VERDADE. Snapshots são read model
    derivado e reconstruível. Escreva teste de propriedade: backfill de uma
    data já processada produz resultado IDÊNTICO.
22. Métricas são CODE-FIRST em domain/metrics/definitions/. Cada métrica
    declara obrigatoriamente: question, formula, limitations,
    expected_action, owner. Sem esses campos, o gate do CI FALHA.
23. Cada métrica tem UM teste com fixture sintética e resultado esperado
    calculado à mão. 100% de cobertura do catálogo. Sem exceção.
24. NENHUM cálculo numérico com LLM. Zero. O LLM só produz narrativa sobre
    números já calculados. Escreva teste com spy no LLMProvider provando
    zero invocações nos endpoints de métrica.
25. NENHUM cálculo numérico no frontend. `/dashboards/{slug}/data` retorna
    tudo pronto. Teste de contrato garante isso.
26. Toda resposta de métrica carrega o envelope do RF-I.6: value, coverage,
    sample_size, is_suppressed, caveat, period_comparison. Sem envelope, o
    endpoint está incompleto.
27. Drill-down universal: TODO número é clicável até a lista de tarefas e até
    a evidência textual literal na fonte. Escreva teste de reconciliação
    provando len(drilldown) == value para métricas de contagem.
28. Alterar fórmula de métrica exige incrementar `version`. O gate do CI
    detecta divergência contra metric_definitions e falha.
29. Insight narrativo passa por guardrail numérico ESTRITO: todo número no
    texto é extraído por parser e validado contra o payload de entrada.
    Falha ⇒ 1 retry ⇒ narrativa suprimida, só números exibidos.
30. Toda métrica de terceiros é AGREGADA por área, sujeita a k-anonimato
    (mínimo 3). Ranking individual de pessoas é PROIBIDO por design.
    Implemente EthicsGuard como validação no CI, não como recomendação.
    Nenhuma métrica de horário, presença ou disponibilidade de terceiros.
31. compute_metrics verifica a existência do snapshot do dia e ABORTA com
    alerta se ausente. Nunca calcule sobre snapshot parcial.
32. Métricas devem produzir resultados IDÊNTICOS em SQLite e Postgres.
    Teste de paridade obrigatório.

═══ COMECE ═══
Fase 0. Apresente o plano.
```

---

## 21. Próximos Passos

### 21.1 Ações imediatas (suas, não do agente)

**1. App Registration no tenant ENGIE — único item verdadeiramente bloqueante.**
Escopos delegados: `User.Read`, `Mail.Read`, `Mail.Send`, `Chat.Read`, `Calendars.Read`, `People.Read`, `User.ReadBasic.All`, `offline_access`. Abra a solicitação antes de codar. O desenvolvimento avança com fixtures, mas a validação real depende disso.

**2. Descobrir o `model_id` correto do Gemini.**
Gere a API key, liste os modelos disponíveis e registre os identificadores exatos para `classifier` e `reasoner`. **Use tier pago** — o gratuito tem implicações de governança de dados incompatíveis com e-mail e calendário corporativos.

**3. Construir os datasets dourados** — maior alavancagem do projeto, e ninguém pode fazer por você:

| Dataset | Volume | Como montar |
|---|---|---|
| Extração — e-mail/chat | 50 itens | Rotule "é tarefa / não é" + campos esperados |
| Extração — calendário | 20 eventos | Rotule o tipo de sinal esperado |
| **Correlação** | **40 pares** | Pegue 10 tarefas reais dos últimos 2 meses; reconstitua a sequência de e-mails/chats/reuniões; rotule cada item como `NEW_TASK`, `UPDATE_EXISTING`, `TRANSITION_EXISTING`, `ATTACH_CONTEXT` ou `NOISE` |
| Insight (fase 9) | 10 payloads | Métricas + narrativa de referência, para testar o guardrail numérico |

**4. Definir a estrutura organizacional (fase 6.5).**
Liste suas áreas, marque quais são equipe própria (`is_own_team=true`), agrupe projetos em portfólios. Meia hora de trabalho que determina a qualidade de toda a Perspectiva 3.

**5. Escolher as 10 métricas iniciais.**
O catálogo tem ~55. **Não implemente todas de uma vez.** Escolha 10 que respondam perguntas que você realmente tem hoje, e para cada uma escreva a ação que tomaria se o número desviasse. Se não conseguir escrever a ação, a métrica não deve entrar. Expanda depois, com base em uso.

**6. Validação de Segurança, Privacidade e RH.**
Dois pedidos distintos, com naturezas diferentes:

- **Segurança/Privacidade:** processar e-mail, chat e calendário corporativos com API externa de LLM. O calendário eleva a sensibilidade — reuniões revelam relações, negociações e informação estratégica.
- **RH/Compliance:** métricas derivadas de comunicação que envolvem terceiros. Mesmo com as salvaguardas da Seção 8, e mesmo sendo dados legitimamente acessíveis a você, métrica sobre pessoas tem sensibilidade jurídica e cultural distinta de métrica de sistema transacional. Vale a conversa **antes** de usar qualquer número com nomes em contexto formal.

### 21.2 Decisões abertas

| Decisão | Opções | Recomendação |
|---|---|---|
| Stack | Python vs. TypeScript full-stack | Python — ecossistema de LLM, embeddings e analítica mais maduro |
| Provedor de LLM | Gemini API vs. Vertex AI vs. Ollama local | Gemini pago para desenvolver; reavaliar conforme parecer de Segurança |
| Nome do produto | — | Substituir "TaskFlow" |
| `ALLOW_AUTO_DONE` | true/false | Comece `false` nas primeiras 2 semanas; ative após validar a taxa de undo |
| Escopo inicial de métricas | 10 vs. 55 | **10.** Métrica sem uso é passivo de manutenção |
| Quando iniciar a fase 7 | Imediato vs. após 6–8 semanas | **Após.** Sem histórico, métrica não tem baseline nem significado |
| Acesso de terceiros ao cockpit | MVP vs. depois | **Depois.** Requer modelo de permissão e revisão ética prévia |

### 21.3 Sequência recomendada de uso real

```
Semanas 1–4    Fases 0–5      Captura e triagem em uso diário
                              → calibrar limiares, medir taxa de undo

Semanas 5–8    Fases 6–6.5    Follow-up ativo + estrutura organizacional
                              → acumular histórico com dados já confiáveis

Semanas 9–12   Fases 7–7.5    Snapshots + 10 métricas iniciais
                              → backfill do histórico acumulado

Semanas 13+    Fases 8–9      Cockpit, alertas, insights, one-pager
                              → primeiro reporte mensal gerado pelo sistema
```

O ponto crítico é a fronteira entre a semana 8 e a 9: só faz sentido medir quando a captura já é confiável. Medir antes produz números enviesados que ensinam a desconfiar do próprio sistema.

---
