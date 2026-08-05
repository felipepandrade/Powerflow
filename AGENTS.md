# AGENTS.md — Diretrizes para Agentes de IA (TaskFlow v1.1)

## Regras Invioláveis de Arquitetura e Código

1. **Arquitetura Hexagonal (Ports & Adapters):**
   - A camada `src/taskflow/domain` é a única fonte da verdade de negócio.
   - `domain/` **não importa nada** de `adapters/`, `application/` ou bibliotecas de I/O (FastAPI, SQLAlchemy, HTTPX, Google GenAI, etc.).
   - Toda dependência externa é invertida usando Interfaces / Classes Abstratas (`ports/`).

2. **Decisões Determinísticas de Correlação:**
   - A decisão final de correlação de tarefas vive em `src/taskflow/domain/policies/correlation_policy.py`.
   - O LLM gera apenas hipótese e evidência (`assessments`). A política de domínio toma a decisão.
   - Toda linha da matriz de arbitragem (RF-G.8 do PRD) deve possuir teste unitário determinístico sem chamada a LLM.

3. **Invariantes de Segurança e Privacidade:**
   - Nenhum segredo ou chave de API pode ser exposto em logs, retornos de API ou exceções.
   - Eventos de calendário marcados como `private` ou `confidential` **nunca** alcançam o payload enviado ao provedor de LLM.
   - Toda ação automática em tarefas possui registro em audit trail (`correlation_runs`) e suporte a reversão (Undo).

4. **Convenções de Código e Testes:**
   - Type hints explícitos em 100% dos métodos e funções (`mypy --strict`).
   - Testes unitários de domínio rodando 100% em memória, sem I/O nem rede.
   - Cobertura de testes mantida ≥ 80% global e ≥ 90% em `domain/`.
