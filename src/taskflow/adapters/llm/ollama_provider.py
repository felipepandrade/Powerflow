import json
from typing import Any, cast

import httpx

from taskflow.domain.ports.ports import EmbeddingProvider, LLMProvider


class OllamaProvider(LLMProvider, EmbeddingProvider):
    """Implementação do provedor LLM usando a API local do Ollama."""

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "qwen3-coder:30b-instruct") -> None:
        self.base_url = base_url
        self.model_name = model_name

    async def _generate_json(self, prompt: str) -> dict[str, Any]:
        """Faz a requisição para a API local do Ollama exigindo JSON format."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0,
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                return cast(dict[str, Any], json.loads(data.get("response", "{}")))
            except Exception:  # noqa: BLE001
                return {}

    async def classify(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = f"Classifique se o seguinte texto contém um compromisso acionável (task). Retorne {{'is_actionable': bool, 'confidence': float}}.\nTexto: {text}"
        return await self._generate_json(prompt)

    async def extract(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Você é um assistente de IA focado em extrair tarefas acionáveis a partir de e-mails ou anotações.\n\n"
            f"Contexto do E-mail:\n"
            f"- Remetente: {context.get('author_name', 'Desconhecido')} ({context.get('author_email', 'Desconhecido')})\n"
            f"- Assunto: {context.get('subject', 'Sem Assunto')}\n"
            f"- Data Atual: {context.get('date', 'Desconhecida')}\n\n"
            f"Texto Original:\n{text}\n\n"
            "Sua tarefa: Identifique a principal solicitação ou compromisso no texto acima.\n"
            "Retorne ESTRITAMENTE um objeto JSON válido (sem markdown, sem explicações) com a seguinte estrutura:\n"
            "{\n"
            "  \"title\": \"Um título curto, claro e direto para a tarefa\",\n"
            "  \"description\": \"Uma descrição detalhada do que precisa ser feito\",\n"
            "  \"due_date\": \"YYYY-MM-DD ou null\",\n"
            "  \"priority\": \"low\" ou \"medium\" ou \"high\"\n"
            "}"
        )
        return await self._generate_json(prompt)

    async def correlate(self, signal: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
        prompt = (
            f"Sinal de entrada: {json.dumps(signal)}\n\n"
            f"Tarefas candidatas: {json.dumps(candidates)}\n\n"
            "Avalie a correlação. Retorne o JSON:\n"
            "{ 'assessments': [ {'task_id': str, 'reasoning': str, 'score': float_0_to_1} ], "
            "'decision_hint': 'apply'|'triage'|'discard' }"
        )
        return await self._generate_json(prompt)

    async def draft_follow_up(self, task: dict[str, Any], context: dict[str, Any], tone: str) -> str:
        prompt = (
            f"Escreva uma mensagem de follow-up (tom: {tone}) para a tarefa: {task.get('title')}.\n"
            f"Contexto: {json.dumps(context)}\n"
            "Retorne apenas o texto da mensagem."
        )
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                return str(data.get("response", ""))
            except Exception:  # noqa: BLE001
                return ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Ollama API de Embeddings
        url = f"{self.base_url}/api/embed"
        embeddings = []
        
        async with httpx.AsyncClient() as client:
            for text in texts:
                payload = {
                    "model": "nomic-embed-text",  # Modelo recomendado localmente
                    "input": text
                }
                try:
                    response = await client.post(url, json=payload, timeout=30.0)
                    response.raise_for_status()
                    data = response.json()
                    # Ollama returna {"embeddings": [[float, ...]]}
                    embs = data.get("embeddings", [[]])
                    if embs:
                        embeddings.append(embs[0])
                except Exception:  # noqa: BLE001
                    embeddings.append([])
                    
        return embeddings
