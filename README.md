# TaskFlow — Sistema Pessoal de Captura Autônoma e Gestão Correlacionada de Tarefas

**TaskFlow** é um copiloto pessoal que lê continuamente e-mails, chats (Teams) e agenda (Outlook/Teams); identifica compromissos com evidência rastreável; decide autonomamente se cada nova informação é uma tarefa nova, atualização de existente ou apenas contexto correlato; e gerencia o ciclo de vida de compromissos que dependem de terceiros.

---

## Quickstart Local (< 5 min)

### Pré-requisitos
- Python 3.12+ (ou Docker & Docker Compose)

### 1. Clonar e configurar ambiente
```bash
cp .env.example .env
```
Preencha no `.env` sua chave `GEMINI_API_KEY` obtida no Google AI Studio (ou configure via UI em Settings).

### 2. Executar via Docker Compose
```bash
docker compose -f infra/compose/local.yml up -d
```
A REST API estará disponível em `http://localhost:8080` e os endpoints de integridade em `http://localhost:8080/health/live`.

### 3. Executar localmente sem Docker
```bash
pip install -e .[dev]
uvicorn apps.api.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## Arquitetura e Estrutura
- **`src/taskflow/domain`**: Entidades puras, Value Objects e Políticas de Domínio (`CorrelationPolicy`, `TaskStateMachine`, etc.).
- **`src/taskflow/application`**: Casos de uso e orquestração.
- **`src/taskflow/adapters`**: Integradores externos (Microsoft Graph, Gemini LLM Provider, SQLAlchemy).
- **`apps/`**: Interfaces de execução (`api`, `worker`, `cli`).

---

## Testes e Qualidade
```bash
# Rodar testes unitários e de integração
pytest

# Checagem de tipos
mypy src apps

# Linting
ruff check .
```
